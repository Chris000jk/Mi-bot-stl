import os
import requests
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
CRYPTOCLOUD_API_KEY = os.getenv("CRYPTOCLOUD_API_KEY")
CRYPTOCLOUD_SHOP_ID = os.getenv("CRYPTOCLOUD_SHOP_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

PRODUCTOS = {
    "rueda": {
        "nombre": "🏍️ Rueda de Moto",
        "precio": 10.0,
        "foto": "https://drive.google.com/uc?export=download&id=1OceXb1_I85OP2r0iAYfQGplk2ArTiIuT",
        "archivo_url": "https://drive.google.com/uc?export=download&id=1F6ygJKkBBdWSwubZzWcnnZcompdrJYxV"
    }
}

def crear_factura(amount, order_id):
    url = "https://api.cryptocloud.plus/v1/invoice/create"
    headers = {"Authorization": f"Token {CRYPTOCLOUD_API_KEY}"}
    data = {"shop_id": CRYPTOCLOUD_SHOP_ID, "amount": amount, "order_id": order_id}
    try:
        return requests.post(url, json=data, headers=headers).json()
    except:
        return None

async def start(update, context):
    keyboard = [[InlineKeyboardButton("📦 Ver Catálogo", callback_data="catalogo")]]
    await update.message.reply_text(
        "🔧 *Bienvenido a mi tienda de archivos STL* 🔧\n\nPagos en USDT.\nPresiona el botón para ver productos.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def catalogo(update, context):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton(f"{p['nombre']} - {p['precio']} USDT", callback_data=f"comprar_{k}")] for k, p in PRODUCTOS.items()]
    await query.edit_message_text("🛒 *Selecciona:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def comprar(update, context, product_key):
    query = update.callback_query
    await query.answer()
    prod = PRODUCTOS[product_key]
    import time
    order_id = f"{update.effective_user.id}_{int(time.time())}"
    factura = crear_factura(prod["precio"], order_id)
    if not factura or not factura.get("result"):
        await query.edit_message_text("❌ Error al crear factura.")
        return
    context.user_data["prod_key"] = product_key
    keyboard = [[InlineKeyboardButton("💳 Pagar", url=factura["result"]["pay_url"])], [InlineKeyboardButton("✅ Ya pagué", callback_data="verificar")]]
    await query.edit_message_text(f"🛒 *{prod['nombre']}* - {prod['precio']} USDT\n\n🔗 Paga y presiona '✅ Ya pagué'", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def verificar(update, context):
    query = update.callback_query
    await query.answer()
    prod_key = context.user_data.get("prod_key")
    if not prod_key or prod_key not in PRODUCTOS:
        await query.edit_message_text("❌ Error.")
        return
    prod = PRODUCTOS[prod_key]
    await query.edit_message_text(f"🎉 *¡PAGO CONFIRMADO!*\n\n📥 Descarga: {prod['archivo_url']}", parse_mode="Markdown", disable_web_page_preview=True)
    context.user_data.clear()

# Líneas para que Render no se queje por falta de puerto
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running!')

def run_webserver():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

# Iniciar el servidor web en un hilo separado
Thread(target=run_webserver, daemon=True).start()

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(catalogo, pattern="^catalogo$"))
    app.add_handler(CallbackQueryHandler(verificar, pattern="^verificar$"))
    app.add_handler(CallbackQueryHandler(lambda u,c: comprar(u,c,u.callback_query.data.split("_")[1]), pattern="^comprar_"))
    print("🚀 Bot corriendo...")
    app.run_polling()

if __name__ == "__main__":
    main()
