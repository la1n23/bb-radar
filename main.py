import os
import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import schedule
import telebot
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

WEBSITE_URL = os.getenv("WEBSITE_URL")
DB_NAME = os.getenv("DB_NAME", "scraped_data.db")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "30"))

PLATFORMS = {
    'hackerone': 'hackerone',
    'remedy': 'remedy',
    'yeswehack': 'yeswehack'
}


bot = telebot.TeleBot(TELEGRAM_TOKEN)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS bb_progs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TIMESTAMP,
            title TEXT UNIQUE,
            platform TEXT,
            type TEXT,
            link TEXT
        )
    """)
    conn.commit()
    conn.close()


def create_if_new(row: tuple):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            INSERT INTO bb_progs (date, title, platform, type, link) VALUES (?, ?, ?, ?, ?)
        """, row)
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError as e:
        conn.close()
        return False

def scrape_website() -> list[tuple]:
    try:
        response = requests.get(WEBSITE_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', { 'id': 'table_1'})
        rows = []
        for tr in table.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds):
                date = tds[1].get_text(strip=True)
                date = datetime.strptime(date, '%d/%m/%Y %H:%M') 
                title = tds[3].get_text(strip=True)
                platform_img = tds[4].find('img')['src']
                bb_type = tds[5].get_text(strip=True)
                link   = tds[6].find('a')['href']

                platform = platform_img
                for s in PLATFORMS.keys():
                    if s in platform_img:
                        platform = PLATFORMS[s]
                        break

                row = (date, title, platform, bb_type, link)
                rows.append(row)
        rows.sort(key=lambda x: x[0])
        #rows.append(
        #    (datetime.strptime("2025-01-02 20:00", "%Y-%m-%d %H:%M"), 'TEST', 'https://bbradar.io/wp-content/uploads/2023/04/c4r-logo.png', 'smart contract', 'https://code4rena.com/audits/2025-04-bitvault')
        #)
        return rows

    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def save_new_items(rows: list[tuple]):
    new_items = []
    for row in rows:
        item = create_if_new(row)
        if item:
            new_items.append(row)
    return new_items

def notify_telegram(new_items):
    if not new_items:
        return
        
    message = f"New items found at {datetime.now()}:\n\n" + "\n\n".join(list(new_items))
    try:
        bot.send_message(TELEGRAM_USER_ID, message)
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")

def job():
    print(f"Running job at {datetime.now()}")
    rows = scrape_website()
    created_rows = save_new_items(rows)
    new_items = [" | ".join([str(item) for item in row]) for row in created_rows]
    print('new', new_items)
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
