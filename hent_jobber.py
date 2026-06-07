from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import requests

# 1) Hent et gratis test-token fra NAV og fjern usynlige tegn
respons = requests.get("https://pam-stilling-feed.nav.no/api/publicToken")
raat_svar = respons.text.strip().replace("\n", "").replace("\r", "")

# Her kutter vi bort alt frem til selve tokenet (som alltid starter med eyJ)
token = raat_svar.split("Feed:")[-1] if "Feed:" in raat_svar else raat_svar
print("Renset token vi bruker:", token)


# 2) Be om annonser endret de siste 7 dagene
siden = datetime.now(timezone.utc) - timedelta(days=7)
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "If-Modified-Since": format_datetime(siden),
}


# 3) Hent én side fra feeden
svar = requests.get(
    "https://pam-stilling-feed.nav.no/api/v1/feed", headers=headers
)
data = svar.json()

# 4) Steg 3: Filtrer annonser og finn by/sted

# Definer ordene du faktisk er på jakt etter (bruk små bokstaver her)
NØKKELORD = ["python", "utvikler", "developer", "programmering", "it-konsulent"]

print(f"Statuskode: {svar.status_code} – Sjekker {len(data['items'])} annonser mot filteret...\n")
antall_treff = 0

for item in data["items"]:
    fe = item.get("_feed_entry", {})
    tittel = fe.get("title", "Ingen tittel")
    bedrift = fe.get("businessName", "Ukjent bedrift")
    beskrivelse = fe.get("description", "")
    
    # Slå sammen tittel og beskrivelse og gjør alt til små bokstaver for treffsikker søking
    soketekst = f"{tittel} {beskrivelse}".lower()
    
    # Sjekk om minst ett av nøkkelordene dine finnes i teksten
    har_nøkkelord = any(ordet in soketekst for ordet in NØKKELORD)
    
    # Hvis annonsen IKKE inneholder noen av ordene våre, hopper vi til neste annonse
    if not har_nøkkelord:
        continue
        
    # --- Hvis vi kommer hit, betyr det at annonsen passerte filteret! ---
    antall_treff += 1
    
    # 1. FINN STED/BY: Henter kommune direkte fra NAV sitt eget felt
    sted = fe.get("municipal", "").strip()
    
    # Backup hvis feltet mangler: Sjekk vanlige arbeidsområder eller let i teksten
    if not sted:
        sted = fe.get("extentOfGeographicalArea", "").strip()
        
    if not sted:
        # Enkel backup-sjekk i teksten for de største studiebyene
        if "oslo" in soketekst: sted = "Oslo"
        elif "trondheim" in soketekst: sted = "Trondheim"
        elif "bergen" in soketekst: sted = "Bergen"
        elif "stavanger" in soketekst: sted = "Stavanger"
        else: sted = "Ikke spesifisert"

    # 2. HENT E-POST (samme logg som før)
    epost = "Ingen e-post funnet"
    kontakter = fe.get("contactList", [])
    if kontakter and isinstance(kontakter, list):
        for kontakt in kontakter:
            if kontakt.get("email"):
                epost = kontakt.get("email")
                break
                
    if epost == "Ingen e-post funnet" and beskrivelse:
        import re
        epost_treff = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', beskrivelse)
        if epost_treff:
            epost = epost_treff[0]

    # Print ut den relevante matchen med lokasjon
    print(f"🎯 MATCH NR. {antall_treff}")
    print(f"STILLING: {tittel}")
    print(f"BEDRIFT:  {bedrift}")
    print(f"STED/BY:  {sted}")
    print(f"E-POST:   {epost}")
    print(f"UTDRAG:   {beskrivelse[:120]}...")
    print("-" * 50)

print(f"\nFerdig! Fant {antall_treff} relevante annonser av totalt {len(data['items'])}.")