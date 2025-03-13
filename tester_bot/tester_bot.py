# tester_bot/tester_bot.py
import os
import json
import logging
import requests
from flask import Flask, request, jsonify
import pika
from stable_baselines3 import PPO
import numpy as np
from utils import fetch_historical_data
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
PORT = int(os.getenv("TESTER_PORT", 5002))
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS")

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials))
channel = connection.channel()
channel.queue_declare(queue='test_results', durable=True)

@app.route('/test_bot', methods=['POST'])
def test_bot():
    config = request.get_json()
    if not config or 'bot_id' not in config:
        return jsonify({"error": "Missing bot_id"}), 400
    model_path = f"/app/models/model_{config['bot_id']}.zip"
    if not os.path.exists(model_path):
        logger.error(f"Model {model_path} not found")
        return jsonify({"error": f"Model {model_path} not found"}), 404
    model = PPO.load(model_path)
    df = fetch_historical_data()
    if df.empty:
        logger.error("No historical data available for testing")
        return jsonify({'error': 'No data'}), 500
    obs = df.iloc[0].values
    total_reward = 0
    wins = 0
    total_trades = 0
    for i in range(len(df) - 1):
        action, _ = model.predict(obs)
        reward = action[0] * df['close'].pct_change().iloc[i + 1]
        if reward > 0:
            wins += 1
        total_trades += 1
        total_reward += reward
        obs = df.iloc[i + 1].values
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
    result = {
        'bot_id': config['bot_id'],
        'total_reward': float(total_reward),
        'sharpe_ratio': float(total_reward / df['close'].pct_change().std() * np.sqrt(252)),
        'win_rate': win_rate,
        'timestamp': datetime.now().isoformat()
    }
    channel.basic_publish(exchange='', routing_key='test_results', body=json.dumps(result), properties=pika.BasicProperties(delivery_mode=2))
    logger.info(f"Testing completed for bot_id: {config['bot_id']}")
    return jsonify(result), 200

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