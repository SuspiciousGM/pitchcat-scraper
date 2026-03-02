import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import time

SHEET_NAME = "Tornejos Pitch & Putt Catalunya"
CREDENTIALS_FILE = "credentials.json"
DAYS_AHEAD = 60

def fetch_tournaments_range():
    """Fetch tournaments using the date range search form"""
    today = datetime.today()
    end   = today + timedelta(days=DAYS_AHEAD)

    url = "https://www.pitch.cat/calendari/index.php"
    data = {
        "cerca": "1",
        "data_ini": today.strftime("%d/%m/%Y"),
        "data_fi":  end.strftime("%d/%m/%Y"),
        "nom": "",
        "cc[]": "",
        "mod[]": "",
        "formula[]": "",
    }

    try:
        r = requests.post(url, data=data,
                          headers={"User-Agent": "Mozilla/5.0",
                                   "Content-Type": "application/x-www-form-urlencoded"},
                          timeout=20)
        r.encoding = "iso-8859-1"
        soup = BeautifulSoup(r.text, "html.parser")

        tournaments = []

        # Each tournament: h4=nom, h6=modalitat+formula, h5=camp
        # They're wrapped in <a href="torneig.php?id=...">
        links = soup.find_all("a", href=lambda h: h and "torneig.php?id=" in h)

        for link in links:
            name_tag   = link.find("h4")
            modal_tag  = link.find("h6")
            course_tag = link.find("h5")
            date_tag   = link.find("span") or link.find("div", class_="data")

            if not name_tag:
                continue

            name   = name_tag.get_text(strip=True)
            modal  = modal_tag.get_text(strip=True)  if modal_tag  else ""
            course = course_tag.get_text(strip=True) if course_tag else ""
            date   = date_tag.get_text(strip=True)   if date_tag   else ""

            href = link.get("href","")
            full_url = f"https://www.pitch.cat/calendari/{href}" if not href.startswith("http") else href

            tournaments.append({
                "Data":        date,
                "Camp":        course,
                "Torneig":     name,
                "Modalitat":   modal,
                "Font":        "pitch.cat",
                "URL":         full_url,
                "Actualitzat": datetime.now().strftime("%d/%m/%Y %H:%M"),
            })

        print(f"Trobats {len(tournaments)} tornejos")
        return tournaments

    except Exception as e:
        print(f"Error: {e}")
        return []


def fetch_by_day_fallback():
    """Fallback: scrape day by day"""
    all_t = []
    today = datetime.today()
    url   = "https://www.pitch.cat/calendari/index.php"

    for i in range(DAYS_AHEAD):
        date = today + timedelta(days=i)
        print(f"  {date.strftime('%d/%m/%Y')}...", end=" ", flush=True)
        try:
            r = requests.post(url,
                data={"cerca":"1",
                      "dia": date.strftime("%d"),
                      "mes": date.strftime("%m"),
                      "any": date.strftime("%Y")},
                headers={"User-Agent":"Mozilla/5.0",
                         "Referer":"https://www.pitch.cat/calendari/index.php"},
                timeout=15)
            r.encoding = "iso-8859-1"
            soup = BeautifulSoup(r.text, "html.parser")

            links = soup.find_all("a", href=lambda h: h and "torneig.php?id=" in h)
            day_t = []
            for link in links:
                name_tag   = link.find("h4")
                modal_tag  = link.find("h6")
                course_tag = link.find("h5")
                if not name_tag:
                    continue
                name   = name_tag.get_text(strip=True)
                modal  = modal_tag.get_text(strip=True)  if modal_tag  else ""
                course = course_tag.get_text(strip=True) if course_tag else ""
                href   = link.get("href","")
                full_url = f"https://www.pitch.cat/calendari/{href}"
                day_t.append({
                    "Data":        date.strftime("%d/%m/%Y"),
                    "Camp":        course,
                    "Torneig":     name,
                    "Modalitat":   modal,
                    "Font":        "pitch.cat",
                    "URL":         full_url,
                    "Actualitzat": datetime.now().strftime("%d/%m/%Y %H:%M"),
                })
            all_t.extend(day_t)
            print(len(day_t) if day_t else "-")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(0.3)

    print(f"\nTotal: {len(all_t)} tornejos")
    return all_t


def update_google_sheets(tournaments):
    print("Connectant a Google Sheets...")
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
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

    headers = ["Data","Camp","Torneig","Modalitat","Font","URL","Actualitzat"]
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

    # Try range search first, fall back to day-by-day
    tournaments = fetch_tournaments_range()
    if not tournaments:
        print("Range search buit, provant dia a dia...")
        tournaments = fetch_by_day_fallback()

    if not tournaments:
        print("No s'han trobat tornejos.")
        return

    update_google_sheets(tournaments)
    print("Fet!")

if __name__ == "__main__":
    main()
