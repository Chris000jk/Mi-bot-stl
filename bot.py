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

# ========== FUNCIÓN CREAR FACTURA ==========
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

# ========== FUNCIÓN VERIFICAR ESTADO DE FACTURA ==========
def verificar_estado_factura(uuid_invoice):
    """Consulta el estado de una factura en CryptoCloud usando su UUID"""
    if not CRYPTOCLOUD_API_KEY:
        return {"error": "Falta API Key"}
    
    url = "https://api.cryptocloud.plus/v1/invoice/info"
    headers = {"Authorization": f"Token {CRYPTOCLOUD_API_KEY}"}
    params = {"uuid": uuid_invoice}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"Verificando factura {uuid_invoice}: {response.status_code}")
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
    
    print(f"Botón presionado: {query.data}")
    
    if query.data == "catalogo":
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
        await query.edit_message_text("⏳ Creando orden...")
        
        order_id = f"{update.effective_user.id}_{int(time.time())}"
        respuesta = crear_factura(15.0, order_id)
        
        if respuesta.get("error"):
            await query.edit_message_text(f"❌ Error: {respuesta['error']}")
            return
        
        if respuesta.get("status") == "success" and respuesta.get("result", {}).get("link"):
            pay_url = respuesta["result"]["link"]
            invoice_uuid = respuesta["result"]["uuid"]
            
            # Guardar el UUID para verificar después
            context.user_data["invoice_uuid"] = invoice_uuid
            
            keyboard = [
                [InlineKeyboardButton("💳 Ir a pagar", url=pay_url)],
                [InlineKeyboardButton("✅ Ya pagué", callback_data="verificar_pago")]
            ]
            await query.edit_message_text(
                "✅ *Orden creada*\n\n"
                "💰 Monto: 15 USD\n\n"
                "1️⃣ Presiona 'Ir a pagar' y completa el pago\n"
                "2️⃣ Luego presiona 'YA PAGUÉ' para recibir tu archivo",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Error al crear la orden. Intenta de nuevo.")
    
    # ========== NUEVO: VERIFICAR PAGO ==========
    elif query.data == "verificar_pago":
        await query.edit_message_text("🔍 Verificando el estado de tu pago...")
        
        invoice_uuid = context.user_data.get("invoice_uuid")
        if not invoice_uuid:
            await query.edit_message_text(
                "❌ No hay una compra activa.\n\nUsa /start para ver el catálogo."
            )
            return
        
        # Consultar estado en CryptoCloud
        estado = verificar_estado_factura(invoice_uuid)
        
        # Verificar si el pago fue confirmado
        if estado and estado.get("status") == "success":
            # Buscar el estado de la factura (puede estar en 'result.status_invoice' o 'result.status')
            estado_invoice = estado.get("result", {}).get("status_invoice")
            if estado_invoice == "paid":
                # PAGO CONFIRMADO - ENTREGAR ARCHIVO
                archivo_url = "https://drive.google.com/uc?export=download&id=1UCpYCM4ueRSeSdEHYKnDKmWOewsKeqd6"
                keyboard = [[InlineKeyboardButton("📦 Ver catálogo", callback_data="catalogo")]]
                await query.edit_message_text(
                    f"🎉 *¡PAGO CONFIRMADO!* 🎉\n\n"
                    f"✅ *Hummer RC*\n\n"
                    f"📥 *Descarga tu archivo:*\n{archivo_url}\n\n"
                    f"🔧 ¡Gracias por tu compra!\n\n"
                    f"📦 Incluye: STL + STEP + SLDPRT + SLDASM",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
                context.user_data.clear()
                return
        
        # Si llegamos aquí, el pago no está confirmado
        await query.edit_message_text(
            "⏳ *Pago pendiente de confirmación*\n\n"
            "Si ya completaste el pago, espera unos minutos.\n\n"
            "💡 *Para pruebas en modo prueba:*\n"
            "1. Ve a tu panel de CryptoCloud\n"
            "2. Ve a 'Payments' → Activa 'Show test invoices'\n"
            "3. Busca tu factura y haz clic en 'Confirm without payment'\n"
            "4. Luego presiona 'YA PAGUÉ' nuevamente.",
            parse_mode="Markdown"
        )

def main():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN no configurado")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(manejar_botones))
    
    print("🚀 Bot funcionando con verificación de pagos")
    app.run_polling()

if __name__ == "__main__":
    main()
