from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import requests
import re

# ==========================================================
# 1) Hent et ferskt token fra NAV
# ==========================================================
respons = requests.get("https://pam-stilling-feed.nav.no/api/publicToken")
raat_svar = respons.text.strip().replace("\n", "").replace("\r", "")
token = raat_svar.split("Feed:")[-1] if "Feed:" in raat_svar else raat_svar

# ==========================================================
# 2) Tidsfilter: KUN de siste 14 dagene
# ==========================================================
siden = datetime.now(timezone.utc) - timedelta(days=14)
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "If-Modified-Since": format_datetime(siden),
}

# Søkeord tilpasset matbutikker og sommer-/deltidsjobber
BUTIKK_ORD = ["kiwi", "rema", "meny", "joker", "coop", "spar", "dagligvare", "butikkmedarbeider", "matbutikk"]
JOBB_TYPE = ["sommervikar", "sommerjobb", "ekstrahjelp", "deltid", "sesong", "medarbeider", "butikkjobb", "teamet", "turnus"]

neste_url = "https://pam-stilling-feed.nav.no/api/v1/feed"
antall_treff = 0
side_nummer = 1

print(f"Søker etter aktive sommer- og deltidsjobber i matbutikker i Oslo...")
print(f"Henter KUN annonser fra de siste 14 dagene.\n")

while neste_url:
    # Fiks for NAVs ufullstendige lenker
    if neste_url.startswith("/"):
        neste_url = f"https://pam-stilling-feed.nav.no{neste_url}"
        
    svar = requests.get(neste_url, headers=headers)
    
    # 304 betyr at det ikke finnes flere nye annonser i dette tidsrommet
    if svar.status_code in [304, 404]:
        break
    if svar.status_code != 200:
        break
        
    data = svar.json()
    items = data.get("items", [])
    
    if not items:
        break
        
    print(f"Skanner side {side_nummer} ({len(items)} nye/endrede annonser)...")

    for item in items:
        if item.get("status") != "ACTIVE":
            continue

        # Gjør hele annonse-objektet til tekst for maksimal treffsikkerhet
        raatekst = str(item).lower()

        # --- FILTER 1: Er det i Oslo? ---
        postnummer_treff = re.search(r"'postalcode':\s*'(\d{4})'", raatekst)
        postnummer = postnummer_treff.group(1) if postnummer_treff else ""
        
        er_i_oslo = "oslo" in raatekst or (postnummer and postnummer.startswith("0"))
        if not er_i_oslo:
            continue

        # --- FILTER 2: Er det en matbutikk? ---
        er_dagligvare = any(ordet in raatekst for ordet in BUTIKK_ORD)
        if not er_dagligvare:
            continue

        # --- FILTER 3: Er det en aktuell jobbtype? ---
        er_aktuell_type = any(ordet in raatekst for ordet in JOBB_TYPE)
        if not er_aktuell_type:
            continue

        # Match funnet!
        antall_treff += 1

        fe = item.get("_feed_entry", {})
        tittel = item.get("title") or fe.get("title") or "Butikkmedarbeider"
        
        bedrift = item.get("businessName") or fe.get("businessName")
        if not bedrift:
            employer_obj = item.get("employer", {}) or fe.get("employer", {})
            bedrift = employer_obj.get("name", "Dagligvarebutikk")

        er_frogner = "frogner" in raatekst or postnummer.startswith("02")
        lokasjon_merke = "Frogner (Nabolaget ditt! 📍)" if er_frogner else f"Oslo (Postnr: {postnummer or 'Oslo'})"

        print(f"\n🎯 MATCH NR. {antall_treff}")
        print(f"STILLING: {tittel}")
        print(f"BUTIKK:   {bedrift}")
        print(f"OMRÅDE:   {lokasjon_merke}")
        print("-" * 40)

    neste_url = data.get("next_url")
    side_nummer += 1

print(f"\nFerdig! Fant totalt {antall_treff} aktuelle butikkjobber i Oslo publisert/endret de siste 14 dagene.")