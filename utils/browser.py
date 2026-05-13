from __future__ import annotations
import logging
import os
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

logger = logging.getLogger("rpa_challenge")


def create_chrome_driver(
    *,
    headless: bool = False,
    implicit_wait_seconds: float = 5.0,
    download_dir: Optional[Path] = None,
) -> webdriver.Chrome:
    """Cria e configura a instância do Chrome."""
    options = ChromeOptions()
    chrome_bin = os.environ.get("CHROME_BIN", "").strip()
    if chrome_bin:
        options.binary_location = chrome_bin
        logger.info("Usando binário do navegador: %s", chrome_bin)
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")

    if download_dir is not None:
        download_dir.mkdir(parents=True, exist_ok=True)
        prefs = {
            "download.default_directory": str(download_dir.resolve()),
            "download.prompt_for_download": False,
        }
        options.add_experimental_option("prefs", prefs)

    driver_path = os.environ.get("CHROMEDRIVER_PATH", "").strip()
    if driver_path:
        service = ChromeService(executable_path=driver_path)
        logger.info("Usando ChromeDriver: %s", driver_path)
    else:
        service = ChromeService()

    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(implicit_wait_seconds)
    logger.info("WebDriver Chrome iniciado com sucesso.")
    return driver
