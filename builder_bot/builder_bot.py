# builder_bot/builder_bot.py
import os
import json
import logging
import requests
from flask import Flask, request, jsonify
import pika
from utils import fetch_historical_data
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)  # Fixed: Correct Flask initialization
PORT = int(os.getenv("BUILDER_PORT", 5001))
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS")

bot_config_count = 0

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials))
channel = connection.channel()
channel.queue_declare(queue='bot_configs', durable=True)

def analyze_market(df):
    """Calculate market volatility to determine strategy."""
    return df['close'].pct_change().std()

@app.route('/generate_bot', methods=['POST'])
def generate_bot():
    global bot_config_count
    data = request.get_json()
    if not data or 'symbol' not in data:
        return jsonify({"error": "Missing symbol in request"}), 400
    symbol = data['symbol']
    df = fetch_historical_data(symbol)
    if df.empty:
        logger.error(f"No historical data for {symbol}")
        return jsonify({"error": "No historical data available"}), 500
    volatility = analyze_market(df)
    strategy = 'statistical_arbitrage' if volatility > 0.2 else 'market_making'
    config = {
        'bot_id': bot_config_count + 1000,
        'strategy': strategy,
        'parameters': {
            'execution_speed_ms': 10,
            'data_sources': ['market', 'news', 'social_media'],
            'model_type': 'reinforcement_learning' if strategy == 'statistical_arbitrage' else 'transformer'
        }
    }
    channel.basic_publish(exchange='', routing_key='bot_configs', body=json.dumps(config), properties=pika.BasicProperties(delivery_mode=2))
    bot_config_count += 1
    logger.info(f"Generated bot config: {config}")
    return jsonify({'status': 'generated', 'config': config}), 200

@app.route('/update_config', methods=['POST'])
def update_config():
    new_config = request.get_json()
    logger.info(f"Received new configuration: {new_config}")
    return jsonify({"status": "config updated"}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)