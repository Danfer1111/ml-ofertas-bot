import logging
import asyncio
import random
import threading
from collections import deque
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import (
    BOT_TOKEN, CHAT_ID, SEARCH_QUERIES,
    SEEN_IDS_LIMIT, MAX_PRODUCTS_PER_RUN, SEARCH_INTERVAL_HOURS
)
from mercadolibre import search_deals, format_message

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")

# ── Estado global ─────────────────────────────────────────────────────────────
seen_ids: deque = deque(maxlen=SEEN_IDS_LIMIT)


# ── Health-check server (requerido por Render Web Service) ───────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass  # silenciar logs del servidor HTTP


def start_health_server():
    port = int(__import__("os").environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health server corriendo en puerto {port}")


async def send_deal(bot: Bot, deal: dict) -> bool:
    """Envía una oferta al chat de Telegram (foto + caption)."""
    text = format_message(deal)
    try:
        if deal.get("thumbnail"):
            await bot.send_photo(
                chat_id=CHAT_ID,
                photo=deal["thumbnail"],
                caption=text,
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False,
            )
        return True
    except TelegramError as e:
        logger.error(f"Error enviando oferta {deal['id']}: {e}")
        return False


async def run_search(bot: Bot) -> None:
    """Ciclo principal: busca ofertas en todas las queries y las publica."""
    logger.info("=" * 60)
    logger.info(f"Iniciando búsqueda — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"IDs ya vistos: {len(seen_ids)}")

    all_deals: list[dict] = []

    for query in SEARCH_QUERIES:
        deals = search_deals(query)
        for d in deals:
            if d["id"] not in seen_ids:
                all_deals.append(d)

    if not all_deals:
        logger.info("Sin ofertas nuevas en este ciclo.")
        return

    # Ordenar por mayor descuento primero
    all_deals.sort(key=lambda x: x["discount"], reverse=True)

    # Eliminar duplicados por ID (mismo producto puede aparecer en varias queries)
    seen_this_run: set = set()
    unique_deals = []
    for d in all_deals:
        if d["id"] not in seen_this_run:
            seen_this_run.add(d["id"])
            unique_deals.append(d)

    to_send = unique_deals[:MAX_PRODUCTS_PER_RUN]
    logger.info(f"Publicando {len(to_send)} oferta(s) nuevas...")

    sent = 0
    for deal in to_send:
        ok = await send_deal(bot, deal)
        if ok:
            seen_ids.append(deal["id"])
            sent += 1
            logger.info(
                f"  ✓ [{deal['id']}] {deal['title'][:50]}... "
                f"| -{deal['discount']}% "
                f"| ${deal['current_price']:,.0f}"
            )
            # Pausa entre mensajes para no saturar la API de Telegram
            await asyncio.sleep(random.uniform(1.5, 3.0))

    logger.info(f"Ciclo finalizado — {sent} oferta(s) enviadas.")


async def startup_message(bot: Bot) -> None:
    """Mensaje de inicio cuando el bot arranca."""
    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=(
                "🤖 *Bot de Ofertas ML activado*\n"
                f"Buscaré ofertas con ≥40% de descuento cada {SEARCH_INTERVAL_HOURS}h.\n"
                "¡La primera búsqueda comienza ahora! 🔍"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
    except TelegramError as e:
        logger.warning(f"No se pudo enviar mensaje de inicio: {e}")


async def main() -> None:
    # Levantar servidor HTTP antes que todo (Render lo necesita para no matar el proceso)
    start_health_server()

    bot = Bot(token=BOT_TOKEN)

    # Verificar credenciales
    try:
        me = await bot.get_me()
        logger.info(f"Bot autenticado: @{me.username} (id={me.id})")
    except TelegramError as e:
        logger.critical(f"Error autenticando bot: {e}")
        return

    # Diagnóstico: mostrar CHAT_ID configurado
    logger.info(f"CHAT_ID configurado: {CHAT_ID}")
    logger.info("Si ves 'Chat not found', abre Telegram, busca tu bot y envíale /start primero.")

    await startup_message(bot)

    # Ejecutar búsqueda inmediata al arrancar
    await run_search(bot)

    # Scheduler: repetir cada N horas
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_search,
        trigger="interval",
        hours=SEARCH_INTERVAL_HOURS,
        args=[bot],
        id="ml_search",
        name="Búsqueda Mercado Libre",
        misfire_grace_time=300,  # tolera 5 min de retraso
    )
    scheduler.start()
    logger.info(f"Scheduler activo — búsqueda cada {SEARCH_INTERVAL_HOURS}h")

    # Mantener el proceso vivo
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot detenido por el usuario.")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
