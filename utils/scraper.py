import requests
import html
import json
import time
from typing import Iterator
from bs4 import BeautifulSoup

from config import RETRY_DELAY, USER_AGENT, X_ALGOLIA_API_KEY
from .sheets import sheet
from .hunter_api import get_ceo_email_from_hunter
from .helpers import extract_domain

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

# Checks if there are any remote or engineering jobs, as well as a dedicated career page
def search_jobs(yc_job_link: str, company_link: str) -> tuple[bool, bool, str]:
    html_structure = get_html(yc_job_link)
    soup = BeautifulSoup(html_structure, "html.parser")

    # Turn the react component into a readable json
    component_div = soup.find("div", id=lambda x: x and x.startswith("WaasShowJobsPage-react-component"))

    if not component_div:
        return (False, False, "")
    
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
def fetch_yc_companies(existing_companies) -> Iterator[None]:
    index = 1

    # YC uses algolia api to fetch companies, we can use it too
    url = "https://45bwzj1sgc-dsn.algolia.net/1/indexes/*/queries"
    headers = {
        "Content-Type": "application/json",
        "x-algolia-agent": "Algolia for JavaScript (3.35.1); Browser; JS Helper (3.16.1)",
        "x-algolia-application-id": "45BWZJ1SGC",
        "x-algolia-api-key": X_ALGOLIA_API_KEY
    }
    data = {
        "requests": [
            {
            "indexName": "YCCompany_production",
            "params": "facetFilters=%5B%5B%22batch%3AFall%202024%22%2C%22batch%3ASpring%202025%22%2C%22batch%3ASummer%202015%22%2C%22batch%3ASummer%202016%22%2C%22batch%3ASummer%202017%22%2C%22batch%3ASummer%202018%22%2C%22batch%3ASummer%202019%22%2C%22batch%3ASummer%202020%22%2C%22batch%3ASummer%202021%22%2C%22batch%3ASummer%202022%22%2C%22batch%3ASummer%202023%22%2C%22batch%3ASummer%202024%22%2C%22batch%3ASummer%202025%22%2C%22batch%3AWinter%202015%22%2C%22batch%3AWinter%202016%22%2C%22batch%3AWinter%202017%22%2C%22batch%3AWinter%202018%22%2C%22batch%3AWinter%202019%22%2C%22batch%3AWinter%202020%22%2C%22batch%3AWinter%202021%22%2C%22batch%3AWinter%202022%22%2C%22batch%3AWinter%202023%22%2C%22batch%3AWinter%202024%22%2C%22batch%3AWinter%202025%22%5D%2C%5B%22isHiring%3Atrue%22%5D%5D&facets=%5B%22app_answers%22%2C%22batch%22%2C%22industries%22%2C%22isHiring%22%2C%22regions%22%2C%22subindustry%22%5D&hitsPerPage=1000&maxValuesPerFacet=1000&page=0&query="
            }
        ]
    }

    res = requests.post(url, json=data, headers=headers)
    res.raise_for_status()
    json_data = res.json()

    # a "hit" is a company dictionary for YC
    for hit in json_data["results"][0]["hits"]:
        index += 1
        name = hit.get("name", "Unknown")
        website = hit.get("website", "Not Found")

        # If we havent done this company before then add it
        if name not in existing_companies:
            stage = hit.get("stage", "Unknown")
            desc = hit.get("one_liner", "")
            slug = hit.get("slug", "")
            link = f"https://www.ycombinator.com/companies/{slug}" if slug else ""

            # Extract founder info
            ceo_name, ceo_linkedin, company_linkedin = extract_founder_company_info(link) if link else None

            # Extract job info
            eng, remote, job_website = search_jobs(link+"/jobs", website) if link else None

            # Find email
            email = get_ceo_email_from_hunter(extract_domain(website), ceo_name.split()[0], ceo_name.split()[-1]) if website else ""

            # Append everything
            sheet.append_row([name, website, job_website, eng, remote, stage, company_linkedin, ceo_name, ceo_linkedin, email, desc])
            existing_companies.add(name)
            yield

        # If we have but email is missing, try using hunter again (if key works)
        elif not sheet.cell(index, 10).value:
            ceo_name = sheet.cell(index, 8).value
            email = get_ceo_email_from_hunter(extract_domain(website), ceo_name.split()[0], ceo_name.split()[-1]) if website else ""
            sheet.update_cell(index, 10, email)
            yield
        
        # Otherwise continue next iteration
        else:
            yield