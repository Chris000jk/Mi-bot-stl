import os
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")

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

# ========== CÓDIGO DEL BOT ==========
async def start(update, context):
    keyboard = [[InlineKeyboardButton("📦 VER CATÁLOGO", callback_data="catalogo")]]
    await update.message.reply_text("Hola! Presiona el botón:", reply_markup=InlineKeyboardMarkup(keyboard))

async def manejar_botones(update, context):
    query = update.callback_query
    await query.answer()
    
    print(f"BOTÓN PRESIONADO: {query.data}")  # 👈 Esto es clave
    
    if query.data == "catalogo":
        keyboard = [[InlineKeyboardButton("💰 COMPRAR - 15 USD", callback_data="comprar")]]
        await query.edit_message_text("Producto: Hummer RC\nPrecio: 15 USD", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "comprar":
        await query.edit_message_text("🎉 COMPRA EXITOSA! Recibirás tu enlace.")
    else:
        await query.edit_message_text(f"No reconozco: {query.data}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(manejar_botones))  # 👈 Un solo handler para todo
    print("🚀 Bot de prueba corriendo...")
    app.run_polling()

if __name__ == "__main__":
    main()
