import os
import requests
import time
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
CRYPTOCLOUD_API_KEY = os.getenv("CRYPTOCLOUD_API_KEY")
CRYPTOCLOUD_SHOP_ID = os.getenv("CRYPTOCLOUD_SHOP_ID")

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

# ========== FUNCIÓN CRYPTOCLOUD ==========
def crear_factura(amount, order_id):
    if not CRYPTOCLOUD_API_KEY or not CRYPTOCLOUD_SHOP_ID:
        return {"error": "Falta configuración CryptoCloud"}
    
    url = "https://api.cryptocloud.plus/v2/invoice/create"
    headers = {"Authorization": f"Token {CRYPTOCLOUD_API_KEY}"}
    data = {"shop_id": CRYPTOCLOUD_SHOP_ID, "amount": amount, "order_id": order_id}
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# ========== COMANDOS ==========
async def start(update, context):
    keyboard = [[InlineKeyboardButton("📦 Ver catálogo", callback_data="catalogo")]]
    await update.message.reply_text(
        "🔧 *Bienvenido a mi tienda* 🔧\n\n"
        "🚗 Hummer RC - 15 USD\n\n"
        "👇 Presiona el botón para ver el producto:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def manejar_botones(update, context):
    query = update.callback_query
    await query.answer()
    
    print(f"Botón presionado: {query.data}")  # Para logs
    
    if query.data == "catalogo":
        # Mostrar producto y botón de comprar
        keyboard = [[InlineKeyboardButton("💰 Comprar - 15 USD", callback_data="comprar")]]
        await query.edit_message_text(
            "🚗 *Hummer RC*\n\n"
            "✅ Incluye: STL + STEP + SLDPRT + SLDASM\n"
            "💰 Precio: 15 USD\n\n"
            "👇 Presiona para comprar:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    elif query.data == "comprar":
        # Crear factura
        await query.edit_message_text("⏳ Creando orden...")
        
        order_id = f"{update.effective_user.id}_{int(time.time())}"
        respuesta = crear_factura(15.0, order_id)
        
        if respuesta.get("error"):
            await query.edit_message_text(f"❌ Error: {respuesta['error']}")
            return
        
        if respuesta.get("status") == "success" and respuesta.get("result", {}).get("link"):
            pay_url = respuesta["result"]["link"]
            keyboard = [[InlineKeyboardButton("💳 Ir a pagar", url=pay_url)]]
            await query.edit_message_text(
                "✅ *Orden creada*\n\n"
                "💰 Monto: 15 USD\n\n"
                "Presiona el botón para pagar con Trust Wallet:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Error al crear la orden. Intenta de nuevo.")

def main():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN no configurado")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(manejar_botones))  # Un solo handler para todo
    
    print("🚀 Bot funcionando")
    app.run_polling()

if __name__ == "__main__":
    main()
