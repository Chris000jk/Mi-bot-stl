import os
import requests
import time
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# ========== VARIABLES DE ENTORNO ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# NUEVAS variables para TU pasarela
MI_PASARELA_API_KEY = os.getenv("MI_PASARELA_API_KEY")
MI_PASARELA_URL = os.getenv("MI_PASARELA_URL", "https://crypto-pasarela.onrender.com")

# ========== PRODUCTO ==========
PRODUCTOS = {
    "carro": {
        "nombre": "🚗 Hummer RC - Completo con Ensamble",
        "precio": 15.0,
        "fotos": [
            "https://drive.google.com/uc?export=download&id=1gKk_OOR2NRHgNMorcAa9Kf8BA7XXIINm",
            "https://drive.google.com/uc?export=download&id=1SbguFbhSlLfilMyHGYXpioxrXfeDygVd",
            "https://drive.google.com/uc?export=download&id=17VvvUeuyc8nn6wSRcjsYx3qGa3-djjMh",
            "https://drive.google.com/uc?export=download&id=12UF7SVcQuGDdz2Sp7RV58bMwW5ARwm0F"
        ],
        "descripcion": "📦 CARROCERÍA + RUEDAS + ENSAMBLE COMPLETO\n\n"
                       "✅ INCLUYE:\n"
                       "• STL (para imprimir)\n"
                       "• STEP (para modificar en CAD)\n"
                       "• SLDPRT (piezas en SolidWorks)\n"
                       "• SLDASM (ensamble completo)\n\n"
                       "🔥 TODO por solo 15 USD",
        "archivo_url": "https://drive.google.com/uc?export=download&id=1UCpYCM4ueRSeSdEHYKnDKmWOewsKeqd6"
    }
}

