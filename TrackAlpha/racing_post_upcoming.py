# TrackAlpha Scraper Pack: Racing Post Edition (Public Data)
# Part 1: Scrape Upcoming Races (Next 7 Days)

import time
import csv
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging

# --- Config --- #
BASE_URL = "https://www.racingpost.com/racecards/"
DAYS_AHEAD = 1
OUTPUT_FILE = "upcoming_races.csv"

# --- Logging Setup --- #
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# --- Selenium Options --- #
options = Options()
options.add_argument('--headless')
options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

# --- Helper Functions --- #
def get_dates():
    """Generate a list of dates for the next DAYS_AHEAD days."""
    return [(datetime.today() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(DAYS_AHEAD)]

def wait_for_element(driver, by, value, timeout=10):
    """Wait for an element to be present on the page."""
    try:
        return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
    except Exception as e:
        logger.error(f"Error waiting for element ({value}): {e}")
        return None

def close_modal(driver):
    """Handle and close modals if they appear."""
    modals = [
        ('RC-chooseBookieMobileExperiment__closeButton', "Bookmaker modal"),
        ('RC-mandatoryLogIn__closeIcon', "Login modal")
    ]
    for modal_class, modal_name in modals:
        try:
            logger.info(f"Checking for {modal_name}...")
            modal = wait_for_element(driver, By.CLASS_NAME, modal_class)
            if modal and modal.is_displayed():
                driver.execute_script("arguments[0].click();", modal)
                logger.info(f"{modal_name} closed successfully.")
            else:
                logger.info(f"{modal_name} is not visible.")
        except Exception as e:
            logger.info(f"No {modal_name} detected or unable to close it: {e}")

def scrape_day(driver, date_str):
    """Scrape all race URLs for a given day."""
    url = f"{BASE_URL}{date_str}"
    logger.info(f"Scraping {url}...")
    driver.get(url)
    wait_for_element(driver, By.CLASS_NAME, 'RC-meetingItem__link')

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    race_links = [
        "https://www.racingpost.com" + race.get('href')
        for race in soup.find_all('a', class_='RC-meetingItem__link')
        if race.get('href')
    ]
    logger.info(f"Found {len(race_links)} races for {date_str}.")
    return race_links

def scrape_race_card(driver, url):
    """Scrape race details from a race page."""
    logger.info(f"Loading race page: {url}")
    driver.get(url)
    close_modal(driver)
    time.sleep(2)  # Allow time for the page to load

    if not wait_for_element(driver, By.CLASS_NAME, 'RC-header', timeout=40):
        logger.error(f"Failed to load race page: {url}")
        return []

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    try:
        race_info = soup.find('div', class_='RC-header')
        course = race_info.find('span', class_='RC-header__raceInstanceTitle').text.strip()
        time_str = race_info.find('span', class_='RC-header__time').text.strip()
        distance = race_info.find('span', class_='RC-header__distance').text.strip()
    except AttributeError as e:
        logger.error(f"Error parsing race info: {e}")
        return []

    horses = []
    for row in soup.find_all('tr', class_='RC-runnerRow'):
        try:
            horse = row.find('a', class_='RC-runnerName').text.strip()
            jockey = row.find('span', class_='RC-jockey').text.strip()
            odds = row.find('span', class_='RC-price').text.strip()
            horses.append([course, time_str, distance, horse, jockey, odds])
        except AttributeError:
            continue
    logger.info(f"Scraped {len(horses)} horses from {url}.")
    return horses

# --- Main Function --- #
def main():
    """Main function to orchestrate the scraping process."""
    service = Service(ChromeDriverManager().install())
    with webdriver.Chrome(service=service, options=options) as driver:
        all_data = []
        for date in get_dates():
            race_urls = scrape_day(driver, date)
            for race_url in race_urls:
                race_data = scrape_race_card(driver, race_url)
                all_data.extend(race_data)
                time.sleep(2)  # Wait between requests

        # Save data to CSV
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Course', 'Time', 'Distance', 'Horse', 'Jockey', 'Odds'])
            writer.writerows(all_data)

        logger.info(f"Saved {len(all_data)} entries to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
