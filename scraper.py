import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import time

SHEET_NAME = "Tornejos Pitch & Putt Catalunya"
CREDENTIALS_FILE = "credentials.json"
BASE_URL = "https://www.pitch.cat/calendari/index.php"
DAYS_AHEAD = 60

def fetch_tournaments_for_date(date):
    date_str = date.strftime("%d/%m/%Y")
    try:
        response = requests.get(
            BASE_URL,
            params={"cerca":"1","dia":date.strftime("%d"),"mes":date.strftime("%m"),"any":date.strftime("%Y")},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )
        response.encoding = "iso-8859-1"
        soup = BeautifulSoup(response.text, "html.parser")
        tournaments = []
        names   = soup.find_all("h4")
        modals  = soup.find_all("h6")
        courses = soup.find_all("h5")
        for i, name_tag in enumerate(names):
            name   = name_tag.get_text(strip=True)
            modal  = modals[i].get_text(strip=True) if i < len(modals) else ""
            course = courses[i].get_text(strip=True) if i < len(courses) else ""
            if not name or len(name) < 3:
                continue
            parts    = modal.split(" ", 1)
            modality = parts[0] if parts else ""
            formula  = parts[1] if len(parts) > 1 else ""
            parent   = name_tag.find_parent("a")
            url = ""
            if parent and parent.get("href"):
                href = parent["href"]
                url = f"https://www.pitch.cat/calendari/{href}" if not href.startswith("http") else href
            tournaments.append({
                "Data":date_str,"Camp":course,"Torneig":name,
                "Modalitat":modality,"Formula":formula,
                "Font":"pitch.cat","URL":url or BASE_URL,
                "Actualitzat":datetime.now().strftime("%d/%m/%Y %H:%M"),
            })
        return tournaments
    except Exception as e:
        print(f"  Error {date_str}: {e}")
        return []

def scrape_all_tournaments():
    all_t = []
    today = datetime.today()
    print(f"Scraping {DAYS_AHEAD} dies...")
    for i in range(DAYS_AHEAD):
        date = today + timedelta(days=i)
        print(f"  {date.strftime('%d/%m/%Y')}...", end=" ", flush=True)
        t = fetch_tournaments_for_date(date)
        all_t.extend(t)
        print(len(t) if t else "-")
        time.sleep(0.4)
    print(f"\nTotal: {len(all_t)} tornejos")
    return all_t

def update_google_sheets(tournaments):
    print("Connectant a Google Sheets...")
    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    creds  = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    try:
        sheet = client.open(SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sheet = client.create(SHEET_NAME)
        sheet.share(None, perm_type="anyone", role="reader")
    try:
        ws = sheet.worksheet("Tornejos")
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet("Tornejos", rows=2000, cols=10)
    headers = ["Data","Camp","Torneig","Modalitat","Formula","Font","URL","Actualitzat"]
    rows = [headers] + [[t.get(h,"") for h in headers] for t in tournaments]
    ws.update("A1", rows)
    try:
        ws_meta = sheet.worksheet("Info")
    except gspread.WorksheetNotFound:
        ws_meta = sheet.add_worksheet("Info", rows=10, cols=2)
    ws_meta.update("A1",[
        ["Camp","Valor"],
        ["Ultima actualitzacio", datetime.now().strftime("%d/%m/%Y %H:%M")],
        ["Total tornejos", len(tournaments)],
        ["Font","pitch.cat"],
        ["URL Sheet", sheet.url],
    ])
    print(f"Escrit! {len(tournaments)} tornejos")
    print(f"URL: {sheet.url}")
    return sheet.url

def main():
    print("PITCH & PUTT SCRAPER", datetime.now().strftime("%d/%m/%Y %H:%M"))
    tournaments = scrape_all_tournaments()
    if not tournaments:
        print("No s'han trobat tornejos.")
        return
    update_google_sheets(tournaments)
    print("Fet!")

if __name__ == "__main__":
    main()
