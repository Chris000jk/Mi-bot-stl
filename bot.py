import os
import requests
import time
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# ========== VARIABLES DE ENTORNO ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

print(f"🔍 BOT_TOKEN: {'✅' if BOT_TOKEN else '❌'}")
print(f"🔍 NOWPAYMENTS_API_KEY: {'✅' if NOWPAYMENTS_API_KEY else '❌'}")

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

# ========== NOWPAYMENTS ==========
def crear_pago(amount, order_id):
    if not NOWPAYMENTS_API_KEY:
        return {"error": "Falta NOWPAYMENTS_API_KEY en Render"}
    
    url = "https://api.nowpayments.io/v1/invoice"
    headers = {
        "x-api-key": NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "price_amount": amount,
        "price_currency": "USD",
        "pay_currency": "USDT_TRC20",
        "order_id": order_id,
        "order_description": f"Compra Hummer RC - {order_id}",
        "is_fixed_rate": True
    }
    
    print(f"📡 Enviando a NOWPayments: {url}")
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        print(f"📡 Status: {response.status_code}")
        
        if response.status_code == 201:
            return response.json()
        elif response.status_code == 401:
            return {"error": "API Key inválida. Verifica en NOWPayments"}
        else:
            return {"error": f"HTTP {response.status_code}: {response.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}

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

# ========== COMANDOS ==========
async def start(update, context):
    foto_bienvenida = "https://drive.google.com/uc?export=download&id=1g4u0wM7nViiEl-RmyZvrYOfo6SxY9zoF"
    
    keyboard = [[InlineKeyboardButton("📦 Ver catálogo", callback_data="catalogo")]]
    
    await update.message.reply_photo(
        photo=foto_bienvenida,
        caption="🔧 *Mi tienda STL* 🔧\n\n"
                "Diseños en SolidWorks para impresión 3D.\n"
                "Pagos en USDT (Trust Wallet).\n"
                "Entrega automática.\n\n"
                "👇 Presiona el botón:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def catalogo(update, context):
    query = update.callback_query
    await query.answer()
    
    prod = PRODUCTOS["carro"]
    
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
    await query.edit_message_text("⏳ Creando orden...")
    
    order_id = f"{update.effective_user.id}_{int(time.time())}"
    respuesta = crear_pago(prod["precio"], order_id)
    
    if respuesta.get("error"):
        await query.edit_message_text(
            f"❌ *Error:*\n`{respuesta['error']}`\n\n"
            f"NOWPAYMENTS_API_KEY: {'✅' if NOWPAYMENTS_API_KEY else '❌'}",
            parse_mode="Markdown"
        )
        return
    
    if respuesta.get("invoice_url"):
        pay_url = respuesta["invoice_url"]
        foto_pago = "https://drive.google.com/uc?export=download&id=1H4U6yimrJENjqwQ2lZWwU3h7JrvY1LG0"
        
        keyboard = [
            [InlineKeyboardButton("💳 Ir a pagar", url=pay_url)],
            [InlineKeyboardButton("✅ Ya pagué", callback_data="verificar")],
            [InlineKeyboardButton("← Volver al catálogo", callback_data="catalogo")]
        ]
        
        await query.message.reply_photo(
            photo=foto_pago,
            caption=(
                f"✅ *Orden creada*\n\n"
                f"🛒 {prod['nombre']}\n"
                f"💰 Monto: {prod['precio']} USD\n\n"
                f"📝 *Paso a paso:*\n"
                f"1️⃣ Presiona 'Ir a pagar'\n"
                f"2️⃣ Selecciona USDT red TRC20\n"
                f"3️⃣ Paga con Trust Wallet\n"
                f"4️⃣ Vuelve y presiona '✅ Ya pagué'\n\n"
                f"🔒 *Pago seguro con NOWPayments*\n\n"
                f"NOWPayments retiene tu pago hasta que recibes el archivo.\n"
                f"Solo entonces se libera el dinero.\n\n"
                f"✅ Sin registro, 100% automático.\n\n"
                f"🔧 Recibirás tu archivo al instante después de presionar 'Ya pagué'"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        await query.delete_message()
        context.user_data["prod_key"] = "carro"
    else:
        await query.edit_message_text("❌ Error al crear la orden", parse_mode="Markdown")

async def verificar(update, context):
    query = update.callback_query
    await query.answer()
    
    prod_key = context.user_data.get("prod_key")
    if not prod_key or prod_key not in PRODUCTOS:
        await query.edit_message_text("❌ No hay compra activa", parse_mode="Markdown")
        return
    
    prod = PRODUCTOS[prod_key]
    keyboard = [[InlineKeyboardButton("📦 Ver catálogo", callback_data="catalogo")]]
    
    await query.edit_message_text(
        f"🎉 *¡Pago confirmado!*\n\n"
        f"✨ {prod['nombre']}\n\n"
        f"📥 *Descarga:*\n{prod['archivo_url']}\n\n"
        f"🔧 ¡Gracias por tu compra!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    context.user_data.clear()

def main():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN no configurado")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(catalogo, pattern="catalogo"))
    app.add_handler(CallbackQueryHandler(comprar, pattern="comprar"))
    app.add_handler(CallbackQueryHandler(verificar, pattern="verificar"))
    
    print("🚀 Bot funcionando con NOWPayments")
    app.run_polling()

if __name__ == "__main__":
    main()
