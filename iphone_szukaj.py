import json
import os
import time
from pathlib import Path

import requests

# ====== USTAWIENIA - ZMIEŃ pod siebie ======
ZAPYTANIE = "iphone 13"      # model, którego szukasz
MAX_CENA = 1800              # maksymalna cena w zł
CO_ILE_MINUT = 10            # jak często sprawdzać
NTFY_TEMAT = os.environ.get("NTFY_TEMAT", "iphone-oferty-ZMIEN-MNIE-123")
# ===========================================

API_URL = "https://www.olx.pl/api/v1/offers/"
PLIK_WIDZIANE = Path("widziane.json")


def wczytaj_widziane():
    if PLIK_WIDZIANE.exists():
        return set(json.loads(PLIK_WIDZIANE.read_text()))
    return set()


def zapisz_widziane(widziane):
    PLIK_WIDZIANE.write_text(json.dumps(sorted(widziane)))


def pobierz_oferty():
    params = {
        "query": ZAPYTANIE,
        "limit": 40,
        "sort_by": "created_at:desc",
        "filter_float_price:to": MAX_CENA,
    }
    odp = requests.get(
        API_URL,
        params=params,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    odp.raise_for_status()
    return odp.json().get("data", [])


def cena_oferty(oferta):
    for p in oferta.get("params", []):
        if p.get("key") == "price":
            return p.get("value", {}).get("value")
    return None


def powiadom(tekst, link):
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TEMAT}",
            data=tekst.encode("utf-8"),
            headers={"Click": link},
            timeout=15,
        )
    except Exception as e:
        print(f"Nie udało się wysłać powiadomienia: {e}")


def sprawdz():
    pierwszy_raz = not PLIK_WIDZIANE.exists()
    widziane = wczytaj_widziane()
    nowe = 0
    for oferta in pobierz_oferty():
        id_oferty = str(oferta["id"])
        if id_oferty in widziane:
            continue
        widziane.add(id_oferty)
        if pierwszy_raz:
            continue
        nowe += 1
        print(f"\nNowa oferta: {oferta['title']}")
        print(f"   Cena: {cena_oferty(oferta)} zł")
        print(f"   Link: {oferta['url']}")
        powiadom(f"{oferta['title']} - {cena_oferty(oferta)} zł", oferta["url"])
    zapisz_widziane(widziane)
    if nowe == 0:
        print("Brak nowych ofert.")


if __name__ == "__main__":
    if os.environ.get("RUN_ONCE"):
        sprawdz()
        raise SystemExit
    print(f"Szukam: '{ZAPYTANIE}' do {MAX_CENA} zł (co {CO_ILE_MINUT} min).")
    while True:
        try:
            sprawdz()
        except Exception as e:
            print(f"Błąd: {e}")
        time.sleep(CO_ILE_MINUT * 60)
