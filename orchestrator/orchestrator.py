# orchestrator/orchestrator.py (updated excerpt)
import os
import logging
from flask import Flask, request, jsonify
from model import ImprovementModel
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

try:
    orchestrator_model = ImprovementModel(model_name="distilgpt2", max_length=100)
    logger.info("Loaded orchestrator model.")
except Exception as e:
    logger.error("Failed to load orchestrator model: %s", e)
    orchestrator_model = None

PORT = int(os.getenv("ORCHESTRATOR_PORT", 5007))
BUILDER_URL = f"http://builder_bot:{os.getenv('BUILDER_PORT', 5001)}/update_config"
TRAINER_URL = f"http://trainer_bot:{os.getenv('TRAINER_PORT', 5006)}/update_config"
TESTER_URL = f"http://tester_bot:{os.getenv('TESTER_PORT', 5002)}/update_config"

@app.route("/health")
def health():
    return jsonify({"status": "OK"}), 200

@app.route("/improve", methods=["POST"])
def improve():
    try:
        data = request.get_json()
        service = data.get("service", "unknown")
        feedback = data.get("feedback", "No feedback provided.")
        prompt = (f"Service: {service}\nFeedback: {feedback}\n"
                  f"|CoT| Analyze feedback and propose improvements. |EndCoT|\nFinal Improvement Suggestions:")
        improvements = orchestrator_model.suggest_improvements(service, prompt) if orchestrator_model else "Model unavailable."
        
        if service == "builder_bot":
            requests.post(BUILDER_URL, json={"improvements": improvements}, timeout=5)
        elif service == "trainer_bot":
            requests.post(TRAINER_URL, json={"improvements": improvements}, timeout=5)
        elif service == "tester_bot":
            requests.post(TESTER_URL, json={"improvements": improvements}, timeout=5)
        
        return jsonify({"service": service, "improvements": improvements}), 200
    except Exception as e:
        logger.error("Error in /improve endpoint: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)