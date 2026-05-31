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
        "nombre": "🚗 Hummer RC",
        "precio": 15.0,
        "fotos": [
            "https://drive.google.com/uc?export=download&id=1gKk_OOR2NRHgNMorcAa9Kf8BA7XXIINm",
            "https://drive.google.com/uc?export=download&id=1SbguFbhSlLfilMyHGYXpioxrXfeDygVd",
            "https://drive.google.com/uc?export=download&id=17VvvUeuyc8nn6wSRcjsYx3qGa3-djjMh",
            "https://drive.google.com/uc?export=download&id=12UF7SVcQuGDdz2Sp7RV58bMwW5ARwm0S"
        ],
        "descripcion": "📦 Carrocería + Ruedas + Ensamble Completo\n\n"
                       "✅ Incluye:\n"
                       "• STL (para impresión 3D)\n"
                       "• STEP (para modificar en CAD)\n"
                       "• SLDPRT (piezas SolidWorks)\n"
                       "• SLDASM (ensamble SolidWorks)\n\n"
                       "🔥 Todo por solo 15 USD",
        "archivo_url": "https://drive.google.com/uc?export=download&id=1UCpYCM4ueRSeSdEHYKnDKmWOewsKeqd6"
    }
}

# ========== CRYPTOCLOUD ==========
def crear_factura(amount, order_id):
    if not CRYPTOCLOUD_API_KEY:
        return {"error": "Falta API Key"}
    if not CRYPTOCLOUD_SHOP_ID:
        return {"error": "Falta Shop ID"}
    
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
    foto_bienvenida = "https://drive.google.com/uc?export=download&id=1g4u0wM7nViiEl-RmyZvrYOfo6SxY9zoF"
    
    keyboard = [[InlineKeyboardButton("📦 Ver catálogo", callback_data="catalogo")]]
    
    await update.message.reply_photo(
        photo=foto_bienvenida,
        caption="🔧 *Bienvenido a mi tienda* 🔧\n\n"
                "Diseños en SolidWorks para impresión 3D.\n"
                "Pagos en USDT (Trust Wallet).\n"
                "Entrega automática.\n\n"
                "👇 Presiona el botón para ver los productos:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def catalogo(update, context):
    query = update.callback_query
    await query.answer()
    
    prod = PRODUCTOS["carro"]
    
    # Galería de fotos
    media_group = []
    for i, foto_url in enumerate(prod["fotos"]):
        if i == 0:
            media_group.append(InputMediaPhoto(
                media=foto_url,
                caption=f"*{prod['nombre']}*\n\n"
                       f"💰 Precio: {prod['precio']} USD\n\n"
                       f"{prod['descripcion']}",
                parse_mode="Markdown"
            ))
        else:
            media_group.append(InputMediaPhoto(media=foto_url))
    
    await query.message.reply_media_group(media=media_group)
    
    # Botón de compra debajo de las fotos
    keyboard = [[InlineKeyboardButton(f"💰 Comprar - {prod['precio']} USD", callback_data="comprar")]]
    await query.message.reply_text(
        "👇 Presiona para comprar",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def comprar(update, context):
    query = update.callback_query
    await query.answer()
    
    prod = PRODUCTOS["carro"]
    
    # Mensaje de espera
    await query.edit_message_text("⏳ Creando orden, un momento...")
    
    order_id = f"{update.effective_user.id}_{int(time.time())}"
    respuesta = crear_factura(prod["precio"], order_id)
    
    if respuesta.get("error"):
        await query.edit_message_text(
            f"❌ *Error temporal*\n\n{respuesta['error']}\n\nIntenta de nuevo.",
            parse_mode="Markdown"
        )
        return
    
    if respuesta.get("status") == "success" and respuesta.get("result", {}).get("link"):
        pay_url = respuesta["result"]["link"]
        foto_pago = "https://drive.google.com/uc?export=download&id=1H4U6yimrJENjqwQ2lZWwU3h7JrvY1LG0"
        
        keyboard = [
            [InlineKeyboardButton("💳 Ir a pagar", url=pay_url)],
            [InlineKeyboardButton("✅ Ya pagué", callback_data="verificar")],
            [InlineKeyboardButton("← Volver al catálogo", callback_data="catalogo")]
        ]
        
        # Mensaje con explicación de CryptoCloud
        await query.message.reply_photo(
            photo=foto_pago,
            caption=(
                f"✅ *Orden creada*\n\n"
                f"🛒 {prod['nombre']}\n"
                f"💰 Monto: {prod['precio']} USD\n\n"
                f"📝 *Paso a paso para pagar:*\n"
                f"1️⃣ Presiona 'Ir a pagar'\n"
                f"2️⃣ Selecciona USDT y la red TRC20\n"
                f"3️⃣ Abre Trust Wallet (o tu exchange)\n"
                f"4️⃣ Escanea el código QR o copia la dirección\n"
                f"5️⃣ Envía el monto exacto de {prod['precio']} USD en USDT\n"
                f"6️⃣ Vuelve aquí y presiona '✅ Ya pagué'\n\n"
                f"🔒 *¿Cómo funciona CryptoCloud?*\n\n"
                f"CryptoCloud es un sistema de pagos que **retiene tu dinero** hasta que recibes el archivo.\n\n"
                f"**Paso 1 - Retención segura**\n"
                f"Cuando pagas, CryptoCloud recibe y retiene el dinero. Nadie puede tocarlo.\n\n"
                f"**Paso 2 - Verificación**\n"
                f"El sistema verifica el pago en la blockchain (segundos).\n\n"
                f"**Paso 3 - Entrega**\n"
                f"Nuestro bot recibe la confirmación y te da el enlace de descarga.\n\n"
                f"**Paso 4 - Liberación**\n"
                f"Solo después de que recibes el archivo, CryptoCloud libera el pago.\n\n"
                f"✅ *Beneficios:* Sin registro, 100% automático, respaldado.\n\n"
                f"🔧 *Recibirás tu archivo al instante después de presionar 'Ya pagué'*"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        await query.delete_message()
        context.user_data["prod_key"] = "carro"
    else:
        await query.edit_message_text(
            "❌ *Error al crear la orden*\n\nIntenta de nuevo en unos segundos.",
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
    keyboard = [[InlineKeyboardButton("📦 Ver catálogo", callback_data="catalogo")]]
    
    await query.edit_message_text(
        f"🎉 *¡Pago confirmado!* 🎉\n\n"
        f"✨ {prod['nombre']}\n\n"
        f"📥 *Descarga tu archivo:*\n{prod['archivo_url']}\n\n"
        f"🔧 ¡Gracias por tu compra!\n\n"
        f"📦 Incluye: STL + STEP + SLDPRT + SLDASM",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    context.user_data.clear()

# ========== MAIN ==========
def main():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN no configurado")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(catalogo, pattern="^catalogo$"))
    app.add_handler(CallbackQueryHandler(comprar, pattern="^comprar$"))
    app.add_handler(CallbackQueryHandler(verificar, pattern="^verificar$"))
    
    print("🚀 Bot funcionando correctamente")
    app.run_polling()

if __name__ == "__main__":
    main()
