import os
import psycopg2
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class GenericScraper:
    def __init__(self, db_config):
        self.db_config = db_config
        self.driver = self._setup_driver()

    def _setup_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        # Prova a usare il binario installato nel Dockerfile se esiste
        if os.path.exists("/usr/bin/google-chrome"):
            options.binary_location = "/usr/bin/google-chrome"
        
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def save_to_db(self, data):
        conn = None
        try:
            # Se db_config è una stringa (DATABASE_URL), la usa direttamente
            if isinstance(self.db_config, str):
                conn = psycopg2.connect(self.db_config)
            else:
                conn = psycopg2.connect(**self.db_config)
                
            cur = conn.cursor()
            query = "INSERT INTO scraped_data (title, price, availability) VALUES (%s, %s, %s)"
            cur.executemany(query, data)
            conn.commit()
            cur.close()
        except Exception as e:
            print(f"Errore DB nello scraper: {e}")
        finally:
            if conn:
                conn.close()

    def scrape(self, start_url):
        print(f"Avvio scraping: {start_url}")
        self.driver.get(start_url)
        
        while True:
            books = self.driver.find_elements(By.CLASS_NAME, "product_pod")
            results = []

            for book in books:
                title = book.find_element(By.TAG_NAME, "h3").find_element(By.TAG_NAME, "a").get_attribute("title")
                price = book.find_element(By.CLASS_NAME, "price_color").text
                availability = book.find_element(By.CLASS_NAME, "instock").text.strip()
                results.append((title, price, availability))

            if results:
                self.save_to_db(results)
                print(f"Salvati {len(results)} libri.")

            try:
                next_btn = self.driver.find_element(By.CLASS_NAME, "next").find_element(By.TAG_NAME, "a")
                next_url = next_btn.get_attribute("href")
                self.driver.get(next_url)
            except:
                print("Fine pagine.")
                break

        self.driver.quit()
