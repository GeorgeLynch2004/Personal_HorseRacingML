import time
import csv
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# --- Config --- #
BASE_URL = "https://www.racingpost.com/racecards/"
DAYS_AHEAD = 7
OUTPUT_FILE = "upcoming_races.csv"

options = Options()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)

def get_dates():
    return [(datetime.today() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(DAYS_AHEAD)]

def scrape_day(date_str):
    url = f"{BASE_URL}{date_str}"
    print(f"Scraping {url}...")
    driver.get(url)
    time.sleep(4)  # Wait for JS
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    races = []
    race_sections = soup.find_all('a', class_='RC-meetingItem__link')
    for race in race_sections:
        href = race.get('href')
        if href:
            races.append("https://www.racingpost.com" + href)
    return races

def scrape_race_card(url):
    print(f"  - Grabbing race: {url}")
    driver.get(url)
    time.sleep(4)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    race_info = soup.find('div', class_='RC-header')
    try:
        course = race_info.find('span', class_='RC-header__raceInstanceTitle').text.strip()
        time_str = race_info.find('span', class_='RC-header__time').text.strip()
        distance = race_info.find('span', class_='RC-header__distance').text.strip()
    except:
        return []

    horses = []
    rows = soup.find_all('tr', class_='RC-runnerRow')
    for row in rows:
        try:
            horse = row.find('a', class_='RC-runnerName').text.strip()
            jockey = row.find('span', class_='RC-jockey').text.strip()
            odds = row.find('span', class_='RC-price').text.strip()
            horses.append([course, time_str, distance, horse, jockey, odds])
        except:
            continue
    return horses

def main():
    all_data = []
    for date in get_dates():
        race_urls = scrape_day(date)
        for race_url in race_urls:
            race_data = scrape_race_card(race_url)
            all_data.extend(race_data)

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Course', 'Time', 'Distance', 'Horse', 'Jockey', 'Odds'])
        writer.writerows(all_data)

    print(f"Saved {len(all_data)} entries to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
    driver.quit()
