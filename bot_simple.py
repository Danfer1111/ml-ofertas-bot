"""
Bot de Ofertas ML — versión GitHub Actions
Corre una vez, busca ofertas, envía a Telegram y termina.
El scheduler es el cron de GitHub Actions (.github/workflows/bot.yml)
"""
import os
import json
import logging
import time
import random
import requests
from pathlib import Path

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN      = os.environ["BOT_TOKEN"]
CHAT_ID        = os.environ["CHAT_ID"]
AFFILIATE_LINK = os.environ.get("AFFILIATE_LINK", "https://meli.la/1Y2v7jp")
ML_CLIENT_ID   = os.environ.get("ML_CLIENT_ID", "")
ML_CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET", "")

MIN_DISCOUNT   = 40
MAX_TO_SEND    = 10
ML_SITE        = "MLM"
SEEN_FILE      = "seen_ids.json"   # persiste entre runs via GitHub Actions cache

SEARCH_QUERIES = [
    "electronica", "celulares", "laptops",
    "audifonos", "smartwatch", "televisores",
    "tablets", "videojuegos",
]

# ── Persistencia de IDs vistos (evita duplicados entre ejecuciones) ───────────
def load_seen() -> set:
    if Path(SEEN_FILE).exists():
        try:
            return set(json.loads(Path(SEEN_FILE).read_text()))
        except Exception:
            pass
    return set()

def save_seen(seen: set) -> None:
    # Guardar solo los últimos 200 IDs
    ids = list(seen)[-200:]
    Path(SEEN_FILE).write_text(json.dumps(ids))

# ── OAuth ML ──────────────────────────────────────────────────────────────────
_token: str = ""

def get_token() -> str:
    global _token
    if _token:
        return _token
    if not ML_CLIENT_ID or not ML_CLIENT_SECRET:
        log.warning("Sin credenciales OAuth — intentando sin token")
        return ""
    try:
        r = requests.post(
            "https://api.mercadolibre.com/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": ML_CLIENT_ID,
                "client_secret": ML_CLIENT_SECRET,
            },
            timeout=10,
        )
        r.raise_for_status()
        _token = r.json()["access_token"]
        log.info("Token OAuth obtenido OK")
        return _token
    except Exception as e:
        log.error(f"Error obteniendo token: {e}")
        return ""

# ── Búsqueda en ML ────────────────────────────────────────────────────────────
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "es-MX,es;q=0.9",
})

def search_deals(query: str, seen: set) -> list[dict]:
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        r = SESSION.get(
            f"https://api.mercadolibre.com/sites/{ML_SITE}/search",
            params={"q": query, "limit": 50, "sort": "relevance"},
            headers=headers,
            timeout=15,
        )
        r.raise_for_status()
    except requests.HTTPError as e:
        log.error(f"[{query}] HTTP {e.response.status_code}")
        return []
    except Exception as e:
        log.error(f"[{query}] Error: {e}")
        return []

    deals = []
    for item in r.json().get("results", []):
        item_id = item.get("id")
        if not item_id or item_id in seen:
            continue

        original = item.get("original_price")
        current  = item.get("price")
        if not original or not current or original <= current:
            continue

        discount = round((1 - current / original) * 100, 1)
        if discount < MIN_DISCOUNT:
            continue

        thumbnail = item.get("thumbnail", "").replace("-I.jpg", "-O.jpg")
        deals.append({
            "id":             item_id,
            "title":          item.get("title", ""),
            "original_price": original,
            "current_price":  current,
            "discount":       discount,
            "thumbnail":      thumbnail,
            "permalink":      item.get("permalink", ""),
            "condition":      item.get("condition", "new"),
            "sold_quantity":  item.get("sold_quantity", 0),
        })

    log.info(f"[{query}] {len(deals)} ofertas nuevas con ≥{MIN_DISCOUNT}%")
    return deals

# ── Envío a Telegram ──────────────────────────────────────────────────────────
TG_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

def fmt_price(n: float) -> str:
    return f"${n:,.0f}"

def build_caption(d: dict) -> str:
    cond = {"new": "Nuevo", "used": "Usado", "refurbished": "Reacondicionado"}.get(d["condition"], d["condition"])
    txt = (
        f"🔥 *{d['title']}*\n\n"
        f"💸 ~~{fmt_price(d['original_price'])}~~ → *{fmt_price(d['current_price'])}*\n"
        f"📉 Descuento: *{d['discount']}%*\n"
        f"📦 Estado: {cond}\n"
    )
    if d["sold_quantity"] > 0:
        txt += f"✅ Vendidos: {d['sold_quantity']:,}\n"
    txt += (
        f"\n🛒 [Ver en Mercado Libre]({d['permalink']})\n"
        f"🤝 [Link de afiliado]({AFFILIATE_LINK})"
    )
    return txt

def send_deal(deal: dict) -> bool:
    caption = build_caption(deal)
    try:
        if deal["thumbnail"]:
            r = requests.post(f"{TG_BASE}/sendPhoto", json={
                "chat_id": CHAT_ID,
                "photo": deal["thumbnail"],
                "caption": caption,
                "parse_mode": "Markdown",
            }, timeout=15)
        else:
            r = requests.post(f"{TG_BASE}/sendMessage", json={
                "chat_id": CHAT_ID,
                "text": caption,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            }, timeout=15)

        if not r.ok:
            log.error(f"Telegram error {r.status_code}: {r.text[:100]}")
            return False
        return True
    except Exception as e:
        log.error(f"Error enviando a Telegram: {e}")
        return False

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    log.info("=" * 50)
    log.info("Iniciando búsqueda de ofertas ML")

    seen = load_seen()
    log.info(f"IDs ya vistos: {len(seen)}")

    all_deals: list[dict] = []
    seen_this_run: set = set()

    for query in SEARCH_QUERIES:
        deals = search_deals(query, seen)
        for d in deals:
            if d["id"] not in seen_this_run:
                seen_this_run.add(d["id"])
                all_deals.append(d)
        time.sleep(1)  # pausa entre queries

    if not all_deals:
        log.info("Sin ofertas nuevas en este ciclo.")
        return

    # Ordenar por mayor descuento
    all_deals.sort(key=lambda x: x["discount"], reverse=True)
    to_send = all_deals[:MAX_TO_SEND]
    log.info(f"Enviando {len(to_send)} oferta(s)...")

    sent = 0
    for deal in to_send:
        ok = send_deal(deal)
        if ok:
            seen.add(deal["id"])
            sent += 1
            log.info(f"  ✓ {deal['title'][:50]} | -{deal['discount']}% | {fmt_price(deal['current_price'])}")
            time.sleep(random.uniform(1.5, 3.0))

    save_seen(seen)
    log.info(f"Listo — {sent} oferta(s) enviadas.")

if __name__ == "__main__":
    main()
