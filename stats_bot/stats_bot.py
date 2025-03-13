# stats_bot/stats_bot.py
import os
import json
import logging
import threading
from collections import deque
from flask import Flask, jsonify
import pika
from sqlalchemy import create_engine, Column, Integer, Float, DateTime, MetaData, Table
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
metadata = MetaData()

test_results_table = Table('test_results', metadata,
    Column('id', Integer, primary_key=True),
    Column('bot_id', Integer),
    Column('sharpe_ratio', Float),
    Column('win_rate', Float),
    Column('timestamp', DateTime),
    autoload_with=engine, extend_existing=True
)

metadata.create_all(engine)
aggregated_results = deque(maxlen=100)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS")
PORT = int(os.getenv("STATS_PORT", 5003))

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10))
def get_rabbitmq_connection():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    return pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials))

try:
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    channel.queue_declare(queue='test_results', durable=True)
except Exception as e:
    logger.error("Failed to connect to RabbitMQ: %s", e)
    raise

def callback(ch, method, properties, body):
    try:
        result = json.loads(body)
        aggregated_results.append(result)
        with engine.begin() as conn:
            conn.execute(test_results_table.insert().values(
                bot_id=result.get('bot_id'),
                sharpe_ratio=result.get('sharpe_ratio'),
                win_rate=result.get('win_rate'),
                timestamp=datetime.fromisoformat(result.get('timestamp'))
            ))
        logger.info("Persisted test result: %s", result)
    except Exception as e:
        logger.error("Error processing test result: %s", e, exc_info=True)

channel.basic_consume(queue='test_results', on_message_callback=callback, auto_ack=True)

def start_consuming():
    try:
        channel.start_consuming()
    except Exception as e:
        logger.error("Error in RabbitMQ consuming loop: %s", e, exc_info=True)

threading.Thread(target=start_consuming, daemon=True).start()

@app.route("/health")
def health():
    return jsonify({"status": "OK", "total_results": len(aggregated_results)}), 200

@app.route('/feedback', methods=['GET'])
def stats_feedback():
    stats = {
        'total_results': len(aggregated_results),
        'last_result': aggregated_results[-1] if aggregated_results else {},
        'aggregated_results': list(aggregated_results)
    }
    return jsonify({'status': 'ok', 'stats': stats}), 200

@app.route('/update_config', methods=['POST'])
def stats_update():
    try:
        new_config = request.get_json()
        logger.info("Received stats bot config update: %s", new_config)
        global aggregated_results
        aggregated_results = deque(aggregated_results, maxlen=new_config.get("max_results", 100))
        return jsonify({'status': 'stats config updated'}), 200
    except Exception as e:
        logger.error("Error updating stats config: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)