import os
import requests
import time
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# ========== VARIABLES DE ENTORNO ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
CRYPTOCLOUD_API_KEY = os.getenv("CRYPTOCLOUD_API_KEY")
CRYPTOCLOUD_SHOP_ID = os.getenv("CRYPTOCLOUD_SHOP_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# ========== CATÁLOGO DE PRODUCTOS ==========
# Cada producto tiene: nombre, precio, foto, descripcion, archivo_url
PRODUCTOS = {
    "carro": {
        "nombre": "🚗 Carro RC Completo",
        "precio": 25.0,
        "foto": "https://drive.google.com/uc?export=download&id=ID_FOTO_CARRO_AQUI",
        "descripcion": "📦 Incluye: 12 piezas STL\n🔧 Fácil de armar\n⚙️ Ruedas móviles\n🎮 Compatible con servos estándar",
        "archivo_url": "https://drive.google.com/uc?export=download&id=ID_ZIP_CARRO_AQUI"
    },
    "rueda": {
        "nombre": "🏍️ Rueda de Moto",
        "precio": 10.0,
        "foto": "https://drive.google.com/uc?export=download&id=1OceXb1_I85OP2r0iAYfQGplk2ArTiIuT",
        "descripcion": "📏 Diámetro: 120mm\n🔩 Diseño realista\n💪 Material recomendado: TPU o ABS",
        "archivo_url": "https://drive.google.com/uc?export=download&id=1F6ygJKkBBdWSwubZzWcnnZcompdrJYxV"
    }
}

# ========== FUNCIONES CRYPTOCLOUD ==========
def crear_factura(amount, order_id):
    url = "https://api.cryptocloud.plus/v2/invoice/create"
    headers = {"Authorization": f"Token {CRYPTOCLOUD_API_KEY}"}
    data = {"shop_id": CRYPTOCLOUD_SHOP_ID, "amount": amount, "order_id": order_id}
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

# ========== COMANDOS ==========
async def start(update, context):
    keyboard = [[InlineKeyboardButton("📦 VER CATÁLOGO", callback_data="catalogo")]]
    await update.message.reply_text(
        "🔧 *MI TIENDA DE STL* 🔧\n\n"
        "🏍️ Piezas y accesorios para impresión 3D\n"
        "💰 Pagos en USDT (Trust Wallet)\n"
        "✅ Entrega automática al confirmar pago\n\n"
        "👇 Presiona el botón para ver los productos:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def catalogo(update, context):
    query = update.callback_query
    await query.answer()
    
    # Eliminar el mensaje del menú anterior
    await query.delete_message()
    
    # Mostrar cada producto como un mensaje independiente
    for key, prod in PRODUCTOS.items():
        keyboard = [[InlineKeyboardButton(f"💰 COMPRAR - {prod['precio']} USDT", callback_data=f"comprar_{key}")]]
        
        # Enviar mensaje con FOTO + DESCRIPCIÓN + BOTÓN
        await query.message.reply_photo(
            photo=prod["foto"],
            caption=f"*{prod['nombre']}*\n\n"
                    f"💰 *Precio:* {prod['precio']} USDT\n\n"
                    f"{prod['descripcion']}\n\n"
                    f"✅ *Incluye:* Archivo STL listo para imprimir\n"
                    f"🔗 *Entrega:* Enlace directo de descarga",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    # Mensaje final
    await query.message.reply_text(
        "🛒 *Para comprar:*\n"
        "1. Presiona COMPRAR en el producto que deseas\n"
        "2. Completa el pago con Trust Wallet\n"
        "3. Presiona VERIFICAR PAGO\n"
        "4. Recibe tu archivo automáticamente",
        parse_mode="Markdown"
    )

async def comprar(update, context, product_key):
    query = update.callback_query
    await query.answer()
    
    if product_key not in PRODUCTOS:
        await query.edit_message_text("❌ Producto no encontrado.")
        return
    
    prod = PRODUCTOS[product_key]
    order_id = f"{update.effective_user.id}_{int(time.time())}"
    
    # Crear factura en CryptoCloud
    factura = crear_factura(prod["precio"], order_id)
    
    if not factura or not factura.get("result"):
        await query.edit_message_text(
            "❌ *Error al crear la factura*\n\n"
            "Intenta de nuevo en unos segundos.\n"
            "Si el problema persiste, contacta al administrador.",
            parse_mode="Markdown"
        )
        return
    
    # Guardar datos de la compra
    context.user_data["prod_key"] = product_key
    context.user_data["pay_url"] = factura["result"]["pay_url"]
    
    keyboard = [
        [InlineKeyboardButton("💳 IR A PAGAR", url=factura["result"]["pay_url"])],
        [InlineKeyboardButton("✅ YA PAGUÉ", callback_data="verificar")],
        [InlineKeyboardButton("🔙 VOLVER AL CATÁLOGO", callback_data="catalogo")]
    ]
    
    # Mostrar confirmación con el mismo producto
    await query.edit_message_caption(
        caption=f"*{prod['nombre']}*\n\n"
                f"💰 *Monto a pagar:* {prod['precio']} USDT\n\n"
                f"📝 *Instrucciones:*\n"
                f"1️⃣ Presiona IR A PAGAR\n"
                f"2️⃣ Completa el pago con Trust Wallet\n"
                f"3️⃣ Vuelve aquí y presiona YA PAGUÉ\n\n"
                f"✅ Recibirás tu archivo automáticamente",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def verificar(update, context):
    query = update.callback_query
    await query.answer()
    
    prod_key = context.user_data.get("prod_key")
    if not prod_key or prod_key not in PRODUCTOS:
        await query.edit_message_text(
            "❌ *No hay una compra activa*\n\n"
            "Usa /start para ver el catálogo.",
            parse_mode="Markdown"
        )
        return
    
    prod = PRODUCTOS[prod_key]
    
    # Mientras estés en modo prueba, siempre confirma
    # Cuando salgas del modo prueba, aquí debes verificar con CryptoCloud
    
    keyboard = [[InlineKeyboardButton("📦 VER MÁS PRODUCTOS", callback_data="catalogo")]]
    
    await query.edit_message_caption(
        caption=f"🎉 *¡PAGO CONFIRMADO!* 🎉\n\n"
                f"✨ *{prod['nombre']}*\n\n"
                f"📥 *Descarga tu archivo:*\n"
                f"{prod['archivo_url']}\n\n"
                f"🔧 ¡Gracias por tu compra!\n"
                f"💬 ¿Preguntas? Contáctame.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    
    # Limpiar datos de la compra
    context.user_data.clear()

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

# ========== MAIN ==========
def main():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN no configurado")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(catalogo, pattern="^catalogo$"))
    app.add_handler(CallbackQueryHandler(verificar, pattern="^verificar$"))
    app.add_handler(CallbackQueryHandler(
        lambda u, c: comprar(u, c, u.callback_query.data.split("_")[1]),
        pattern="^comprar_"
    ))
    
    print("🚀 Bot corriendo con catálogo visual...")
    app.run_polling()

if __name__ == "__main__":
    main()
