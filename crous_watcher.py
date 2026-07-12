"""
Crous Watcher
=============
Surveille trouverunlogement.lescrous.fr et envoie une notification Telegram
dès qu'un nouveau logement apparaît dans les codes postaux ciblés.

Variables d'environnement requises :
    TELEGRAM_BOT_TOKEN : token du bot Telegram (obtenu via @BotFather)
    TELEGRAM_CHAT_ID   : identifiant du chat/utilisateur à notifier

Fichier d'état :
    state.json : liste des identifiants de logements déjà vus. Ce fichier
    est mis à jour à chaque exécution et recommité dans le dépôt par le
    workflow GitHub Actions.
"""

import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# 47 = campagne 2026-2027. Pour l'année en cours, utiliser 42 à la place.
SEARCH_URL = "https://trouverunlogement.lescrous.fr/tools/47/search"
BASE_DOMAIN = "https://trouverunlogement.lescrous.fr"

# Codes postaux ciblés (Lyon et alentours proches de Rockefeller)
TARGET_POSTAL_CODES = [
    "69002", "69003", "69004", "69005", "69006", "69007", "69008",
    "69100", "69500", "69200", "69120",
]

STATE_FILE = Path(__file__).parent / "state.json"
MAX_PAGES = 15          # garde-fou pour éviter une boucle infinie
REQUEST_TIMEOUT = 20    # secondes
DELAY_BETWEEN_PAGES = 1 # secondes, pour rester correct vis-à-vis du site

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CrousWatcher/1.0; +https://github.com/)"
}

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


# ---------------------------------------------------------------------------
# Récupération et parsing des pages
# ---------------------------------------------------------------------------

def fetch_page(page: int) -> str:
    url = SEARCH_URL if page == 1 else f"{SEARCH_URL}?page={page}"
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def parse_listings(html_text: str) -> list[dict]:
    """Extrait les annonces d'une page de résultats.

    On repère les liens vers /accommodations/<id>, puis on remonte au
    conteneur (li) le plus proche pour en extraire tout le texte (adresse,
    prix, etc.). Cette approche est volontairement générique afin de
    résister à de petits changements de mise en page du site.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    listings = []
    seen_ids = set()

    for link in soup.select('a[href*="/accommodations/"]'):
        href = link.get("href", "")
        match = re.search(r"/accommodations/(\d+)", href)
        if not match:
            continue
        acc_id = match.group(1)
        if acc_id in seen_ids:
            continue
        seen_ids.add(acc_id)

        container = link.find_parent("li") or link.parent
        text = container.get_text(" ", strip=True) if container else link.get_text(strip=True)
        title = link.get_text(strip=True) or "Logement Crous"
        full_url = href if href.startswith("http") else BASE_DOMAIN + href

        listings.append({
            "id": acc_id,
            "title": title,
            "text": text,
            "url": full_url,
        })

    return listings


def matches_target_area(listing: dict) -> bool:
    return any(code in listing["text"] for code in TARGET_POSTAL_CODES)


def collect_matching_listings() -> dict[str, dict]:
    matches: dict[str, dict] = {}
    page = 1

    while page <= MAX_PAGES:
        try:
            html_text = fetch_page(page)
        except requests.RequestException as exc:
            print(f"Erreur réseau page {page} : {exc}")
            break

        listings = parse_listings(html_text)
        if not listings:
            break

        for item in listings:
            if matches_target_area(item):
                matches[item["id"]] = item

        page += 1
        time.sleep(DELAY_BETWEEN_PAGES)

    return matches


# ---------------------------------------------------------------------------
# Etat (fichier state.json)
# ---------------------------------------------------------------------------

def load_previous_ids() -> set | None:
    """Retourne None si c'est la toute première exécution (pas de fichier)."""
    if not STATE_FILE.exists():
        return None
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return set(data.get("seen_ids", []))
    except (json.JSONDecodeError, OSError):
        return None


def save_ids(ids: set) -> None:
    STATE_FILE.write_text(
        json.dumps({"seen_ids": sorted(ids)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def send_telegram_message(text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": False,
    }
    resp = requests.post(url, data=payload, timeout=15)
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------------

def main() -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("TELEGRAM_BOT_TOKEN et/ou TELEGRAM_CHAT_ID manquants. Arrêt.")
        sys.exit(1)

    previous_ids = load_previous_ids()
    matches = collect_matching_listings()
    print(f"{len(matches)} logement(s) trouvé(s) dans les codes postaux ciblés.")

    if previous_ids is None:
        # Première exécution : on enregistre l'état de référence sans notifier,
        # pour ne pas recevoir un message pour chaque logement déjà en ligne.
        print("Premier lancement : initialisation du fichier d'état, sans notification.")
        save_ids(set(matches.keys()))
        return

    new_ids = set(matches.keys()) - previous_ids

    for acc_id in new_ids:
        item = matches[acc_id]
        message = f"Nouveau logement Crous disponible :\n\n{item['title']}\n{item['url']}"
        try:
            send_telegram_message(message)
            print(f"Notification envoyée pour l'annonce {acc_id}.")
        except requests.RequestException as exc:
            print(f"Echec d'envoi Telegram pour {acc_id} : {exc}")

    save_ids(set(matches.keys()))


if __name__ == "__main__":
    main()
