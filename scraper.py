"""
pitch.cat Tournament Scraper
Scrapes tournaments from pitch.cat and writes to Google Sheets
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import time

# ── CONFIG ────────────────────────────────────────────────────
SHEET_NAME = "Tornejos Pitch & Putt Catalunya"
CREDENTIALS_FILE = "credentials.json"  # Google Service Account JSON
BASE_URL = "http://www.pitch.cat/calendari/index.php"

# Quants dies endavant scrapejar (30 = proper mes)
DAYS_AHEAD = 60

# ── SCRAPER ───────────────────────────────────────────────────
def fetch_tournaments_for_date(date: datetime) -> list[dict]:
    """Fetch all tournaments for a specific date from pitch.cat"""
    date_str = date.strftime("%d/%m/%Y")
    
    try:
        response = requests.post(
            BASE_URL,
            data={
                "cerca": "1",
                "dia": date.strftime("%d"),
                "mes": date.strftime("%m"),
                "any": date.strftime("%Y"),
            },
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )
        response.encoding = "iso-8859-1"
        soup = BeautifulSoup(response.text, "html.parser")
        
        tournaments = []
        
        # Find tournament table rows
        rows = soup.select("table tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                # Skip header rows
                text = [c.get_text(strip=True) for c in cells]
                if not text[0] or text[0].lower() in ("data", "camp", "torneig"):
                    continue
                
                tournament = {
                    "Data": date_str,
                    "Camp": text[0] if len(text) > 0 else "",
                    "Torneig": text[1] if len(text) > 1 else "",
                    "Modalitat": text[2] if len(text) > 2 else "",
                    "Categoria": text[3] if len(text) > 3 else "",
                    "Hora": text[4] if len(text) > 4 else "",
                    "Inscripcions": text[5] if len(text) > 5 else "",
                    "Font": "pitch.cat",
                    "URL": BASE_URL,
                    "Actualitzat": datetime.now().strftime("%d/%m/%Y %H:%M"),
                }
                tournaments.append(tournament)
        
        return tournaments
        
    except Exception as e:
        print(f"  ⚠ Error fetching {date_str}: {e}")
        return []


def scrape_all_tournaments(days_ahead: int = 60) -> list[dict]:
    """Scrape tournaments for the next N days"""
    all_tournaments = []
    today = datetime.today()
    
    print(f"🔍 Scraping {days_ahead} dies de tornejos...")
    
    for i in range(days_ahead):
        date = today + timedelta(days=i)
        print(f"  📅 {date.strftime('%d/%m/%Y')}...", end=" ", flush=True)
        
        tournaments = fetch_tournaments_for_date(date)
        all_tournaments.extend(tournaments)
        
        if tournaments:
            print(f"✅ {len(tournaments)} tornejos")
        else:
            print("—")
        
        time.sleep(0.5)  # Respectful scraping
    
    print(f"\n✅ Total: {len(all_tournaments)} tornejos trobats")
    return all_tournaments


# ── GOOGLE SHEETS ─────────────────────────────────────────────
def update_google_sheets(tournaments: list[dict]):
    """Write tournament data to Google Sheets"""
    
    print("\n📊 Connectant a Google Sheets...")
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Open or create sheet
    try:
        sheet = client.open(SHEET_NAME)
        print(f"  ✅ Sheet '{SHEET_NAME}' trobat")
    except gspread.SpreadsheetNotFound:
        sheet = client.create(SHEET_NAME)
        sheet.share(None, perm_type="anyone", role="reader")  # Public read
        print(f"  ✅ Sheet '{SHEET_NAME}' creat")
    
    # Get or create worksheets
    try:
        ws_tornejos = sheet.worksheet("Tornejos")
        ws_tornejos.clear()
    except gspread.WorksheetNotFound:
        ws_tornejos = sheet.add_worksheet("Tornejos", rows=1000, cols=10)
    
    # Headers
    headers = ["Data", "Camp", "Torneig", "Modalitat", "Categoria", "Hora", "Inscripcions", "Font", "URL", "Actualitzat"]
    
    # Build rows
    rows = [headers]
    for t in tournaments:
        rows.append([t.get(h, "") for h in headers])
    
    # Write to sheet
    ws_tornejos.update("A1", rows)
    
    # Format header row
    ws_tornejos.format("A1:J1", {
        "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
        "textFormat": {"bold": True, "foregroundColor": {"red": 0.79, "green": 1.0, "blue": 0.3}},
    })
    
    # Freeze header
    sheet.batch_update({"requests": [{"updateSheetProperties": {
        "properties": {"sheetId": ws_tornejos.id, "gridProperties": {"frozenRowCount": 1}},
        "fields": "gridProperties.frozenRowCount"
    }}]})
    
    # Update metadata tab
    try:
        ws_meta = sheet.worksheet("Info")
    except gspread.WorksheetNotFound:
        ws_meta = sheet.add_worksheet("Info", rows=10, cols=2)
    
    ws_meta.update("A1", [
        ["Camp", "Valor"],
        ["Última actualització", datetime.now().strftime("%d/%m/%Y %H:%M")],
        ["Total tornejos", len(tournaments)],
        ["Dies consultats", DAYS_AHEAD],
        ["Font principal", "pitch.cat"],
        ["URL Sheet", sheet.url],
    ])
    
    print(f"  ✅ {len(tournaments)} tornejos escrits al Google Sheet")
    print(f"  🔗 URL: {sheet.url}")
    return sheet.url


# ── MAIN ──────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  PITCH & PUTT TOURNAMENT SCRAPER")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 50)
    
    tournaments = scrape_all_tournaments(DAYS_AHEAD)
    
    if not tournaments:
        print("⚠ No s'han trobat tornejos. Revisa la connexió o l'estructura de la web.")
        return
    
    url = update_google_sheets(tournaments)
    
    print("\n🎉 Fet!")
    print(f"   Google Sheet: {url}")


if __name__ == "__main__":
    main()
