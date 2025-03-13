# lean_engine\lean_service.py
import os
import json
import logging
from flask import Flask, request, jsonify
from sqlalchemy import create_engine
import redis
from lean.cli import LeanCLI
from datetime import datetime, timedelta
from quantconnect.data import Consolidators
from quantconnect.data.market import TradeBar
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
redis_client = redis.Redis(host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")), decode_responses=True)
DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)
PORT = int(os.getenv("LEAN_PORT", 6000))

def download_historical_data(symbol, days, resolution="Daily"):
    """Download historical data using Lean CLI."""
    cli = LeanCLI()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    try:
        cli.data_download(
            dataset="US Equities",
            data_type="Trade",
            ticker=symbol.upper(),
            resolution=resolution.lower(),
            start=start_date.strftime("%Y%m%d"),
            end=end_date.strftime("%Y%m%d"),
            output=DATA_DIR
        )
        data_file = f"{DATA_DIR}/{symbol.lower()}/trade_{resolution.lower()}.csv"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                return [line.strip().split(',') for line in f.readlines()]
        return []
    except Exception as e:
        logger.error(f"Error downloading data for {symbol}: {e}")
        return []

def consolidate_data(raw_data, symbol, timeframe_minutes=15):
    """Consolidate raw data into timeframes."""
    consolidator = Consolidators.TradeBarConsolidator(timedelta(minutes=timeframe_minutes))
    consolidated = []
    
    def on_consolidated(bar):
        consolidated.append({
            'time': bar.time.isoformat(),
            'open': float(bar.open),
            'high': float(bar.high),
            'low': float(bar.low),
            'close': float(bar.close),
            'volume': int(bar.volume)
        })
    
    consolidator.DataConsolidated += on_consolidated
    for row in raw_data[1:]:  # Skip header
        try:
            time = datetime.strptime(row[0], '%Y%m%d %H:%M:%S')
            bar = TradeBar(time, symbol=symbol, open=float(row[1]), high=float(row[2]), 
                          low=float(row[3]), close=float(row[4]), volume=int(row[5]))
            consolidator.update(bar)
        except Exception as e:
            logger.error(f"Error consolidating row {row}: {e}")
    return consolidated

def get_historical_data(symbol, days, resolution="Daily"):
    """Fetch or retrieve cached historical data."""
    cache_key = f"{symbol}_{days}_{resolution}"
    cached_data = redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    data = download_historical_data(symbol, days, resolution)
    redis_client.set(cache_key, json.dumps(data), ex=3600)
    return data

@app.route('/get_history', methods=['POST'])
def get_history():
    payload = request.get_json()
    symbol = payload.get('symbol', 'AAPL')
    days = payload.get('days', 30)
    resolution = payload.get('resolution', 'Daily')
    consolidate = payload.get('consolidate', False)
    timeframe = payload.get('timeframe_minutes', 15)
    data = get_historical_data(symbol, days, resolution)
    if consolidate and resolution.lower() == 'minute':
        data = consolidate_data(data, symbol, timeframe)
    return jsonify({'symbol': symbol, 'data': data})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)