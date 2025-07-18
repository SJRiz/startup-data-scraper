from tqdm import tqdm

from utils.sheets import sheet
from utils.scraper import fetch_yc_companies

def main():

    # Add header row if empty
    if len(sheet.get_all_values()[0]) < 2:
        sheet.append_row([
            "Startup Name", "Website", "Job URL", "Hiring Engineers?",
            "Hiring Remote?", "Stage", "Linkedin URL", "CEO Name", "CEO Linkedin", "CEO Email", "Short Desc"
        ])

    # Load existing company names to avoid duplicates
    existing_companies = set(row[0] for row in sheet.get_all_values()[1:] if row[0])

    # Go through the generator and evaluate each company individually
    for _ in tqdm(fetch_yc_companies(existing_companies), desc="Searching for startups", leave=False):
        continue

if __name__ == "__main__":
    main()