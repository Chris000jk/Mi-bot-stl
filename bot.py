import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")

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

async def start(update, context):
    keyboard = [[InlineKeyboardButton("📦 VER CATÁLOGO", callback_data="catalogo")]]
    await update.message.reply_text("Hola, presiona el botón:", reply_markup=InlineKeyboardMarkup(keyboard))

async def botones(update, context):
    query = update.callback_query
    await query.answer()
    
    print(f"Callback recibido: {query.data}")  # 👈 Esto es clave
    
    if query.data == "catalogo":
        keyboard = [[InlineKeyboardButton("💰 COMPRAR - 15 USD", callback_data="comprar")]]
        await query.edit_message_text("Producto: Hummer RC\nPrecio: 15 USD", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "comprar":
        await query.edit_message_text("🎉 Compraste el producto! Enlace de descarga: [AQUÍ]")
    else:
        await query.edit_message_text(f"No reconozco: {query.data}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(botones))
    print("Bot simple corriendo...")
    app.run_polling()

if __name__ == "__main__":
    main()
