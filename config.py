import os

# === CREDENCIALES ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "8759115195:AAEUEQ-a2kvjwv6SL70RR7XFceNYmw1TzzE")
CHAT_ID = os.getenv("CHAT_ID", "1803571733")
AFFILIATE_LINK = os.getenv("AFFILIATE_LINK", "https://meli.la/1Y2v7jp")

# === CONFIGURACIÓN DE BÚSQUEDA ===
MIN_DISCOUNT_PERCENT = 40       # Descuento mínimo para publicar
MAX_PRODUCTS_PER_RUN = 10       # Máx. productos por ciclo
SEEN_IDS_LIMIT = 100            # Cuántos IDs recordar para no duplicar
SEARCH_INTERVAL_HOURS = 1       # Frecuencia de búsqueda

# === CATEGORÍAS A BUSCAR ===
# IDs de categorías de Mercado Libre México
# Ref: https://api.mercadolibre.com/sites/MLM/categories
SEARCH_QUERIES = [
    "electronica",
    "celulares",
    "laptops",
    "audifonos",
    "smartwatch",
    "televisores",
    "tablets",
    "videojuegos",
]

# === MERCADO LIBRE API ===
ML_SITE = "MLM"   # México
ML_API_BASE = "https://api.mercadolibre.com"
ML_SEARCH_LIMIT = 50   # items por búsqueda (máx 50 en API pública)
