# TrackAlpha Scraper Pack: Racing Post Edition (Public Data)
# Part 1: Scrape Upcoming Races (Next 7 Days)

from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import logging
import csv
import time

# --- Setup Logging --- #
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger()

# --- Config --- #
BASE_URL = "https://www.racingpost.com/racecards/"
DAYS_AHEAD = 1
OUTPUT_FILE = "upcoming_racecards.csv"

# --- Selenium Setup --- #
options = Options()
options.add_argument("--headless=new")
options.add_argument("window-size=1920,1080")
options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# --- Helper Functions --- #
def get_dates():
    """Generate a list of dates for the next DAYS_AHEAD days."""
    return [(datetime.today() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(DAYS_AHEAD)]

def wait_for_element(driver, by, value, timeout=10):
    """Wait for an element to be present on the page."""
    try:
        return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
    except Exception as e:
        logger.warning(f"Timeout waiting for element ({value}): {e}")
        return None

def get_meeting_links(date_str):
    """Get all meeting links for a specific date."""
    url = f"{BASE_URL}{date_str}"
    logger.info(f"Fetching meetings for {date_str}: {url}")
    driver.get(url)
    time.sleep(3)  # Allow time for the page to load
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    return ["https://www.racingpost.com" + a['href'] for a in soup.select('a.RC-meetingItem__link[href]')]

def get_race_links(meeting_url):
    """Get all race links for a specific meeting."""
    logger.info(f"Fetching races from meeting: {meeting_url}")
    driver.get(meeting_url)
    if not wait_for_element(driver, By.CLASS_NAME, "RC-cardHeader__raceInstance", timeout=10):
        logger.warning(f"Timeout waiting for races in {meeting_url}")
        return []

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    return [
        "https://www.racingpost.com" + a['href']
        for a in soup.select('a.RC-cardHeader__raceInstance[href]')
    ]

def scrape_race_card(url):
    """Scrape details of a specific race card."""
    logger.info(f"Scraping race card: {url}")
    driver.get(url)
    time.sleep(3)  # Allow time for the page to load
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    try:
        header = soup.select_one('.RC-header')
        course = header.select_one('.RC-header__raceInstanceTitle').text.strip()
        race_time = header.select_one('.RC-header__time').text.strip()
        distance = header.select_one('.RC-header__distance').text.strip()
    except Exception as e:
        logger.warning(f"Header parsing failed for {url}: {e}")
        return []

    horses = []
    for row in soup.select('tr.RC-runnerRow'):
        try:
            horse = row.select_one('.RC-runnerName').text.strip()
            jockey = row.select_one('.RC-jockey').text.strip()
            odds = row.select_one('.RC-price').text.strip()
            horses.append([course, race_time, distance, horse, jockey, odds])
        except Exception:
            continue

    logger.info(f"Scraped {len(horses)} horses from {url}")
    return horses

# --- Main Function --- #
def main():
    """Main function to orchestrate the scraping process."""
    all_entries = []
    for date_str in get_dates():
        logger.info(f"Processing date: {date_str}")
        meetings = get_meeting_links(date_str)
        logger.info(f"Found {len(meetings)} meetings for {date_str}")
        for meeting in meetings:
            races = get_race_links(meeting)
            logger.info(f"Found {len(races)} races in meeting: {meeting}")
            for race_url in races:
                race_data = scrape_race_card(race_url)
                all_entries.extend(race_data)
                time.sleep(2)  # Wait between requests

    # Save to CSV
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Course', 'Time', 'Distance', 'Horse', 'Jockey', 'Odds'])
        writer.writerows(all_entries)

    logger.info(f"Saved {len(all_entries)} rows to {OUTPUT_FILE}")

if __name__ == "__main__":
    try:
        main()
    finally:
        driver.quit()
