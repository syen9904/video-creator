import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class Browser:
    def __init__(self, url, seconds = 10):
        self.driver = None
        self.url = url
        self.seconds = seconds
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service)
        self.driver.get(self.url)

    def scroll_find(self, xpath, button=False, scroll=False):
        try:
            element = WebDriverWait(self.driver, self.seconds).until(
                  EC.presence_of_element_located((By.XPATH, xpath)))
            return element
        except:
            if not scroll: return None
            os.system("osascript -e 'tell application \"Google Chrome\" to activate'")
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            try:
                element = WebDriverWait(self.driver, self.seconds).until(
                    EC.presence_of_element_located((By.XPATH, xpath)))
                return element
            except:
                return None