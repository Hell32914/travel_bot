# Travel Assistant Telegram Bot ✈️

**Description:**  
Travel Assistant is an interactive Telegram bot for searching flights, hotels, building travel routes, and setting trip reminders.  
The bot stores data in SQLite and automatically sends notifications for scheduled trips.

---

## Features
- Flight search (top 5 results)
- Hotel search (top 5 results)
- Multi-city route planning
- Trip reminders
- Saving travel history in a database
- Interactive menu with buttons

---

## Installation and Running

1. Clone the repository:
```bash
git clone https://github.com/username/travel-assistant-bot.git
cd travel-assistant-bot
```
2. Install dependencies:
```cmd
pip install -r requirements.txt
```
3. Create a .env file based on .env.example and add your API keys.

4. Run the bot:
```cmd
python travel_bot.py
```

travel-assistant-bot/

│

├── travel_bot.py        # Main bot code

├── requirements.txt     # Dependencies

├── .env.example         # Example API keys

└── travel_bot.db        # SQLite database (ignored in Git)






APIs Used

[Skyscanner API](https://rapidapi.com/server-error?code=NOT_FOUND&message=API%20not%20found.)

[Booking API](https://developers.booking.com/?utm_source=chatgpt.com)

[Google Maps Directions API](https://developers.google.com/maps/documentation/directions/overview?utm_source=chatgpt.com)

[Telegram Bot API](https://core.telegram.org/bots/api?utm_source=chatgpt.com)
