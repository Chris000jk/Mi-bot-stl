import os
import requests
import time
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# ========== VARIABLES DE ENTORNO ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
CRYPTOCLOUD_API_KEY = os.getenv("CRYPTOCLOUD_API_KEY")
CRYPTOCLOUD_SHOP_ID = os.getenv("CRYPTOCLOUD_SHOP_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# ========== VERIFICACIÓN DE ERRORES ==========
print(f"🔍 BOT_TOKEN: {'✅ OK' if BOT_TOKEN else '❌ FALTA'}")
print(f"🔍 CRYPTOCLOUD_API_KEY: {'✅ OK' if CRYPTOCLOUD_API_KEY else '❌ FALTA'}")
print(f"🔍 CRYPTOCLOUD_SHOP_ID: {'✅ OK' if CRYPTOCLOUD_SHOP_ID else '❌ FALTA'}")
print(f"🔍 ADMIN_ID: {ADMIN_ID if ADMIN_ID else '❌ FALTA'}")

if not CRYPTOCLOUD_API_KEY or not CRYPTOCLOUD_SHOP_ID:
    print("⚠️ ADVERTENCIA: CryptoCloud no configurado. El bot funcionará pero no podrá crear facturas.")

# ========== PRODUCTO ==========
PRODUCTOS = {
    "carro": {
        "nombre": "🚗 Hummer RC",
        "precio": 15.0,
        "fotos": [
            "https://drive.google.com/uc?export=download&id=1gKk_OOR2NRHgNMorcAa9Kf8BA7XXIINm",
            "https://drive.google.com/uc?export=download&id=1SbguFbhSlLfilMyHGYXpioxrXfeDygVd",
            "https://drive.google.com/uc?export=download&id=17VvvUeuyc8nn6wSRcjsYx3qGa3-djjMh",
            "https://drive.google.com/uc?export=download&id=12UF7SVcQuGDdz2Sp7RV58bMwW5ARwm0S"
        ],
        "descripcion": "✅ INCLUYE: STL + STEP + SLDPRT + SLDASM\n\n🔥 15 USD",
        "archivo_url": "https://drive.google.com/uc?export=download&id=1UCpYCM4ueRSeSdEHYKnDKmWOewsKeqd6"
    }
}

# ========== CRYPTOCLOUD ==========
def crear_factura(amount, order_id):
    if not CRYPTOCLOUD_API_KEY or not CRYPTOCLOUD_SHOP_ID:
        print("❌ No se puede crear factura: falta API Key o Shop ID")
        return None
    
    url = "https://api.cryptocloud.plus/v2/invoice/create"
    headers = {"Authorization": f"Token {CRYPTOCLOUD_API_KEY}"}
    data = {"shop_id": CRYPTOCLOUD_SHOP_ID, "amount": amount, "order_id": order_id}
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        print(f"📡 Respuesta CryptoCloud: {response.status_code}")
        return response.json()
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# ========== COMANDOS ==========
async def start(update, context):
    keyboard = [[InlineKeyboardButton("📦 VER CATÁLOGO", callback_data="catalogo")]]
    await update.message.reply_text(
        "🔧 *MI TIENDA DE STL* 🔧\n\n👇 Presiona el botón:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def catalogo(update, context):
    query = update.callback_query
    await query.answer()
    await query.delete_message()
    
    prod = PRODUCTOS["carro"]
    
    media_group = []
    for i, foto_url in enumerate(prod["fotos"]):
        if i == 0:
            media_group.append(InputMediaPhoto(
                media=foto_url,
                caption=f"*{prod['nombre']}*\n💰 {prod['precio']} USD\n\n{prod['descripcion']}",
                parse_mode="Markdown"
            ))
        else:
            media_group.append(InputMediaPhoto(media=foto_url))
    
    await query.message.reply_media_group(media=media_group)
    
    keyboard = [[InlineKeyboardButton(f"💰 COMPRAR - {prod['precio']} USD", callback_data="comprar")]]
    await query.message.reply_text(
        "👇 Presiona COMPRAR 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def comprar(update, context):
    query = update.callback_query
    await query.answer()
    
    prod = PRODUCTOS["carro"]
    order_id = f"{update.effective_user.id}_{int(time.time())}"
    
    factura = crear_factura(prod["precio"], order_id)
    
    if not factura or not factura.get("result"):
        await query.edit_message_text(
            "❌ *Error al crear la factura*\n\n"
            "Verifica que CryptoCloud esté configurado correctamente.\n\n"
            f"API Key: {'✅' if CRYPTOCLOUD_API_KEY else '❌ FALTA'}\n"
            f"Shop ID: {'✅' if CRYPTOCLOUD_SHOP_ID else '❌ FALTA'}",
            parse_mode="Markdown"
        )
        return
    
    context.user_data["prod_key"] = "carro"
    
    keyboard = [
        [InlineKeyboardButton("💳 PAGAR", url=factura["result"]["pay_url"])],
        [InlineKeyboardButton("✅ YA PAGUÉ", callback_data="verificar")],
        [InlineKeyboardButton("🔙 VOLVER", callback_data="catalogo")]
    ]
    
    await query.edit_message_text(
        f"🛒 *{prod['nombre']}*\n💰 {prod['precio']} USD\n\n1️⃣ Paga\n2️⃣ Presiona YA PAGUÉ",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def verificar(update, context):
    query = update.callback_query
    await query.answer()
    
    prod_key = context.user_data.get("prod_key")
    if not prod_key:
        await query.edit_message_text("❌ No hay compra activa. Usa /start")
        return
    
    prod = PRODUCTOS[prod_key]
    
    await query.edit_message_text(
        f"🎉 *¡PAGO CONFIRMADO!*\n\n📥 {prod['archivo_url']}\n\n¡Gracias!",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    context.user_data.clear()

# ========== SERVIDOR ==========
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running!')

def run_webserver():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

Thread(target=run_webserver, daemon=True).start()

# ========== MAIN ==========
def main():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN no configurado")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(catalogo, pattern="catalogo"))
    app.add_handler(CallbackQueryHandler(comprar, pattern="comprar"))
    app.add_handler(CallbackQueryHandler(verificar, pattern="verificar"))
    
    print("🚀 Bot corriendo")
    app.run_polling()

if __name__ == "__main__":
    main()
