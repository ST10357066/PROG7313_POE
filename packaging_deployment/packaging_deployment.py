# packaging_deployment/packaging_deployment.py
import os
import json
import logging
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
PORT = int(os.getenv("DEPLOYMENT_PORT", 5004))
STATS_URL = f"http://stats_bot:{os.getenv('STATS_PORT', 5003)}/feedback"

@app.route('/deploy_bot', methods=['POST'])
def deploy_bot():
    config = request.get_json()
    response = requests.get(STATS_URL)
    stats = response.json().get('stats', {}).get('aggregated_results', [])
    bot_results = [r for r in stats if r['bot_id'] == config['bot_id']]
    if bot_results:
        bot_stats = max(bot_results, key=lambda x: x['timestamp'])
        errors = []
        if bot_stats['sharpe_ratio'] <= 0.7:
            errors.append('Sharpe ratio below 0.7')
        if bot_stats['win_rate'] <= 70:
            errors.append('Win rate below 70%')
        if errors:
            return jsonify({'error': 'Performance below threshold', 'details': errors}), 403
        return jsonify({'status': 'deployed', 'bot_id': config['bot_id']}), 200
    else:
        return jsonify({'error': 'No stats found for bot_id'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)