import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from urllib.error import URLError
import time

@pytest.fixture(scope="module")
def browser():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        yield driver
        driver.quit()
    except Exception as e:
        pytest.skip(f"Chrome não está disponível no servidor: {e}")

def test_login_page_loads(browser):
    # A aplicação principal está rodando na porta 8050
    browser.get("http://127.0.0.1:8050/login")
    
    # Verifica se a página carregou
    assert "Sales Dashboard" in browser.page_source

def test_unauthenticated_redirect(browser):
    browser.get("http://127.0.0.1:8050/")
    time.sleep(2)  # Tempo para o redirect client-side (Location component) agir
    assert "/login" in browser.current_url
