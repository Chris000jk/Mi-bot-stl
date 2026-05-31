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

# ========== PRODUCTO ==========
PRODUCTOS = {
    "carro": {
        "nombre": "🚗 Hummer RC - Completo con Ensamble",
        "precio": 15.0,
        "fotos": [
            "https://drive.google.com/uc?export=download&id=1gKk_OOR2NRHgNMorcAa9Kf8BA7XXIINm",
            "https://drive.google.com/uc?export=download&id=1SbguFbhSlLfilMyHGYXpioxrXfeDygVd",
            "https://drive.google.com/uc?export=download&id=17VvvUeuyc8nn6wSRcjsYx3qGa3-djjMh",
            "https://drive.google.com/uc?export=download&id=12UF7SVcQuGDdz2Sp7RV58bMwW5ARwm0S"
        ],
        "descripcion": "📦 CARROCERÍA + RUEDAS + ENSAMBLE COMPLETO\n\n"
                       "✅ INCLUYE:\n"
                       "• STL (para imprimir)\n"
                       "• STEP (para modificar en CAD)\n"
                       "• SLDPRT (piezas en SolidWorks)\n"
                       "• SLDASM (ensamble completo)\n\n"
                       "🔥 TODO por solo 15 USD",
        "archivo_url": "https://drive.google.com/uc?export=download&id=1UCpYCM4ueRSeSdEHYKnDKmWOewsKeqd6"
    }
}

# ========== CRYPTOCLOUD ==========
def crear_factura(amount, order_id):
    if not CRYPTOCLOUD_API_KEY:
        return {"error": "Falta CRYPTOCLOUD_API_KEY en Render"}
    if not CRYPTOCLOUD_SHOP_ID:
        return {"error": "Falta CRYPTOCLOUD_SHOP_ID en Render"}
    
    url = "https://api.cryptocloud.plus/v2/invoice/create"
    headers = {"Authorization": f"Token {CRYPTOCLOUD_API_KEY}"}
    data = {"shop_id": CRYPTOCLOUD_SHOP_ID, "amount": amount, "order_id": order_id}
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

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

# ========== COMANDOS DEL BOT ==========
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
    
    prod = PRODUCTOS["carro"]
    
    # Galería de fotos (carrusel)
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
    
    await query.message.reply_media_group(media=media_group)
    
    # Botón de compra
    keyboard = [[InlineKeyboardButton(f"💰 COMPRAR - {prod['precio']} USD", callback_data="comprar")]]
    await query.message.reply_text(
        "👇 *Presiona el botón para comprar* 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def comprar(update, context):
    query = update.callback_query
    await query.answer()
    
    prod = PRODUCTOS["carro"]
    
    # Mostrar mensaje de espera
    await query.edit_message_text("⏳ *Creando factura, espera un momento...*", parse_mode="Markdown")
    
    order_id = f"{update.effective_user.id}_{int(time.time())}"
    respuesta = crear_factura(prod["precio"], order_id)
    
    # Verificar errores de configuración
    if respuesta.get("error"):
        await query.edit_message_text(
            f"❌ *Error de configuración:*\n`{respuesta['error']}`\n\n"
            f"Contacta al administrador.",
            parse_mode="Markdown"
        )
        return
    
    # Verificar respuesta exitosa de CryptoCloud
    if respuesta.get("status") == "success" and respuesta.get("result", {}).get("link"):
        pay_url = respuesta["result"]["link"]
        
        keyboard = [
            [InlineKeyboardButton("💳 PAGAR AHORA", url=pay_url)],
            [InlineKeyboardButton("✅ YA PAGUÉ", callback_data="verificar")],
            [InlineKeyboardButton("🔙 VER CATÁLOGO", callback_data="catalogo")]
        ]
        
        # Detectar si está en modo prueba
        modo = "🔧 *MODO PRUEBA* (no se cobra realmente)" if respuesta["result"].get("test_mode") else "💰 *MODO REAL*"
        
        await query.edit_message_text(
            f"✅ *Factura creada correctamente!*\n\n{modo}\n\n"
            f"🛒 *{prod['nombre']}*\n"
            f"💰 *Monto:* {prod['precio']} USD\n\n"
            f"📝 *Instrucciones:*\n"
            f"1️⃣ Presiona PAGAR AHORA\n"
            f"2️⃣ Completa el pago con Trust Wallet\n"
            f"3️⃣ Vuelve aquí y presiona YA PAGUÉ\n\n"
            f"✅ Recibirás tu archivo automáticamente",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        # Guardar datos para verificación
        context.user_data["prod_key"] = "carro"
    else:
        await query.edit_message_text(
            f"❌ *Respuesta inesperada de CryptoCloud*\n\n"
            f"Intenta de nuevo más tarde.",
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
        f"📦 El archivo incluye: STL + STEP + SLDPRT + SLDASM",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    
    context.user_data.clear()

# ========== MAIN ==========
def main():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN no configurado en Render")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(catalogo, pattern="^catalogo$"))
    app.add_handler(CallbackQueryHandler(comprar, pattern="^comprar$"))
    app.add_handler(CallbackQueryHandler(verificar, pattern="^verificar$"))
    
    print("🚀 Bot corriendo con galería de fotos y CryptoCloud integrado...")
    app.run_polling()

if __name__ == "__main__":
    main()
