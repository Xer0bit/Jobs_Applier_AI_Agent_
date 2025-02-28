from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from src.config import CHROME_DRIVER_PATH

def setup_chrome_driver():
    """
    Sets up the Chrome WebDriver with specified options.
    """
    chrome_options = Options()
    # Add any desired Chrome options here.  For example:
    # chrome_options.add_argument("--headless")  # Run in headless mode
    # chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration

    service = Service(executable_path=CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver
