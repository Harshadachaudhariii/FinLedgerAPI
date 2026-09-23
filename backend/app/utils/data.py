import json
from app.utils.logger import logger


def load_data():
    try:
        with open("./data/transactions.json", "r") as f:
            data = json.load(f)
            logger.info("Data loaded successfully from transactions.json")
            return data
    except FileNotFoundError:
        logger.exception("Data file not found while loading transactions.json")
        raise
    except json.JSONDecodeError:
        logger.exception("Invalid JSON found in transactions.json")
        raise


def save_data(data):
    try:
        with open('./data/transactions.json', 'w') as f:
            json.dump(data, f, indent=4)
        logger.info("Data saved successfully to transactions.json")
    except OSError:
        logger.exception("Failed to save data to transactions.json")
        raise