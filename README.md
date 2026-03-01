# Pitch & Putt Tournament Scraper 🏌️

Scraping diari automàtic de tornejos de pitch.cat → Google Sheets

## Resultat final

Un Google Sheet que s'actualitza cada dia a les 7h amb tots els tornejos
dels propers 60 dies a Catalunya.

---

## Setup (1 sola vegada, ~15 minuts)

### 1. Crear Google Service Account

1. Ves a https://console.cloud.google.com
2. Crea un projecte nou → "pitchcat-scraper"
3. Activa les APIs:
   - **Google Sheets API**
   - **Google Drive API**
4. Ves a **IAM & Admin → Service Accounts**
5. Crea un Service Account → "pitchcat-bot"
6. Crea una clau JSON → descarrega el fitxer
7. Desa el contingut del JSON (ho necessitaràs al pas 3)

### 2. Crear repo a GitHub

```bash
# Al teu ordinador
mkdir pitchcat-scraper
cd pitchcat-scraper
git init
# Copia tots els fitxers d'aquest zip aquí
git add .
git commit -m "feat: pitch.cat tournament scraper"
git remote add origin https://github.com/EL_TEU_USUARI/pitchcat-scraper.git
git push -u origin main
```

### 3. Afegir el secret de Google a GitHub

1. Al teu repo → **Settings → Secrets → Actions**
2. Clica **New repository secret**
3. Nom: `GOOGLE_CREDENTIALS`
4. Valor: el contingut sencer del fitxer JSON descarregat al pas 1
5. Guarda

### 4. Provar manualment

1. Ves a **Actions** al teu repo GitHub
2. Clica "Daily Tournament Scraper"
3. Clica **Run workflow**
4. Espera ~2 minuts
5. Al log trobaràs la URL del Google Sheet ✅

---

## Com funciona

```
Cada dia a les 7:00 AM
        ↓
GitHub Actions s'activa
        ↓
Python consulta pitch.cat dia per dia (60 dies)
        ↓
Parseja els tornejos (camp, nom, modalitat, hora...)
        ↓
Escriu tot al Google Sheet automàticament
```

## Estructura del Google Sheet

| Data | Camp | Torneig | Modalitat | Categoria | Hora | Inscripcions | Font |
|------|------|---------|-----------|-----------|------|--------------|------|
| 15/03/2025 | Vallromanes | Open Primavera | Individual | Absolut | 09:00 | Oberta | pitch.cat |

## Afegir més fonts (opcional)

Pots ampliar el scraper editant `scraper.py` i afegint noves funcions
`fetch_from_NOMCLUB()` seguint el mateix patró.

## Costos

- GitHub Actions: **Gratis** (2.000 minuts/mes gratuïts, aquest script usa ~2min/dia)
- Google Sheets API: **Gratis**
- Total: **0€**
