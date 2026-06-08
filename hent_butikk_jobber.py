from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import re
import requests

respons = requests.get("https://pam-stilling-feed.nav.no/api/publicToken")
raat_svar = respons.text.strip().replace("\n", "").replace("\r", "")
token = raat_svar.split("Feed:")[-1] if "Feed:" in raat_svar else raat_svar

siden = datetime.now(timezone.utc) - timedelta(days=30)
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "If-Modified-Since": format_datetime(siden),
}

BUTIKK_ORD = ["kiwi", "rema", "meny", "joker", "coop", "spar", "dagligvare", "butikkmedarbeider", "matbutikk"]
FROGNER_POSTNR = 267
MAKS_SIDER = 30

neste_url = "https://pam-stilling-feed.nav.no/api/v1/feed"
side_nummer = 1
alle_treff = []

print("Søker etter butikkjobber i Oslo...\n")

while neste_url and side_nummer <= MAKS_SIDER:
    if neste_url.startswith("/"):
        neste_url = f"https://pam-stilling-feed.nav.no{neste_url}"

    svar = requests.get(neste_url, headers=headers)

    if svar.status_code == 304:
        break
    if svar.status_code != 200:
        print(f"Feil fra server: {svar.status_code}")
        break

    data = svar.json()
    items = data.get("items", [])
    if not items:
        break

    print(f"Skanner side {side_nummer} ({len(items)} annonser)...")

    for item in items:
        fe = item.get("_feed_entry", {})
        if fe.get("status") != "ACTIVE":
            continue
        if fe.get("municipal", "").upper() != "OSLO":
            continue
        soketekst = f"{fe.get('title', '')} {fe.get('businessName', '')}".lower()
        if not any(ordet in soketekst for ordet in BUTIKK_ORD):
            continue
        alle_treff.append(item)

    neste_url = data.get("next_url")
    side_nummer += 1

print(f"\nFant {len(alle_treff)} treff — henter postnummer for å rangere etter avstand til Frogner...\n")

def hent_postnummer(item):
    url = item.get("url", "")
    if url.startswith("/"):
        url = f"https://pam-stilling-feed.nav.no{url}"
    try:
        svar = requests.get(url, headers=headers, timeout=5)
        if svar.status_code == 200:
            match = re.search(r"postalcode['\"]:\s*['\"]?(\d{4})", str(svar.json()).lower())
            if match:
                return match.group(1)
    except Exception:
        pass
    return ""

rangerte = []
for item in alle_treff:
    fe = item.get("_feed_entry", {})
    tittel = fe.get("title") or item.get("title") or "Butikkmedarbeider"
    bedrift = fe.get("businessName") or "Dagligvarebutikk"
    postnr = hent_postnummer(item)
    try:
        avstand = abs(int(postnr) - FROGNER_POSTNR)
    except ValueError:
        avstand = 9999
    rangerte.append({"tittel": tittel, "bedrift": bedrift, "postnr": postnr, "avstand": avstand})

rangerte.sort(key=lambda x: x["avstand"])

print("Topp 20 nærmeste butikkjobber til Frogner:\n")
for i, jobb in enumerate(rangerte[:20], 1):
    sted = f"Postnr {jobb['postnr']}" if jobb["postnr"] else "Oslo (ukjent postnr)"
    print(f"🎯 {i}. {jobb['tittel']}")
    print(f"   {jobb['bedrift']} — {sted}")
    print("-" * 40)
