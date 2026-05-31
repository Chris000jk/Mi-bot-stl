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

def crear_factura(amount, order_id):
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

async def start(update, context):
    keyboard = [[InlineKeyboardButton("💰 COMPRAR - 15 USD", callback_data="comprar")]]
    await update.message.reply_text(
        "🚗 *Hummer RC*\n💰 Precio: 15 USD\n\n✅ Incluye: STL + STEP + SLDPRT + SLDASM\n\nPresiona el botón para comprar:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def botones(update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == "comprar":
        await query.edit_message_text("⏳ Creando factura, espera...")
        
        order_id = f"{update.effective_user.id}_{int(time.time())}"
        respuesta = crear_factura(15.0, order_id)
        
        # 👉 CORREGIDO: leer la respuesta correctamente
        if respuesta.get("error"):
            await query.edit_message_text(f"❌ Error: {respuesta['error']}")
            return
        
        # La respuesta exitosa tiene "status": "success" y dentro "result" con "link"
        if respuesta.get("status") == "success" and respuesta.get("result", {}).get("link"):
            pay_url = respuesta["result"]["link"]
            keyboard = [[InlineKeyboardButton("💳 PAGAR AHORA", url=pay_url)]]
            
            modo = "🔧 *MODO PRUEBA* (no se cobra realmente)" if respuesta["result"].get("test_mode") else "💰 *MODO REAL*"
            
            await query.edit_message_text(
                f"✅ *Factura creada!*\n\n{modo}\n\n"
                f"📦 *Hummer RC*\n💰 Monto: 15 USD\n\n"
                f"Presiona el botón para pagar con Trust Wallet:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(f"❌ Respuesta inesperada: {respuesta}")
    else:
        await query.edit_message_text(f"Botón no reconocido: {query.data}")

def main():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN no configurado")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(botones))
    
    print("🚀 Bot funcionando correctamente")
    app.run_polling()

if __name__ == "__main__":
    main()
