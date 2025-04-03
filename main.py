import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import schedule
import telebot
from datetime import datetime

# Configuration
WEBSITE_URL = "https://example.com"  # Replace with target website
DB_NAME = "scraped_data.db"
TABLE_NAME = "scraped_items"
TELEGRAM_TOKEN = "your_telegram_bot_token"  # Replace with your token
TELEGRAM_USER_ID = "your_telegram_user_id"  # Replace with your user ID
CHECK_INTERVAL_MINUTES = 30  # Change to desired interval

# Initialize Telegram bot
bot = telebot.TeleBot(TELEGRAM_TOKEN)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def scrape_website():
    try:
        response = requests.get(WEBSITE_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('table tr')  # Adjust selector as needed
        return [row.get_text(strip=True) for row in rows if row.get_text(strip=True)]
    except Exception as e:
        print(f"Error scraping website: {e}")
        return []

def save_new_items(items):
    new_items = []
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    for item in items:
        try:
            cursor.execute(f"INSERT INTO {TABLE_NAME} (content) VALUES (?)", (item,))
            new_items.append(item)
        except sqlite3.IntegrityError:
            continue
    
    conn.commit()
    conn.close()
    return new_items

def notify_telegram(new_items):
    if not new_items:
        return
        
    message = f"New items found at {datetime.now()}:\n\n" + "\n\n".join(new_items)
    try:
        bot.send_message(TELEGRAM_USER_ID, message)
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")

def job():
    print(f"Running job at {datetime.now()}")
    items = scrape_website()
    new_items = save_new_items(items)
    if new_items:
        notify_telegram(new_items)

def run_scheduler():
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    init_db()
    job()  
    run_scheduler()
