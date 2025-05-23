from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
import requests
from bs4 import BeautifulSoup
from tabulate import tabulate
import time
import schedule
import telebot
from datetime import datetime
from dotenv import load_dotenv
import sqlite3

load_dotenv()

WEBSITE_URL = os.getenv("WEBSITE_URL", "https://bbradar.io")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "30"))
DATA_DIR = os.getcwd() + "/data"

PLATFORMS = {
    'hackerone': 'hackerone',
    'remedy': 'remedy',
    'yeswehack': 'yeswehack',
    'immunefi': 'immunefi',
    'c4r': 'code4rena',
    'Logotype.D9ur76GB.png': 'HackenProof',
    'bugbase': 'bugbase',
    'intigriti': 'intigriti',
    'standoff365': 'standoff365'
}

conn = sqlite3.connect('links.db')
cursor = conn.cursor()

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def init_db():
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                title TEXT,
                platform TEXT,
                bb_type TEXT,
                link TEXT
            )
        ''')
        conn.commit()
    except sqlite3.OperationalError as e:
        pass

def get_diff(rows):
    diff = []
    for row in rows:
        cursor.execute('SELECT * FROM links WHERE link = ?', (row[4],))
        existing_row = cursor.fetchone()
        if existing_row is None:
            diff.append(row)
            cursor.execute('INSERT INTO links (date, title, platform, bb_type, link) VALUES (?, ?, ?, ?, ?)', row)
            conn.commit()
    return diff

def scrape_website() -> list[tuple]:
    try:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options)
        driver.get(WEBSITE_URL)

        time.sleep(3)
        html = driver.page_source
        driver.quit()

        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', { 'id': 'table_1'})
        rows = []
        for tr in table.find_all('tr'):
            tds = tr.find_all('td')
            try:
                if len(tds):
                    date = tds[0].get_text(strip=True)
                    date = datetime.strptime(date, '%d/%m/%Y %H:%M') 
                    title = tds[2].get_text(strip=True)
                    platform_img =  tds[3].find('img')['src']
                    bb_type = tds[4].get_text(strip=True)
                    link   = tds[5].find('a')['href']

                    platform = platform_img
                    for s in PLATFORMS.keys():
                        if s in platform_img:
                            platform = PLATFORMS[s]
                            break

                    row = (date, title, platform, bb_type, link)
                    rows.append(row)
            except Exception as x:
                print('Error parsing a table row, probably format changed:',x, tds)
        rows.sort(key=lambda x: x[0])
        return rows

    except Exception as e:
        raise e
        print(f"Error fetching data: {e}")
        return []

def notify_telegram(new_items):
    if not new_items:
        return
    message = ''
    for row in new_items:
        message += f"{row[1]} - {row[0]}\n"
        message += f"{row[2]} - {row[3]}\n"
        message += f"{row[4]}\n"
        message += "------------------------\n"

    try:
        bot.send_message(TELEGRAM_USER_ID, message, disable_web_page_preview=True)
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")

def job():
    print(f"Running job at {datetime.now()}")
    rows = scrape_website()
    new_items = [[str(item) for item in row] for row in rows]

    diff = get_diff(new_items)

    if diff:
        print(tabulate(diff, tablefmt='plain'))

        half = len(diff)//2
        notify_telegram(diff[:half])
        notify_telegram(diff[half:])
    else:
        print(f"No new items {datetime.now()}")

def run_scheduler():
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    init_db()
    job()
    run_scheduler()
