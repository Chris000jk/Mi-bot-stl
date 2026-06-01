import os
import requests
import json
import time
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# ========== VARIABLES ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
CRYPTOCLOUD_API_KEY = os.getenv("CRYPTOCLOUD_API_KEY")
CRYPTOCLOUD_SHOP_ID = os.getenv("CRYPTOCLOUD_SHOP_ID")

print(f"🔍 API Key: {'✅ OK' if CRYPTOCLOUD_API_KEY else '❌ FALTA'}")
print(f"🔍 Shop ID: {'✅ OK' if CRYPTOCLOUD_SHOP_ID else '❌ FALTA'}")

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
        "descripcion": "📦 Carrocería + Ruedas + Ensamble\n🔥 15 USD",
        "archivo_url": "https://drive.google.com/uc?export=download&id=1UCpYCM4ueRSeSdEHYKnDKmWOewsKeqd6"
    }
}

# ========== CRYPTOCLOUD CON URL CORRECTA ==========
def crear_factura(amount, order_id):
    if not CRYPTOCLOUD_API_KEY:
        return {"error": "Falta CRYPTOCLOUD_API_KEY"}
    if not CRYPTOCLOUD_SHOP_ID:
        return {"error": "Falta CRYPTOCLOUD_SHOP_ID"}
    
    # URL correcta según documentación de CryptoCloud
    url = "https://api.cryptocloud.plus/v2/invoice/create"
    
    headers = {
        "Authorization": f"Token {CRYPTOCLOUD_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    data = {
        "shop_id": CRYPTOCLOUD_SHOP_ID,
        "amount": amount,
        "order_id": order_id,
        "currency": "USD"
    }
    
    print(f"📡 URL: {url}")
    print(f"📡 Headers: Authorization=Token ***, Content-Type=application/json")
    print(f"📡 Data: {data}")
    
    try:
        response = requests.post(
            url, 
            json=data, 
            headers=headers, 
            timeout=30,
            allow_redirects=True
        )
        
        print(f"📡 Status code: {response.status_code}")
        print(f"📡 Response text: {response.text[:500]}")
        
        if response.status_code == 405:
            return {"error": "Error 405: Método no permitido. La URL de la API puede ser incorrecta. Contacta con soporte de CryptoCloud."}
        
        if response.status_code == 401:
            return {"error": "Error 401: API Key inválida. Verifica tu clave en CryptoCloud."}
        
        if response.status_code == 404:
            return {"error": "Error 404: Endpoint no encontrado. Verifica la URL de la API."}
        
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}: {response.text[:200]}"}
        
        if not response.text or response.text.strip() == "":
            return {"error": "Respuesta vacía de CryptoCloud"}
        
        try:
            return response.json()
        except json.JSONDecodeError as e:
            return {"error": f"Error JSON: {str(e)}. Respuesta: {response.text[:200]}"}
            
    except requests.exceptions.Timeout:
        return {"error": "Tiempo de espera agotado"}
    except requests.exceptions.ConnectionError:
        return {"error": "Error de conexión"}
    except Exception as e:
        return {"error": f"Error: {str(e)}"}

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

# ========== BOT ==========
async def start(update, context):
    keyboard = [[InlineKeyboardButton("📦 Ver catálogo", callback_data="catalogo")]]
    await update.message.reply_text(
        "🔧 *Mi tienda STL* 🔧\n\n👇 Presiona el botón:",
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
                caption=f"*{prod['nombre']}*\n💰 {prod['precio']} USD\n\n{prod['descripcion']}",
                parse_mode="Markdown"
            ))
        else:
            media_group.append(InputMediaPhoto(media=foto_url))
    
    await query.message.reply_media_group(media=media_group)
    
    keyboard = [[InlineKeyboardButton(f"💰 Comprar - {prod['precio']} USD", callback_data="comprar")]]
    await query.message.reply_text("👇 Comprar", reply_markup=InlineKeyboardMarkup(keyboard))

async def comprar(update, context):
    query = update.callback_query
    await query.answer()
    
    prod = PRODUCTOS["carro"]
    await query.edit_message_text("⏳ Conectando con CryptoCloud...")
    
    order_id = f"{update.effective_user.id}_{int(time.time())}"
    respuesta = crear_factura(prod["precio"], order_id)
    
    if respuesta.get("error"):
        await query.edit_message_text(
            f"❌ *Error:*\n`{respuesta['error']}`\n\n"
            f"Variables en Render:\n"
            f"CRYPTOCLOUD_API_KEY: {'✅' if CRYPTOCLOUD_API_KEY else '❌'}\n"
            f"CRYPTOCLOUD_SHOP_ID: {'✅' if CRYPTOCLOUD_SHOP_ID else '❌'}",
            parse_mode="Markdown"
        )
        return
    
    if respuesta.get("status") == "success" and respuesta.get("result", {}).get("pay_url"):
        pay_url = respuesta["result"]["pay_url"]
        keyboard = [[InlineKeyboardButton("💳 Ir a pagar", url=pay_url)]]
        
        await query.message.reply_text(
            f"✅ *Orden creada*\n💰 {prod['precio']} USD\n🔗 Presiona para pagar:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        await query.delete_message()
    else:
        await query.edit_message_text(f"❌ Respuesta inesperada: {respuesta}", parse_mode="Markdown")

def main():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN no configurado")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(catalogo, pattern="catalogo"))
    app.add_handler(CallbackQueryHandler(comprar, pattern="comprar"))
    
    print("🚀 Bot funcionando...")
    app.run_polling()

if __name__ == "__main__":
    main()
