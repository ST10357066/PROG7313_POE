# utils.py
import os
import logging
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
LEAN_URL = f"http://lean_engine:{os.getenv('LEAN_PORT', 6000)}/get_history"
logger = logging.getLogger(__name__)

def fetch_historical_data(symbol="AAPL", days=90, resolution="Minute"):
    """Fetch historical market data from the lean engine.
    
    Args:
        symbol (str): Stock symbol (default: 'AAPL').
        days (int): Number of days of data (default: 90).
        resolution (str): Data resolution (default: 'Minute').
    
    Returns:
        pd.DataFrame: Historical data or empty DataFrame on failure.
    """
    try:
        response = requests.post(LEAN_URL, json={"symbol": symbol, "days": days, "resolution": resolution}, timeout=10)
        response.raise_for_status()
        data = response.json().get("data", [])
        df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        df['time'] = pd.to_datetime(df['time'])
        return df
    except requests.RequestException as e:
        logger.error(f"Failed to fetch historical data: {e}")
        return pd.DataFrame()