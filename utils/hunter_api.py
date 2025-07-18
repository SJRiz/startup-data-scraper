import requests

from config import HUNTER_API_KEY

# Uses Hunter Email Finder API to get CEO email by name + domain
def get_ceo_email_from_hunter(domain: str, first_name: str, last_name: str) -> str:
    if not domain or not first_name or not last_name:
        return ""
    
    try:
        url = "https://api.hunter.io/v2/email-finder"
        params = {
            "domain": domain,
            "first_name": first_name,
            "last_name": last_name,
            "api_key": HUNTER_API_KEY
        }
        resp = requests.get(url, params=params, timeout=3)
        resp.raise_for_status()
        data = resp.json().get("data", {})

        return data.get("email", "Not Found")
    
    except Exception:
        return ""