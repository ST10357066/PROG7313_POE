# trainer_bot\trainer_bot.py
import os
import json
import logging
import requests
from flask import Flask, request, jsonify
import pika
from stable_baselines3 import PPO
from gym import Env
from gym.spaces import Box
import numpy as np
from utils import fetch_historical_data
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
PORT = int(os.getenv("TRAINER_PORT", 5006))
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS")

class TradingEnv(Env):
    """Custom Gym environment for trading."""
    def __init__(self, df):
        super().__init__()
        self.df = df
        self.action_space = Box(low=-1, high=1, shape=(2,), dtype=np.float32)
        self.observation_space = Box(low=0, high=np.inf, shape=(6,), dtype=np.float32)
        self.current_step = 0

    def reset(self):
        self.current_step = 0
        return self.df.iloc[self.current_step].values

    def step(self, action):
        self.current_step += 1
        reward = action[0] * self.df['close'].pct_change().iloc[self.current_step]
        done = self.current_step >= len(self.df) - 1
        obs = self.df.iloc[self.current_step].values if not done else np.zeros(6)
        return obs, reward, done, {}

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials))
channel = connection.channel()
channel.queue_declare(queue='training_results', durable=True)

@app.route('/train', methods=['POST'])
def train():
    config = request.get_json()
    if not config or 'bot_id' not in config:
        return jsonify({"error": "Missing bot_id"}), 400
    df = fetch_historical_data()
    if df.empty:
        logger.error("No historical data available for training")
        return jsonify({'error': 'No data'}), 500
    env = TradingEnv(df)
    model = PPO("MlpPolicy", env, verbose=0)
    model.learn(total_timesteps=10000)
    os.makedirs("/app/models", exist_ok=True)
    model_path = f"/app/models/model_{config['bot_id']}.zip"
    model.save(model_path)
    result = {
        'bot_id': config['bot_id'],
        'model_path': model_path,
        'status': 'trained'
    }
    channel.basic_publish(exchange='', routing_key='training_results', body=json.dumps(result), properties=pika.BasicProperties(delivery_mode=2))
    logger.info(f"Training completed for bot_id: {config['bot_id']}")
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