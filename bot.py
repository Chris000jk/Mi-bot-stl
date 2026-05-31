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

# ========== PRODUCTO: HUMMER RC ==========
PRODUCTOS = {
    "carro_hummer": {
        "nombre": "🚗 Hummer RC - Completo con Ensamble",
        "precio": 15.0,
        "fotos": [
            "https://drive.google.com/uc?export=download&id=1gKk_OOR2NRHgNMorcAa9Kf8BA7XXIINm",
            "https://drive.google.com/uc?export=download&id=1SbguFbhSlLfilMyHGYXpioxrXfeDygVd",
            "https://drive.google.com/uc?export=download&id=17VvvUeuyc8nn6wSRcjsYx3qGa3-djjMh",
            "https://drive.google.com/uc?export=download&id=12UF7SVcQuGDdz2Sp7RV58bMwW5ARwm0S"
        ],
        "descripcion": "📦 CARROCERÍA + RUEDAS + ENSAMBLE COMPLETO\n\n"
                       "📏 Tamaño: 20cm x 10cm x 10cm\n"
                       "🔧 Fácil de imprimir y armar\n"
                       "⚙️ Piezas ensamblables\n\n"
                       "✅ INCLUYE:\n"
                       "• STL (para imprimir)\n"
                       "• STEP (para modificar en CAD)\n"
                       "• SLDPRT (piezas en SolidWorks)\n"
                       "• SLDASM (ensamble completo en SolidWorks)\n\n"
                       "🔥 TODO por solo 15 USD\n"
                       "💳 Pagos en USDT (Trust Wallet)",
        "archivo_url": "https://drive.google.com/uc?export=download&id=1UCpYCM4ueRSeSdEHYKnDKmWOewsKeqd6"
    }
}

# ========== FUNCIONES CRYPTOCLOUD ==========
def crear_factura(amount, order_id):
    url = "https://api.cryptocloud.plus/v2/invoice/create"
    headers = {"Authorization": f"Token {CRYPTOCLOUD_API_KEY}"}
    data = {"shop_id": CRYPTOCLOUD_SHOP_ID, "amount": amount, "order_id": order_id}
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        return response.json()
    except Exception as e:
        print(f"Error crear factura: {e}")
        return None

# ========== COMANDOS ==========
async def start(update, context):
    keyboard = [[InlineKeyboardButton("📦 VER CATÁLOGO", callback_data="catalogo")]]
    await update.message.reply_text(
        "🔧 *MI TIENDA DE STL* 🔧\n\n"
        "🚗 Diseños en SolidWorks para impresión 3D\n"
        "💰 Pagos en USDT (Trust Wallet)\n"
        "✅ Entrega automática\n\n"
        "👇 Presiona el botón para ver los productos:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def catalogo(update, context):
    query = update.callback_query
    await query.answer()
    await query.delete_message()
    
    prod = PRODUCTOS["carro_hummer"]
    
    # Crear galería con las 4 fotos
    media_group = []
    for i, foto_url in enumerate(prod["fotos"]):
        if i == 0:
            media_group.append(InputMediaPhoto(
                media=foto_url,
                caption=f"*{prod['nombre']}*\n\n"
                       f"💰 *Precio:* {prod['precio']} USD\n\n"
                       f"{prod['descripcion']}\n\n"
                       f"🔧 *Desliza para ver más fotos* 👉",
                parse_mode="Markdown"
            ))
        else:
            media_group.append(InputMediaPhoto(media=foto_url))
    
    # Enviar galería
    await query.message.reply_media_group(media=media_group)
    
    # Enviar botón de compra
    keyboard = [[InlineKeyboardButton(f"💰 COMPRAR - {prod['precio']} USD", callback_data="comprar_carro_hummer")]]
    await query.message.reply_text(
        "👇 *Presiona el botón para comprar* 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def comprar(update, context):
    query = update.callback_query
    await query.answer()
    
    prod = PRODUCTOS["carro_hummer"]
    order_id = f"{update.effective_user.id}_{int(time.time())}"
    
    factura = crear_factura(prod["precio"], order_id)
    
    if not factura or not factura.get("result"):
        await query.edit_message_text(
            "❌ *Error al crear la factura*\n\n"
            "Intenta de nuevo en unos segundos.",
            parse_mode="Markdown"
        )
        return
    
    context.user_data["prod_key"] = "carro_hummer"
    
    keyboard = [
        [InlineKeyboardButton("💳 IR A PAGAR", url=factura["result"]["pay_url"])],
        [InlineKeyboardButton("✅ YA PAGUÉ", callback_data="verificar")],
        [InlineKeyboardButton("🔙 VER CATÁLOGO", callback_data="catalogo")]
    ]
    
    await query.edit_message_text(
        f"🛒 *{prod['nombre']}*\n\n"
        f"💰 *Monto a pagar:* {prod['precio']} USD\n\n"
        f"📝 *Instrucciones:*\n"
        f"1️⃣ Presiona IR A PAGAR\n"
        f"2️⃣ Completa el pago con Trust Wallet\n"
        f"3️⃣ Vuelve aquí y presiona YA PAGUÉ\n\n"
        f"✅ Recibirás tu archivo automáticamente",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def verificar(update, context):
    query = update.callback_query
    await query.answer()
    
    prod_key = context.user_data.get("prod_key")
    if not prod_key or prod_key not in PRODUCTOS:
        await query.edit_message_text(
            "❌ *No hay una compra activa*\n\nUsa /start para ver el catálogo.",
            parse_mode="Markdown"
        )
        return
    
    prod = PRODUCTOS[prod_key]
    
    keyboard = [[InlineKeyboardButton("📦 VER CATÁLOGO", callback_data="catalogo")]]
    
    await query.edit_message_text(
        f"🎉 *¡PAGO CONFIRMADO!* 🎉\n\n"
        f"✨ *{prod['nombre']}*\n\n"
        f"📥 *Descarga tu archivo:*\n{prod['archivo_url']}\n\n"
        f"🔧 ¡Gracias por tu compra!\n\n"
        f"📦 El archivo incluye STL + STEP + SLDPRT + SLDASM",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    
    context.user_data.clear()

# ========== SERVIDOR PARA RENDER ==========
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
    app.add_handler(CallbackQueryHandler(catalogo, pattern="^catalogo$"))
    app.add_handler(CallbackQueryHandler(comprar, pattern="comprar_carro_hummer"))
    app.add_handler(CallbackQueryHandler(verificar, pattern="^verificar$"))
    
    print("🚀 Bot corriendo con galería de 4 fotos...")
    app.run_polling()

if __name__ == "__main__":
    main()
