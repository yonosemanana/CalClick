from dotenv import load_dotenv
import schedule
import time
import random
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import os
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('work_automation.log'),
        logging.StreamHandler()
    ]
)

WORK_PORTAL_URL = "https://panel.rcponline.pl/login/"

class WorkPortalAutomation:
    def __init__(self, portal_url, username, password):
        """
        Initialize the automation system

        Args:
            portal_url (str): URL of the work portal
            username (str): Login username
            password (str): Login password
        """
        self.portal_url = portal_url
        self.username = username
        self.password = password
        self.driver = None
        self.weekly_schedule = self.generate_weekly_schedule()

    def generate_weekly_schedule(self):
        """
        Generate random weekly schedule: 3 days office, 2 days home
        Returns dict with day numbers (0=Monday) and location
        """
        days = [0, 1, 2, 3, 4]  # Monday to Friday
        random.shuffle(days)

        schedule = {}
        # First 3 days are office
        for day in days[:3]:
            schedule[day] = "office"
        # Last 2 days are home
        for day in days[3:]:
            schedule[day] = "home"

        logging.info(f"Weekly schedule generated: {schedule}")
        return schedule

    def setup_driver(self):
        """Initialize Chrome driver with options"""
        options = webdriver.ChromeOptions()
        # Uncomment below to run headless
        # options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.maximize_window()

    def login(self):
        """Login to the portal"""
        try:
            self.driver.get(self.portal_url)
            wait = WebDriverWait(self.driver, 10)

            # Wait for the username field to appear
            wait.until(EC.presence_of_element_located((By.NAME, "_username")))

            # Locate elements precisely by 'name' or 'id'
            username_input = self.driver.find_element(By.NAME, "_username")
            password_input = self.driver.find_element(By.NAME, "_password")
            login_button = self.driver.find_element(By.ID, "kt_login_signin_submit")
            logging.debug(username_input)

            # Fill in the form
            username_input.clear()
            username_input.send_keys(self.username)
            password_input.clear()
            password_input.send_keys(self.password)

            # Submit the form
            login_button.click()

            # Wait for redirect or confirmation (adjust timeout as needed)
            wait.until(EC.url_changes(self.driver.current_url))

            logging.info(f"Current URL: {self.driver.current_url}")
            logging.info("Login successful")
            return True

        except TimeoutException:
            logging.error("Login failed - timeout")
            return False
        except Exception as e:
            logging.error(f"Login error: {str(e)}")
            return False

    def click_start_work(self):
        """Click the start work button"""
        try:
            wait = WebDriverWait(self.driver, 10)

            # Updated selectors for start work based on the HTML
            selectors = [
                (By.XPATH, "//option[@value='1'][@data-content='<i class=\"fa fa-play text-success me-3\"></i>work_start']"),
                (By.XPATH, "//button[contains(@data-content, 'work_start')]"),
                (By.XPATH, "//button[contains(@class, 'text-success') and contains(., 'Start')]"),
                (By.XPATH, "//*[contains(@class, 'fa-play')]")
            ]

            for by, selector in selectors:
                try:
                    start_button = wait.until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    start_button.click()
                    logging.info(f"Clicked start work button using selector: {selector}")
                    return True
                except (TimeoutException, NoSuchElementException):
                    continue

            raise Exception("Start work button not found")

        except Exception as e:
            logging.error(f"Error clicking start work: {str(e)}")
            return False

    def click_stop_work(self):
        """Click the stop work button"""
        try:
            wait = WebDriverWait(self.driver, 10)

            # Updated selectors for stop work based on the HTML
            selectors = [
                (By.XPATH, "//option[@value='6'][@data-content='<i class=\"fa fa-stop text-danger me-3\"></i>work_finish']"),
                (By.XPATH, "//button[contains(@data-content, 'work_finish')]"),
                (By.XPATH, "//button[contains(@class, 'text-danger') and contains(., 'Stop')]"),
                (By.XPATH, "//*[contains(@class, 'fa-stop')]")
            ]

            for by, selector in selectors:
                try:
                    stop_button = wait.until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    stop_button.click()
                    logging.info(f"Clicked stop work button using selector: {selector}")
                    return True
                except (TimeoutException, NoSuchElementException):
                    continue

            raise Exception("Stop work button not found")

        except Exception as e:
            logging.error(f"Error clicking stop work: {str(e)}")
            return False

    def select_location(self, location):
        """
        Select work location (office or home)

        Args:
            location (str): "office" or "home"
        """
        try:
            wait = WebDriverWait(self.driver, 10)

            # Updated selectors for location based on the HTML
            location_map = {
                "office": [
                    (By.XPATH, "//button[contains(@class, 'office-btn')]"),
                    (By.XPATH, "//input[@value='office']"),
                    (By.XPATH, "//button[contains(text(), 'Office')]")
                ],
                "home": [
                    (By.XPATH, "//option[@value='22'][@data-content='<i class=\"fas fa-home text-dark-green\"></i>Home office registered']"),
                    (By.XPATH, "//option[@value='23'][@data-content='<i class=\"fas fa-home text-dark-green\"></i>Home office unregistered']"),
                    (By.XPATH, "//button[contains(@class, 'home-btn')]"),
                    (By.XPATH, "//input[@value='home']"),
                    (By.XPATH, "//button[contains(text(), 'Home')]")
                ]
            }

            selectors = location_map.get(location.lower(), [])
            for by, selector in selectors:
                try:
                    location_button = wait.until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    location_button.click()
                    logging.info(f"Selected location: {location} using selector: {selector}")
                    return True
                except (TimeoutException, NoSuchElementException):
                    continue

            raise Exception(f"No matching {location} button found")

        except Exception as e:
            logging.error(f"Error selecting location: {str(e)}")
            return False

    def morning_routine(self):
        """Execute morning login routine"""
        today = datetime.now().weekday()

        # # Check if it's a business day (Monday=0 to Friday=4)
        # if today > 4:
        #     logging.info("Weekend - skipping morning routine")
        #     return

        logging.info("Starting morning routine")

        try:
            self.setup_driver()

            if self.login():
                location = self.weekly_schedule[today]
                if self.select_location(location):
                    time.sleep(2)  # Brief pause
                    self.click_start_work()

            # Keep browser open for a bit, then close
            time.sleep(5)

        except Exception as e:
            logging.error(f"Morning routine error: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()

    def evening_routine(self):
        """Execute evening logout routine"""
        today = datetime.now().weekday()

        # Check if it's a business day
        if today > 4:
            logging.info("Weekend - skipping evening routine")
            return

        logging.info("Starting evening routine")

        try:
            self.setup_driver()

            if self.login():
                time.sleep(2)
                self.click_stop_work()

            time.sleep(5)

        except Exception as e:
            logging.error(f"Evening routine error: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()

    def cleanup(self):
        """Cleanup resources"""
        if self.driver:
            self.driver.quit()


def calculate_random_time(base_hour, base_minute, variance_minutes=30):
    """
    Calculate a random time around the base time

    Args:
        base_hour (int): Base hour (24-hour format)
        base_minute (int): Base minute
        variance_minutes (int): +/- variance in minutes

    Returns:
        str: Time in HH:MM format
    """
    # Random offset between -variance and +variance
    offset = random.randint(-variance_minutes, variance_minutes)

    base_time = datetime.now().replace(hour=base_hour, minute=base_minute, second=0)
    random_time = base_time + timedelta(minutes=offset)

    return random_time.strftime("%H:%M")


def schedule_tasks(automation):
    """Schedule daily tasks with random times"""
    # Clear any existing schedules
    schedule.clear()

    # Generate random times for today
    morning_time = calculate_random_time(8, 0, 30)
    evening_time = calculate_random_time(16, 0, 30)

    logging.info(f"Today's schedule - Morning: {morning_time}, Evening: {evening_time}")

    # Schedule tasks
    schedule.every().monday.at(morning_time).do(automation.morning_routine)
    schedule.every().tuesday.at(morning_time).do(automation.morning_routine)
    schedule.every().wednesday.at(morning_time).do(automation.morning_routine)
    schedule.every().thursday.at(morning_time).do(automation.morning_routine)
    schedule.every().friday.at(morning_time).do(automation.morning_routine)

    schedule.every().monday.at(evening_time).do(automation.evening_routine)
    schedule.every().tuesday.at(evening_time).do(automation.evening_routine)
    schedule.every().wednesday.at(evening_time).do(automation.evening_routine)
    schedule.every().thursday.at(evening_time).do(automation.evening_routine)
    schedule.every().friday.at(evening_time).do(automation.evening_routine)

    ### Tests
    automation.morning_routine()


    # Regenerate weekly schedule every Monday at midnight
    schedule.every().monday.at("00:01").do(lambda: automation.generate_weekly_schedule())

    # Reschedule with new random times every day at midnight
    schedule.every().day.at("00:00").do(lambda: schedule_tasks(automation))


def main():
    """Main application entry point"""
    # IMPORTANT: Update these with your actual credentials and URL
    username = os.getenv("CALCLICK_USER")
    password = os.getenv("CALCLICK_PASS")

    logging.info("Starting Work Portal Automation System")

    # Initialize automation
    automation = WorkPortalAutomation(WORK_PORTAL_URL, username, password)

    # Schedule tasks
    schedule_tasks(automation)

    logging.info("Scheduler initialized. Running...")

    # Run scheduler loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        automation.cleanup()


if __name__ == "__main__":
    main()