# ========== TU PASARELA (reemplaza CryptoCloud) ==========
def crear_factura(amount, order_id, description="Compra en StoreSTLing"):
    """Crea una factura en TU pasarela"""
    if not MI_PASARELA_API_KEY:
        return {"error": "Falta MI_PASARELA_API_KEY en Render"}
    if not MI_PASARELA_URL:
        return {"error": "Falta MI_PASARELA_URL en Render"}
    
    url = f"{MI_PASARELA_URL}/api/invoices"
    headers = {
        "x-api-key": MI_PASARELA_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "amount": amount,
        "currency": "USDT",
        "order_id": order_id,
        "description": description,
        "expires_in": 3600  # 1 hora para pagar
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def verificar_estado_factura(invoice_id):
    """Verifica el estado de una factura en TU pasarela"""
    if not MI_PASARELA_API_KEY or not MI_PASARELA_URL:
        return "error"
    
    url = f"{MI_PASARELA_URL}/api/invoices/{invoice_id}"
    headers = {"x-api-key": MI_PASARELA_API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()
        return data.get("status")  # pending, paid, expired, failed
    except Exception as e:
        print(f"Error verificando factura: {e}")
        return "error"

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

# ========== COMANDOS DEL BOT ==========
async def start(update, context):
    foto_bienvenida = "https://drive.google.com/uc?export=download&id=1g4u0wM7nViiEl-RmyZvrYOfo6SxY9zoF"
    
    keyboard = [[InlineKeyboardButton("📦 VER CATÁLOGO", callback_data="catalogo")]]
    
    # MENSAJE MODIFICADO PARA VERIFICAR QUE EL CÓDIGO NUEVO ESTÁ CORRIENDO
    await update.message.reply_photo(
        photo=foto_bienvenida,
        caption="🔧 *MI TIENDA DE STL - VERSIÓN 2.0* 🔧\n\n"
                "✅ *PASARELA PROPIA ACTIVA* ✅\n\n"
                "🚗 Diseños en SolidWorks para impresión 3D\n"
                "💰 Pagos en USDT (Trust Wallet)\n"
                "✅ Entrega automática\n\n"
                "👇 Presiona el botón para ver los productos:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def catalogo(update, context):
    query = update.callback_query
    await query.answer()
    
    prod = PRODUCTOS["carro"]
    
    # Galería de fotos (carrusel)
    media_group = []
    for i, foto_url in enumerate(prod["fotos"]):
        if i == 0:
            media_group.append(InputMediaPhoto(
                media=foto_url,
                caption=f"*{prod['nombre']}*\n\n"
                       f"💰 *Precio:* {prod['precio']} USD\n\n"
                       f"{prod['descripcion']}\n\n"
                       f"🔧 *Desliza para ver más fotos* 👉",
                parse_mode="Markdown"
            ))
        else:
            media_group.append(InputMediaPhoto(media=foto_url))
    
    await query.message.reply_media_group(media=media_group)
    
    # Botón de compra
    keyboard = [[InlineKeyboardButton(f"💰 COMPRAR - {prod['precio']} USD", callback_data="comprar")]]
    await query.message.reply_text(
        "👇 *Presiona el botón para comprar* 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def comprar(update, context):
    query = update.callback_query
    await query.answer()
    
    prod = PRODUCTOS["carro"]
    
    # Mostrar mensaje de espera
    await query.edit_message_text("⏳ *Creando factura, espera un momento...*", parse_mode="Markdown")
    
    order_id = f"{update.effective_user.id}_{int(time.time())}"
    respuesta = crear_factura(prod["precio"], order_id, prod["nombre"])
    
    # Verificar errores de configuración
    if respuesta.get("error"):
        await query.edit_message_text(
            f"❌ *Error de configuración:*\n`{respuesta['error']}`\n\n"
            f"Contacta al administrador.",
            parse_mode="Markdown"
        )
        return
    
    # Verificar respuesta exitosa de TU pasarela
    if respuesta.get("status") == "pending" and respuesta.get("data", {}).get("address"):
        direccion_wallet = respuesta["data"]["address"]
        invoice_id = respuesta["data"]["invoice_id"]
        amount = respuesta["data"]["amount"]
        
        # Guardar datos para verificación
        context.user_data["prod_key"] = "carro"
        context.user_data["invoice_id"] = invoice_id
        context.user_data["order_id"] = order_id
        
        keyboard = [
            [InlineKeyboardButton("💳 VER DIRECCIÓN DE PAGO", callback_data="mostrar_direccion")],
            [InlineKeyboardButton("✅ YA PAGUÉ", callback_data="verificar")],
            [InlineKeyboardButton("🔙 VER CATÁLOGO", callback_data="catalogo")]
        ]
        
        await query.edit_message_text(
            f"✅ *Factura creada correctamente!*\n\n"
            f"💰 *TU PROPIA PASARELA* (sin intermediarios)\n\n"
            f"🛒 *{prod['nombre']}*\n"
            f"💰 *Monto:* {amount} USDT\n\n"
            f"📝 *Instrucciones:*\n"
            f"1️⃣ Presiona VER DIRECCIÓN DE PAGO\n"
            f"2️⃣ Envía EXACTAMENTE {amount} USDT a esa dirección\n"
            f"3️⃣ Vuelve aquí y presiona YA PAGUÉ\n\n"
            f"⏰ *Tienes 1 hora para pagar*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            f"❌ *Respuesta inesperada de la pasarela*\n\n"
            f"Intenta de nuevo más tarde.",
            parse_mode="Markdown"
        )

async def mostrar_direccion(update, context):
    query = update.callback_query
    await query.answer()
    
    invoice_id = context.user_data.get("invoice_id")
    if not invoice_id:
        await query.edit_message_text(
            "❌ *No hay una compra activa*\n\nUsa /start para ver el catálogo.",
            parse_mode="Markdown"
        )
        return
    
    # Obtener los datos de la factura
    if not MI_PASARELA_API_KEY or not MI_PASARELA_URL:
        await query.edit_message_text("❌ Error de configuración de la pasarela.", parse_mode="Markdown")
        return
    
    url = f"{MI_PASARELA_URL}/api/invoices/{invoice_id}"
    headers = {"x-api-key": MI_PASARELA_API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()
        
        if data.get("status") == "pending" and data.get("data", {}).get("address"):
            address = data["data"]["address"]
            amount = data["data"]["amount"]
            
            await query.edit_message_text(
                f"💳 *DIRECCIÓN PARA EL PAGO*\n\n"
                f"💰 *Monto:* {amount} USDT (TRC-20)\n\n"
                f"📍 *Dirección:*\n`{address}`\n\n"
                f"⚠️ *Importante:*\n"
                f"• Envía EXACTAMENTE {amount} USDT\n"
                f"• Usa la red TRC-20\n"
                f"• Después de pagar, presiona YA PAGUÉ\n\n"
                f"⏰ Tienes hasta que expire la factura",
                parse_mode="Markdown"
            )
            
            # Volver a poner los botones
            keyboard = [
                [InlineKeyboardButton("✅ YA PAGUÉ", callback_data="verificar")],
                [InlineKeyboardButton("🔙 VER CATÁLOGO", callback_data="catalogo")]
            ]
            await update.callback_query.message.reply_text(
                "👇 *Cuando termines el pago:*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                "❌ *No se encontró la factura o ya expiró*\n\nUsa /start para ver el catálogo.",
                parse_mode="Markdown"
            )
    except Exception as e:
        await query.edit_message_text(f"❌ Error al obtener la dirección: {e}", parse_mode="Markdown")

async def verificar(update, context):
    query = update.callback_query
    await query.answer()
    
    prod_key = context.user_data.get("prod_key")
    invoice_id = context.user_data.get("invoice_id")
    
    if not prod_key or not invoice_id:
        await query.edit_message_text(
            "❌ *No hay una compra activa*\n\nUsa /start para ver el catálogo.",
            parse_mode="Markdown"
        )
        return
    
    prod = PRODUCTOS[prod_key]
    
    # Verificar estado en TU pasarela
    estado = verificar_estado_factura(invoice_id)
    
    if estado == "paid":
        keyboard = [[InlineKeyboardButton("📦 VER CATÁLOGO", callback_data="catalogo")]]
        
        await query.edit_message_text(
            f"🎉 *¡PAGO CONFIRMADO!* 🎉\n\n"
            f"✨ *{prod['nombre']}*\n\n"
            f"📥 *Descarga tu archivo:*\n{prod['archivo_url']}\n\n"
            f"🔧 ¡Gracias por tu compra!\n\n"
            f"📦 El archivo incluye: STL + STEP + SLDPRT + SLDASM",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        
        context.user_data.clear()
    elif estado == "pending":
        keyboard = [
            [InlineKeyboardButton("✅ VOLVER A VERIFICAR", callback_data="verificar")],
            [InlineKeyboardButton("🔙 VER CATÁLOGO", callback_data="catalogo")]
        ]
        await query.edit_message_text(
            f"⏳ *Pago no confirmado aún*\n\n"
            f"💰 *Monto:* {prod['precio']} USDT\n\n"
            f"• Asegúrate de haber enviado el monto exacto\n"
            f"• La red TRC-20 puede tardar unos minutos\n"
            f"• Presiona VERIFICAR de nuevo más tarde\n\n"
            f"⚠️ *Si ya pagaste y pasó más de 30 minutos*, contacta al administrador.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    elif estado == "expired":
        await query.edit_message_text(
            f"❌ *La factura expiró*\n\n"
            f"Usa /start para crear una nueva compra.",
            parse_mode="Markdown"
        )
        context.user_data.clear()
    else:
        keyboard = [[InlineKeyboardButton("🔙 VER CATÁLOGO", callback_data="catalogo")]]
        await query.edit_message_text(
            f"❌ *Error verificando el pago*\n\n"
            f"Estado devuelto: {estado}\n\n"
            f"Intenta de nuevo o contacta al administrador.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

# ========== MAIN ==========
def main():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN no configurado en Render")
        return
    
    if not MI_PASARELA_API_KEY:
        print("⚠️ ADVERTENCIA: MI_PASARELA_API_KEY no configurada")
    
    if not MI_PASARELA_URL:
        print("⚠️ ADVERTENCIA: MI_PASARELA_URL no configurada, usando default")
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(catalogo, pattern="^catalogo$"))
    app.add_handler(CallbackQueryHandler(comprar, pattern="^comprar$"))
    app.add_handler(CallbackQueryHandler(mostrar_direccion, pattern="^mostrar_direccion$"))
    app.add_handler(CallbackQueryHandler(verificar, pattern="^verificar$"))
    
    print("🚀 Bot corriendo con TU PROPIA PASARELA de pagos...")
    app.run_polling()

if __name__ == "__main__":
    main()
