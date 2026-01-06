[README.md](https://github.com/user-attachments/files/24453976/README.md)
# DigiMV Prospect Tool - Cloud Versie

🏥 Analyseer Nederlandse zorgorganisaties direct in de browser.

## 🚀 Live Demo

[Open de app](https://digimv-prospect.streamlit.app) *(link werkt na deployment)*

## 📦 Deployment naar Streamlit Cloud

### Stap 1: GitHub Repository

1. Maak een nieuwe GitHub repository
2. Upload deze bestanden:
   - `app.py`
   - `requirements.txt`

### Stap 2: Streamlit Cloud

1. Ga naar [share.streamlit.io](https://share.streamlit.io)
2. Log in met je GitHub account
3. Klik "New app"
4. Selecteer je repository
5. Main file: `app.py`
6. Klik "Deploy!"

De app is binnen enkele minuten live! 🎉

## 📋 Gebruik

### Optie 1: Genereer vanuit bronbestanden

1. Upload de 3 DigiMV Excel bestanden (Part 1, 2, 3)
2. Upload `Nederland.csv` voor provincie/coördinaten
3. Klik "Genereer Master Database"

### Optie 2: Upload bestaande Master

1. Selecteer "Upload Master Excel"
2. Upload je bestaande Master Database Excel
3. Optioneel: upload `Nederland.csv` voor kaartweergave

## 📁 Nederland.csv Formaat

```csv
straat;huisnummer;huisletter;huisnummertoevoeging;postcode;woonplaats;gemeente;provincie;lat;lon
Oostvaardersdiep;1;;;1309AA;Almere;Almere;Flevoland;52.41681018;5.22054682
```

**Vereiste kolommen:** `postcode`, `provincie`, `lat`, `lon`
**Separator:** `;` (puntkomma)

## ✨ Features

- 🗺️ Interactieve kaart van Nederland
- 📋 Sorteerbare tabel met alle organisaties
- 🔍 Filter op type, provincie, omzet
- 💾 Export naar Excel
- 📱 Werkt op desktop en mobiel

## 🔧 Lokaal draaien

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 📄 Licentie

Intern gebruik - Primio
