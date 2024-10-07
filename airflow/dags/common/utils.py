# File: dags/common/utils.py
import os
from dotenv import load_dotenv
from config import scraper_config

def load_env_vars():
    load_dotenv()

def get_env_var(var_name):
    return os.getenv(var_name)

def get_scraper_config():
    return scraper_config.SCRAPER_CONFIG

def get_csv_combiner_config():
    return scraper_config.CSV_COMBINER_CONFIG

def get_global_settings():
    return scraper_config.GLOBAL_SETTINGS