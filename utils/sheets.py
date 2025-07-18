import gspread
import time
from oauth2client.service_account import ServiceAccountCredentials

from config import GOOGLE_SHEET_NAME

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gs_client = gspread.authorize(creds)
sheet = gs_client.open(GOOGLE_SHEET_NAME).sheet1

# If we hit the rate limit for reading, just wait
def safe_cell_read(sheet, row, col, delay=10):
    while True:
        try:
            return sheet.cell(row, col).value
        except Exception as e:
            if "429" in str(e):
                time.sleep(5)
            else:
                raise