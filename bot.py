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

# ========== FUNCIÓN CRYPTOCLOUD CON ERRORES VISIBLES ==========
def crear_factura(amount, order_id):
    # Verificar que las claves existen
    if not CRYPTOCLOUD_API_KEY:
        return {"error": "❌ Falta CRYPTOCLOUD_API_KEY en las variables de entorno de Render"}
    if not CRYPTOCLOUD_SHOP_ID:
        return {"error": "❌ Falta CRYPTOCLOUD_SHOP_ID en las variables de entorno de Render"}
    
    url = "https://api.cryptocloud.plus/v2/invoice/create"
    headers = {"Authorization": f"Token {CRYPTOCLOUD_API_KEY}"}
    data = {"shop_id": CRYPTOCLOUD_SHOP_ID, "amount": amount, "order_id": order_id}
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        if response.status_code != 200:
            return {"error": f"❌ HTTP {response.status_code}: {response.text[:200]}"}
        return response.json()
    except Exception as e:
        return {"error": f"❌ Excepción: {str(e)}"}

# ========== CÓDIGO DEL BOT ==========
async def start(update, context):
    keyboard = [[InlineKeyboardButton("📦 VER CATÁLOGO", callback_data="catalogo")]]
    await update.message.reply_text("🔧 *MI TIENDA DE STL* 🔧\n\n👇 Presiona el botón:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def manejar_botones(update, context):
    query = update.callback_query
    await query.answer()
    
    print(f"BOTÓN PRESIONADO: {query.data}")
    
    if query.data == "catalogo":
        keyboard = [[InlineKeyboardButton("💰 COMPRAR - 15 USD", callback_data="comprar")]]
        await query.edit_message_text(
            "🚗 *Hummer RC*\n💰 Precio: 15 USD\n\n✅ Incluye: STL + STEP + SLDPRT + SLDASM",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    elif query.data == "comprar":
        # 👉 AHORA SÍ, INTENTAMOS CREAR LA FACTURA
        order_id = f"{update.effective_user.id}_{int(time.time())}"
        factura = crear_factura(15.0, order_id)
        
        # Si hay error, mostrarlo al usuario
        if factura.get("error"):
            await query.edit_message_text(
                f"❌ *Error al crear la factura:*\n\n{factura['error']}\n\n"
                f"Verifica que las variables de entorno en Render estén configuradas correctamente.",
                parse_mode="Markdown"
            )
            return
        
        # Si la factura se creó bien
        if factura and factura.get("result"):
            pay_url = factura["result"]["pay_url"]
            keyboard = [[InlineKeyboardButton("💳 IR A PAGAR", url=pay_url)]]
            await query.edit_message_text(
                f"🛒 *Hummer RC*\n💰 Monto: 15 USD\n\n"
                f"✅ Presiona el botón para pagar con Trust Wallet\n\n"
                f"Luego de pagar, presiona /pagado",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"❌ *Respuesta inesperada de CryptoCloud*\n\n{factura}",
                parse_mode="Markdown"
            )
    else:
        await query.edit_message_text(f"No reconozco: {query.data}")

def main():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN no configurado")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(manejar_botones))
    
    print("🚀 Bot corriendo...")
    app.run_polling()

if __name__ == "__main__":
    main()
