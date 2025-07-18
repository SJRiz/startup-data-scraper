from urllib.parse import urlparse

# Removes the https:// portion of the website to get the domain
def extract_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "")