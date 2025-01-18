import logging
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scrape_google_maps_reviews.log', mode='w'),  # Log to file
        logging.StreamHandler(sys.stdout)  # Log to console (for Jupyter/real-time output)
    ]
)

def get_overall_rating_and_review_count(business_name, address):
    logging.info(f"Scraping overall rating and review count for: {business_name}, located at: {address}")

    # Initialize WebDriver
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--remote-debugging-port=9222")
        driver = webdriver.Chrome(options=options)
        driver.maximize_window()
    except Exception as e:
        logging.error(f"Failed to initialize WebDriver: {e}")
        return {}

    try:
        # Open Google Maps
        driver.get("https://www.google.com/maps")
        wait = WebDriverWait(driver, 20)

        # Search for the business by name and address
        search_box = wait.until(EC.presence_of_element_located((By.ID, "searchboxinput")))
        search_box.clear()  # Clear the input box to avoid residual text
        search_box.send_keys(f"{business_name} {address}")
        search_box.send_keys(Keys.RETURN)
        time.sleep(5)

        # Extract overall rating and total number of reviews
        try:
            overall_rating = driver.find_element(By.CSS_SELECTOR, 'div.F7nice span[aria-hidden="true"]').text
            num_reviews_element = driver.find_element(By.CSS_SELECTOR, 'span[aria-label$="reviews"]')
            num_reviews = int(''.join(filter(str.isdigit, num_reviews_element.get_attribute('aria-label'))))
            logging.info(f"Overall Rating: {overall_rating}, Total Reviews: {num_reviews}")
        except Exception as e:
            logging.warning(f"Failed to extract overall rating or review count: {e}")
            overall_rating = "N/A"
            num_reviews = 0

        # Return the data
        result = {
            "Business Name": business_name,
            "Address": address,
            "Overall Rating": overall_rating,
            "Total Reviews": num_reviews,
        }
        logging.info(f"Data extracted: {result}")
        return result

    except Exception as e:
        logging.error(f"Error during scraping: {e}")
        return {}

    finally:
        driver.quit()