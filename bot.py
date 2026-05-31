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

# Servidor para Render
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
    # Primero, verificar que las claves existen
    if not CRYPTOCLOUD_API_KEY:
        return {"error": "Falta API_KEY"}
    if not CRYPTOCLOUD_SHOP_ID:
        return {"error": "Falta SHOP_ID"}
    
    url = "https://api.cryptocloud.plus/v2/invoice/create"
    headers = {"Authorization": f"Token {CRYPTOCLOUD_API_KEY}"}
    data = {"shop_id": CRYPTOCLOUD_SHOP_ID, "amount": amount, "order_id": order_id}
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# ========== BOT ==========
async def start(update, context):
    # Botón único que dice COMPRAR
    keyboard = [[InlineKeyboardButton("💰 COMPRAR - 15 USD", callback_data="comprar")]]
    await update.message.reply_text(
        "🚗 *Hummer RC*\n💰 Precio: 15 USD\n\nPresiona el botón para comprar:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def botones(update, context):
    query = update.callback_query
    await query.answer()
    
    print(f"📱 Botón presionado: {query.data}")  # Esto se ve en logs de Render
    
    if query.data == "comprar":
        # Mostrar "Procesando..." mientras se crea la factura
        await query.edit_message_text("⏳ Creando factura, espera...")
        
        order_id = f"{update.effective_user.id}_{int(time.time())}"
        factura = crear_factura(15.0, order_id)
        
        # Si hay error, mostrarlo
        if factura.get("error"):
            await query.edit_message_text(f"❌ Error: {factura['error']}\n\nVerifica las variables en Render.")
            return
        
        # Si la factura se creó bien
        if factura.get("result") and factura["result"].get("pay_url"):
            pay_url = factura["result"]["pay_url"]
            keyboard = [[InlineKeyboardButton("💳 PAGAR AHORA", url=pay_url)]]
            await query.edit_message_text(
                "✅ *Factura creada!*\n\nPresiona el botón para pagar con Trust Wallet:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(f"❌ Respuesta inesperada: {factura}")
    else:
        await query.edit_message_text(f"Botón no reconocido: {query.data}")

def main():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN no configurado")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(botones))  # Un solo handler para todo
    
    print("🚀 Bot iniciado - Modo prueba definitivo")
    app.run_polling()

if __name__ == "__main__":
    main()
