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
from logging.handlers import RotatingFileHandler
import os
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import platform
import shutil

# Load environment variables
load_dotenv()

# Configure logging
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.DEBUG

# Root logger
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(LOG_LEVEL)
console_formatter = logging.Formatter(LOG_FORMAT)
console_handler.setFormatter(console_formatter)

# Rotating file handler (debug.log) - 1MB max, keep 5 backups
log_file = 'debug.log'
file_handler = RotatingFileHandler(log_file, maxBytes=1 * 1024 * 1024, backupCount=5)
file_handler.setLevel(LOG_LEVEL)
file_handler.setFormatter(console_formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)


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
        days = [0, 1, 2, 3, 4, 5, 6]  # Monday to Friday
        random.shuffle(days)

        schedule = {}
        # First 3 days are office
        for day in days[:3]:
            schedule[day] = "office"
        # Last 2 days are home
        for day in days[3:]:
            schedule[day] = "home"

        logger.info(f"Weekly schedule generated: {schedule}")
        return schedule

    def setup_driver(self):
        """Initialize Chrome driver with options"""
        options = webdriver.ChromeOptions()

        # Common options
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--no-first-run')

        system = platform.system().lower()

        # Try to find a suitable binary
        chrome_binary = None
        if system == 'linux':
            # Common chromium/chrome binary locations
            for candidate in ("/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable"):
                if shutil.which(candidate) or os.path.exists(candidate):
                    chrome_binary = candidate
                    break
            # Fallback to PATH lookup
            if not chrome_binary:
                found = shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
                chrome_binary = found

            # Always run headless on Linux server by default
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')

            # If we found a binary, tell ChromeOptions to use it
            if chrome_binary:
                options.binary_location = chrome_binary
                is_chromium = 'chromium' in chrome_binary.lower()
                logger.info(f"setup_driver: using {'Chromium' if is_chromium else 'Chrome'} binary at: {chrome_binary}")
                
                # Use ChromeType.CHROMIUM for Chromium binary, otherwise default to Chrome
                if is_chromium:
                    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
                    logger.info("setup_driver: using ChromeType.CHROMIUM driver")
                else:
                    service = Service(ChromeDriverManager().install())
                    logger.info("setup_driver: using standard Chrome driver")
            else:
                # No binary found, but still try with default Chrome setup
                logger.warning("setup_driver: no Chrome/Chromium binary found, using default setup")
                service = Service(ChromeDriverManager().install())

        elif system == 'windows':
            # On Windows use visible Chrome for development
            service = Service(ChromeDriverManager().install())
            logger.info("setup_driver: using standard Chrome driver for Windows")
            # avoid headless on Windows so tester can see the browser

        else:
            # Default: let webdriver_manager choose Chrome
            service = Service(ChromeDriverManager().install())
            logger.info("setup_driver: using standard Chrome driver")

        try:
            drv_path = service.path or getattr(service, 'executable_path', None)
            if drv_path:
                logger.info(f"setup_driver: chromedriver installed at: {drv_path}")
        except Exception as e:
            logger.debug(f"setup_driver: couldn't get driver path: {e}")

        self.driver = webdriver.Chrome(service=service, options=options)

        # Set default timeouts
        self.driver.set_page_load_timeout(30)
        self.driver.implicitly_wait(10)

    def get_current_location(self):
        """Read the currently selected location label and return 'office' or 'home' or None"""
        try:
            # the visible element for selected value
            elem = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="remote_holder"]/span/span[1]/span'))
            )
            text = elem.text.strip().lower()
            if 'office' in text or 'in the office' in text:
                return 'office'
            if 'home' in text:
                return 'home'
            return None
        except Exception:
            return None

    def login(self):
        """Login to the portal"""
        try:
            self.driver.get(self.portal_url)
            wait = WebDriverWait(self.driver, 10)

            # Wait for login form and ensure we're on login page
            login_form = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "kt-login_form"))
            )

            # Find username and password fields directly
            username_input = self.driver.find_element(By.NAME, "_username")
            password_input = self.driver.find_element(By.NAME, "_password")

            # Clear and enter username
            username_input.clear()
            username_input.send_keys(self.username)
            logger.info("Username entered")

            # Clear and enter password
            password_input.clear()
            password_input.send_keys(self.password)
            logger.info("Password entered")

            # Find and click login button
            login_button = self.driver.find_element(By.ID, "kt_login_signin_submit")
            login_button.click()
            logger.info("Login button clicked")

            # Wait for redirect
            wait.until(lambda driver: driver.current_url != self.portal_url)
            current_url = self.driver.current_url
            logger.info(f"Current URL after login: {current_url}")

            if "login" not in current_url.lower():
                logger.info("Login successful - redirected to dashboard")
                return True
            else:
                logger.error("Still on login page after attempt")
                return False

        except TimeoutException:
            logger.error("Timeout waiting for redirect after login")
            return False

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False

    def click_start_work(self):
        """Click the start work button (preserve previously selected location)."""
        try:
            wait = WebDriverWait(self.driver, 10)

            # Small pause to ensure page settled after selection
            time.sleep(2)

            # Preserve current location before clicking start
            previous_location = self.get_current_location()

            # Use the provided XPath selector (do not try alternatives)
            by, selector = (By.XPATH, "//button[@data-id='1' and contains(@class, 'start-work-button')]")

            try:
                start_button = wait.until(EC.element_to_be_clickable((by, selector)))
                start_button.click()
                logger.info(f"Successfully clicked start button using selector: {selector}")

                # Wait briefly and verify location didn't change
                time.sleep(2)
                current_location = self.get_current_location()
                if previous_location and current_location != previous_location:
                    logger.warning("Location changed after clicking start; attempting to reapply previous location")
                    # try to reapply previous location (one attempt)
                    if previous_location:
                        self.select_location(previous_location)

                return True

            except (TimeoutException, NoSuchElementException):
                logger.error("Could not find or click start button with the XPath selector")
                return False

        except Exception as e:
            logger.error(f"Error clicking start work: {str(e)}")
            return False

    def click_stop_work(self):
        """Click the stop work button"""
        try:
            wait = WebDriverWait(self.driver, 10)

            # First make sure the page is fully loaded after location selection
            time.sleep(2)

            # Try different selectors for the start button
            by, selector = (By.XPATH, "//button[@data-id='6' and contains(@class, 'end-work-button')]")

            try:
                # Try to find the button
                stop_button = wait.until(EC.presence_of_element_located((by, selector)))
                stop_button.click()
                logger.info(f"Successfully clicked stop button using selector: {selector}")
                return True

            except (TimeoutException, NoSuchElementException):
                # If we get here, no button was found
                logger.error("Could not find or click stop button with any selector")
                return False

        except Exception as e:
            logger.error(f"Error clicking stop work: {str(e)}")
            return False

    def select_location(self, location):
        """
        Select work location (office or home)
        Args:
            location (str): "office" or "home"
        """
        try:
            wait = WebDriverWait(self.driver, 10)

            # Find the dropdown using the exact XPath
            try:
                remote_select = wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="remote_holder"]/span/span[1]/span'))
                )
                logger.info("Found dropdown using exact XPath")
                remote_select.click()
                logger.info("Clicked dropdown successfully")

            except (TimeoutException, NoSuchElementException):
                logger.error("Could not find location dropdown or click it")
                return False

            # Select the appropriate option
            if location.lower() == "office":
                option_text = "In the office"
                data_id = "0"
            else:
                option_text = "Home office"
                data_id = "1"

            # Try to find the option using XPath
            by, selector = (By.XPATH, f"//div[@data-id='{data_id}'][contains(text(), '{option_text}')]")

            attempts = 0
            while attempts < 3:
                try:
                    option = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((by, selector)))
                    option.click()
                    logger.info(f"Selected location '{option_text}' using selector: {selector}")
                    # Wait until UI reflects selection
                    time.sleep(1)
                    current = self.get_current_location()
                    if current == location.lower():
                        return True
                    attempts += 1
                    logger.warning(f"Location selection not reflected yet (attempt {attempts}), retrying")
                    # reopen dropdown before retry
                    remote_select = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="remote_holder"]/span/span[1]/span'))
                    )
                    remote_select.click()

                except (TimeoutException, NoSuchElementException) as e:
                    logger.error(f"Failed with selector {selector}: {str(e)}")
                    return False

            logger.error("Failed to confirm location selection after retries")
            return False

        except Exception as e:
            logger.error(f"Error in select_location: {str(e)}")
            return False

    def morning_routine(self):
        """Execute morning login routine"""
        today = datetime.now().weekday()

        logger.info("Starting morning routine")

        try:
            self.setup_driver()
            logger.info("Driver setup complete")

            if not self.login():
                raise Exception("Login failed")
            logger.info("Login successful, waiting for page load")

            time.sleep(3)  # Wait for page to fully load after login

            location = self.weekly_schedule[today]
            logger.info(f"Attempting to select location: {location}")

            if not self.select_location(location):
                raise Exception("Failed to select location")
            logger.info("Location selection successful")

            time.sleep(2)  # Brief pause before clicking start

            if not self.click_start_work():
                raise Exception("Failed to click start work button")
            logger.info("Start work button clicked successfully")

            # Keep browser open for a bit, then close
            time.sleep(5)

        except Exception as e:
            logger.error(f"Morning routine error: {str(e)}")
            # Log the current URL to help with debugging
            if self.driver:
                logger.error(f"Current URL when error occurred: {self.driver.current_url}")
                # Take screenshot on error
                try:
                    self.driver.save_screenshot("error_screenshot.png")
                    logger.info("Error screenshot saved as error_screenshot.png")
                except Exception as ss_err:
                    logger.error(f"Failed to save screenshot: {str(ss_err)}")
        finally:
            if self.driver:
                self.driver.quit()

    def evening_routine(self):
        """Execute evening logout routine"""
        today = datetime.now().weekday()

        logger.info("Starting evening routine")

        try:
            self.setup_driver()
            logger.info("Driver setup complete")

            if not self.login():
                raise Exception("Login failed")
            logger.info("Login successful, waiting for page load")

            time.sleep(3)  # Wait for page to fully load after login

            if not self.click_stop_work():
                raise Exception("Failed to click stop work button")
            logger.info("Stop work button clicked successfully")

            # Keep browser open for a bit, then close
            time.sleep(5)

        except Exception as e:
            logger.error(f"Evening routine error: {str(e)}")
            # Log the current URL to help with debugging
            if self.driver:
                logger.error(f"Current URL when error occurred: {self.driver.current_url}")
                # Take screenshot on error
                try:
                    self.driver.save_screenshot("error_screenshot.png")
                    logger.info("Error screenshot saved as error_screenshot.png")
                except Exception as ss_err:
                    logger.error(f"Failed to save screenshot: {str(ss_err)}")
        finally:
            if self.driver:
                self.driver.quit()


    def cleanup(self):
        """Cleanup resources"""
        if self.driver:
            self.driver.quit()


