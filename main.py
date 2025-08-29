# travel_assistant_ultimate.py
import os
import sqlite3
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, ConversationHandler, MessageHandler, filters
)
from apscheduler.schedulers.background import BackgroundScheduler

# -------------------- Ключи и бот --------------------
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
SKYSCANNER_KEY = os.getenv("SKYSCANNER_KEY")
BOOKING_KEY = os.getenv("BOOKING_KEY")
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY")

app = ApplicationBuilder().token(TOKEN).build()
scheduler = BackgroundScheduler()
scheduler.start()

# -------------------- База данных --------------------
conn = sqlite3.connect("travel_bot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS trips(
    chat_id INTEGER,
    type TEXT,
    description TEXT,
    datetime TEXT
)""")
conn.commit()

# -------------------- Состояния --------------------
CHOOSING, TYPING_FLIGHT, TYPING_HOTEL, TYPING_ROUTE, TYPING_REMIND = range(5)

# -------------------- Главное меню --------------------
def main_menu():
    keyboard = [
        [InlineKeyboardButton("✈️ Поиск билетов", callback_data="flight")],
        [InlineKeyboardButton("🏨 Поиск отелей", callback_data="hotel")],
        [InlineKeyboardButton("🗺️ Маршрут", callback_data="route")],
        [InlineKeyboardButton("⏰ Напоминание", callback_data="remind")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я Travel Assistant ✈️\nВыберите действие:", reply_markup=main_menu())
    return CHOOSING

# -------------------- Меню --------------------
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    if choice == "flight":
        await query.edit_message_text("Введите: ORIGIN DESTINATION DATE(YYYY-MM-DD)")
        return TYPING_FLIGHT
    elif choice == "hotel":
        await query.edit_message_text("Введите: CITY CHECKIN CHECKOUT(YYYY-MM-DD)")
        return TYPING_HOTEL
    elif choice == "route":
        await query.edit_message_text("Введите города через пробел: START CITY1 CITY2 ...")
        return TYPING_ROUTE
    elif choice == "remind":
        await query.edit_message_text("Введите: YYYY-MM-DD_HH:MM MESSAGE")
        return TYPING_REMIND

# -------------------- Функции API --------------------
def search_flights(origin, destination, date):
    url = f"https://api.skyscanner.net/apiservices/browsequotes/v1.0/US/USD/en-US/{origin}/{destination}/{date}?apiKey={SKYSCANNER_KEY}"
    response = requests.get(url)
    flights = []
    if response.status_code == 200:
        data = response.json()
        for quote in data.get("Quotes", [])[:5]:  # топ 5
            direct = "Прямой" if quote.get('Direct') else "С пересадкой"
            flights.append(f"{quote.get('MinPrice', '?')}$ - {direct}")
    if not flights:
        flights.append("Рейсы не найдены.")
    return flights

def search_hotels(city, checkin, checkout):
    url = f"https://api.booking.com/v1/hotels?city={city}&checkin={checkin}&checkout={checkout}&apikey={BOOKING_KEY}"
    response = requests.get(url)
    hotels = []
    if response.status_code == 200:
        for hotel in response.json().get("results", [])[:5]:
            hotels.append(f"{hotel.get('name', '?')} - {hotel.get('price', '?')} per night")
    if not hotels:
        hotels.append("Отели не найдены.")
    return hotels

def get_route(cities):
    full_route = []
    for i in range(len(cities)-1):
        start, end = cities[i], cities[i+1]
        url = f"https://maps.googleapis.com/maps/api/directions/json?origin={start}&destination={end}&key={GOOGLE_MAPS_KEY}"
        response = requests.get(url).json()
        if not response.get("routes"):
            full_route.append(f"Маршрут {start} → {end} не найден")
            continue
        steps = response['routes'][0]['legs'][0]['steps']
        instructions = []
        for step in steps:
            instr = step['html_instructions'].replace("<b>", "").replace("</b>", "")
            instr = instr.replace("<div style=\"font-size:0.9em\">", " ").replace("</div>", "")
            instructions.append(instr)
        full_route.append(f"Маршрут {start} → {end}:\n" + "\n".join(instructions))
    return full_route

def set_reminder(chat_id, message, dt):
    scheduler.add_job(lambda: app.bot.send_message(chat_id, f"⏰ Напоминание: {message}"), 'date', run_date=dt)

# -------------------- Обработчики --------------------
async def handle_flight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        origin, dest, date = update.message.text.split()
        flights = search_flights(origin, dest, date)
        await update.message.reply_text("\n".join(flights), reply_markup=main_menu())
        # Сохраняем топ-рейсы
        for f in flights:
            cursor.execute("INSERT INTO trips VALUES(?,?,?,?)", (update.message.chat_id, "flight", f, date))
        conn.commit()
    except:
        await update.message.reply_text("Ошибка. Формат: ORIGIN DESTINATION DATE")
    return CHOOSING

async def handle_hotel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        city, checkin, checkout = update.message.text.split()
        hotels = search_hotels(city, checkin, checkout)
        await update.message.reply_text("\n".join(hotels), reply_markup=main_menu())
        for h in hotels:
            cursor.execute("INSERT INTO trips VALUES(?,?,?,?)", (update.message.chat_id, "hotel", h, checkin))
        conn.commit()
    except:
        await update.message.reply_text("Ошибка. Формат: CITY CHECKIN CHECKOUT")
    return CHOOSING

async def handle_route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cities = update.message.text.split()
        if len(cities) < 2:
            await update.message.reply_text("Нужно минимум 2 города")
            return CHOOSING
        routes = get_route(cities)
        await update.message.reply_text("\n\n".join(routes), reply_markup=main_menu())
        cursor.execute("INSERT INTO trips VALUES(?,?,?,?)", (update.message.chat_id, "route", " → ".join(cities), datetime.now().isoformat()))
        conn.commit()
    except:
        await update.message.reply_text("Ошибка при построении маршрута")
    return CHOOSING

async def handle_remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.split(maxsplit=1)
        dt = datetime.strptime(parts[0], "%Y-%m-%d_%H:%M")
        message = parts[1]
        set_reminder(update.message.chat_id, message, dt)
        cursor.execute("INSERT INTO trips VALUES(?,?,?,?)", (update.message.chat_id, "reminder", message, parts[0]))
        conn.commit()
        await update.message.reply_text(f"Напоминание установлено на {dt}", reply_markup=main_menu())
    except:
        await update.message.reply_text("Ошибка. Формат: YYYY-MM-DD_HH:MM MESSAGE")
    return CHOOSING

# -------------------- Conversation Handler --------------------
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        CHOOSING: [CallbackQueryHandler(menu_handler)],
        TYPING_FLIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_flight)],
        TYPING_HOTEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hotel)],
        TYPING_ROUTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_route)],
        TYPING_REMIND: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_remind)],
    },
    fallbacks=[CommandHandler('start', start)]
)

app.add_handler(conv_handler)
print("Бот запущен...")
app.run_polling()
