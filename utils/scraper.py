import requests
import html
import json
import time
from typing import Iterator
from bs4 import BeautifulSoup
from pathlib import Path

from config import RETRY_DELAY, USER_AGENT, X_ALGOLIA_API_KEY
from .sheets import safe_cell_read, sheet
from .hunter_api import get_ceo_email_from_hunter
from .helpers import extract_domain

data_path = Path(__file__).resolve().parent.parent / "data" / "storedcompanies.txt"

# Gets the HTML structure of a website. Default 2 attempts
def get_html(link: str, attempts: int = 2) -> str:
    headers = {
        "User-Agent": USER_AGENT
    }
    try:
        response = requests.get(link, headers=headers, timeout=5)
        response.raise_for_status()
        time.sleep(RETRY_DELAY)
        return response.text

    # Retry if failure
    except requests.RequestException:
        if attempts > 0:
            time.sleep(RETRY_DELAY)
            return get_html(link, attempts-1)
        else:
            return ""

# Appends the CEO's name, linkedin, and company linkedin to the sheet
def extract_founder_company_info(yc_company_link: str) -> tuple[str, str, str]:
    html_structure = get_html(yc_company_link)
    soup = BeautifulSoup(html_structure, "html.parser")

    ceo_name = soup.find("div", class_="min-w-0 flex-1").find("div", class_="text-xl font-bold").get_text(strip=True)

    ceo_linkedin = soup.find("a", class_="flex h-8 w-8 items-center justify-center rounded-md border border-[#EBEBEB] bg-white transition-colors duration-150 hover:bg-gray-50", attrs={"aria-label":"LinkedIn profile"})
    if ceo_linkedin:
        ceo_linkedin = ceo_linkedin['href']

    company_linkedin = soup.find("a", class_="flex h-9 w-9 items-center justify-center rounded-md border border-[#EBEBEB] bg-white transition-colors duration-150 hover:bg-gray-50", attrs={"aria-label":"LinkedIn profile"})
    if company_linkedin:
        company_linkedin = company_linkedin['href']

    return ceo_name, ceo_linkedin, company_linkedin

# Checks if there are any remote or engineering jobs
def search_jobs(yc_job_link: str, company_link: str) -> tuple[bool, bool, str]:
    html_structure = get_html(yc_job_link)
    soup = BeautifulSoup(html_structure, "html.parser")

    # Turn the react component into a readable json
    component_div = soup.find("div", id=lambda x: x and x.startswith("WaasShowJobsPage-react-component"))

    if not component_div:
        return False, False, ""

    data_page_json = component_div["data-page"]
    decoded_data = html.unescape(data_page_json)
    data = json.loads(decoded_data)

    # Extract job data, and see if there is remote or eng anywhere
    job_postings = data["props"]["jobPostings"]
    eng = False
    remote = False

    for job in job_postings:
        title = job["title"]
        location = job.get("location")
        role = job.get("role")

        if "remote" in location.lower() or "remote" in job.get("locationType", "").lower() or "remote" in [tag.lower() for tag in job.get("tags", [])] or "remote" in title.lower():
            remote = True
        if "eng" in role.lower() or "engineer" in title.lower():
            eng = True

    # See if we can find the company's official job website
    job_website = find_job_website(company_link)
    if job_website != "":
        return (eng, remote, job_website)
    else:
        return (eng, remote, yc_job_link+" (could not find a dedicated career website)")


# Checks to see if the company's webpage has a job website
def find_job_website(company_link: str) -> str:
    if get_html(company_link+"/careers"):
        return company_link+"/careers"
    if get_html(company_link+"/jobs"):
        return company_link+"/jobs"
    return ""

# Fetches all the company's data through a generator/iterator using lazy evaluation (saves a lot of space rather than calculating all at once)
def fetch_yc_companies() -> Iterator[None]:
    url = "https://45bwzj1sgc-dsn.algolia.net/1/indexes/*/queries"
    headers = {
        "Content-Type": "application/json",
        "x-algolia-agent": "Algolia for JavaScript (3.35.1); Browser; JS Helper (3.16.1)",
        "x-algolia-application-id": "45BWZJ1SGC",
        "x-algolia-api-key": X_ALGOLIA_API_KEY
    }

    # First get all available batches
    batch_payload = {
        "requests": [{
            "indexName": "YCCompany_production",
            "query": "",
            "hitsPerPage": 0,
            "facets": ["batch"],
            "facetFilters": [["regions:America / Canada"]]
        }]
    }
    res = requests.post(url, json=batch_payload, headers=headers)
    res.raise_for_status()
    batches = list(res.json()["results"][0]["facets"]["batch"].keys())

    # Process each batch separately
    for batch in batches:
        payload = {
            "requests": [{
                "indexName": "YCCompany_production",
                "query": "",
                "page": 0,
                "hitsPerPage": 1000,
                "facets": [],
                "facetFilters": [
                    ["regions:America / Canada"],
                    [f"batch:{batch}"]
                ]
            }]
        }

        res = requests.post(url, json=payload, headers=headers)
        res.raise_for_status()
        result = res.json()["results"][0]
        hits = result["hits"]

        for hit in hits:

            # Retrieve previous companies
            with open(data_path, "r", encoding="utf-8") as f:
                existing_companies = set(line.strip() for line in f if line.strip())

            try:
                name = hit.get("name", "Unknown")
                website = hit.get("website", "Not Found")

                if name not in existing_companies:
                    stage = hit.get("stage", "Unknown")
                    desc = hit.get("one_liner", "")
                    slug = hit.get("slug", "")
                    link = f"https://www.ycombinator.com/companies/{slug}" if slug else ""

                    # Founder info
                    ceo_name, ceo_linkedin, company_linkedin = extract_founder_company_info(link) if link else (None, None, None)

                    # Job info
                    eng, remote, job_website = search_jobs(link + "/jobs", website) if link else (None, None, None)

                    # Email
                    email = get_ceo_email_from_hunter(
                        extract_domain(website),
                        ceo_name.split()[0],
                        ceo_name.split()[-1]
                    ) if website and ceo_name else ""

                    # Write to sheet (double check)
                    if name not in existing_companies:
                        sheet.append_row([
                            name, website, job_website, eng, remote, stage,
                            company_linkedin, ceo_name, ceo_linkedin, email, desc
                        ])
                        with open(data_path, "a", encoding="utf-8") as f:
                            f.write('\n' + name.strip())
                    yield

                else:
                    yield

            except:
                yield