import os
import requests
import time
import hashlib
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# ========== VARIABLES DE ENTORNO (configurar en Render) ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
NOWPAYMENTS_IPN_SECRET = os.getenv("NOWPAYMENTS_IPN_SECRET", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

print(f"🔍 BOT_TOKEN: {'✅ OK' if BOT_TOKEN else '❌ FALTA'}")
print(f"🔍 NOWPAYMENTS_API_KEY: {'✅ OK' if NOWPAYMENTS_API_KEY else '❌ FALTA'}")

# ========== PRODUCTO ==========
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
        "descripcion": "📦 Carrocería + Ruedas + Ensamble Completo\n\n"
                       "✅ Incluye:\n"
                       "• STL (para impresión 3D)\n"
                       "• STEP (para modificar en CAD)\n"
                       "• SLDPRT (piezas SolidWorks)\n"
                       "• SLDASM (ensamble SolidWorks)\n\n"
                       "🔥 Todo por solo 15 USD",
        "archivo_url": "https://drive.google.com/uc?export=download&id=1UCpYCM4ueRSeSdEHYKnDKmWOewsKeqd6"
    }
}

# ========== NOWPAYMENTS ==========
def crear_pago_nowpayments(amount, order_id):
    if not NOWPAYMENTS_API_KEY:
        return {"error": "Falta NOWPAYMENTS_API_KEY en Render"}
    
    url = "https://api.nowpayments.io/v1/invoice"
    headers = {
        "x-api-key": NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "price_amount": amount,
        "price_currency": "USD",
        "pay_currency": "USDT_TRC20",
        "order_id": order_id,
        "order_description": f"Compra de Hummer RC - {order_id}",
        "ipn_callback_url": "https://mi-bot-stl.onrender.com/ipn"  # URL de tu bot en Render
    }
    
    print(f"📡 Enviando a NOWPayments: {url}")
    print(f"📡 Data: {data}")
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        print(f"📡 Status: {response.status_code}")
        print(f"📡 Respuesta: {response.text[:500]}")
        
        if response.status_code == 201:
            return response.json()
        elif response.status_code == 401:
            return {"error": "API Key inválida. Ver