def calculate_random_time(base_hour, base_minute, variance_minutes=30):
    """
    Calculate a random time around the base time with random seconds

    Args:
        base_hour (int): Base hour (24-hour format)
        base_minute (int): Base minute
        variance_minutes (int): +/- variance in minutes

    Returns:
        str: Time in HH:MM format
    """
    # Random offset between -variance and +variance
    offset = random.randint(-variance_minutes, variance_minutes)

    # Generate random seconds
    random_seconds = random.randint(0, 59)

    base_time = datetime.now().replace(hour=base_hour, minute=base_minute, second=random_seconds)
    random_time = base_time + timedelta(minutes=offset)

    return random_time.strftime("%H:%M:%S")


def schedule_tasks(automation):
    """Schedule daily tasks with random times"""
    # Clear any existing schedules
    schedule.clear()

    # Generate random times for today
    morning_time = calculate_random_time(8, 0, 30)
    evening_time = calculate_random_time(16, 0, 30)

    # Schedule tasks (using only HH:MM part for schedule library compatibility)
    morning_schedule_time = morning_time[:5]  # Get only HH:MM part
    evening_schedule_time = evening_time[:5]  # Get only HH:MM part

    logger.info(f"Today's schedule - Morning: {morning_schedule_time}, Evening: {evening_schedule_time}")

    # Schedule morning tasks
    schedule.every().monday.at(morning_schedule_time).do(automation.morning_routine)
    schedule.every().tuesday.at(morning_schedule_time).do(automation.morning_routine)
    schedule.every().wednesday.at(morning_schedule_time).do(automation.morning_routine)
    schedule.every().thursday.at(morning_schedule_time).do(automation.morning_routine)
    schedule.every().friday.at(morning_schedule_time).do(automation.morning_routine)

    # Schedule evening tasks
    schedule.every().monday.at(evening_schedule_time).do(automation.evening_routine)
    schedule.every().tuesday.at(evening_schedule_time).do(automation.evening_routine)
    schedule.every().wednesday.at(evening_schedule_time).do(automation.evening_routine)
    schedule.every().thursday.at(evening_schedule_time).do(automation.evening_routine)
    schedule.every().friday.at(evening_schedule_time).do(automation.evening_routine)

    # ### Tests
    automation.morning_routine()
    automation.evening_routine()

    # Regenerate weekly schedule every Monday at midnight
    schedule.every().monday.at("00:01").do(lambda: automation.generate_weekly_schedule())

    # Reschedule with new random times every day at midnight
    schedule.every().day.at("00:00").do(lambda: schedule_tasks(automation))


def main():
    """Main application entry point"""
    # IMPORTANT: Update these with your actual credentials and URL
    username = os.getenv("CALCLICK_USER")
    password = os.getenv("CALCLICK_PASS")

    logger.info("Starting Work Portal Automation System")

    # Initialize automation
    automation = WorkPortalAutomation(WORK_PORTAL_URL, username, password)

    # Schedule tasks
    schedule_tasks(automation)

    logger.info("Scheduler initialized. Running...")

    # Run scheduler loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        automation.cleanup()


if __name__ == "__main__":
    main()
