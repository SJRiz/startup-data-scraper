import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import GOOGLE_SHEET_NAME

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gs_client = gspread.authorize(creds)
sheet = gs_client.open(GOOGLE_SHEET_NAME).sheet1