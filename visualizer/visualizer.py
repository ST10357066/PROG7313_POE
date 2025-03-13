# visualizer\visualizer.py
import os
import logging
import requests
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

STATS_URL = f"http://stats_bot:{os.getenv('STATS_PORT', 5003)}/feedback"
DEPLOYMENT_URL = f"http://packaging_deployment:{os.getenv('DEPLOYMENT_PORT', 5004)}/deploy_bot"
PORT = int(os.getenv("VISUALIZER_PORT", 5005))

@app.route("/health")
def health():
    return jsonify({"status": "OK"}), 200

@app.route("/dashboard")
def dashboard():
    try:
        response = requests.get(STATS_URL, timeout=5)
        stats = response.json().get("stats", {}) if response.status_code == 200 else {}
    except Exception as e:
        logger.error("Error fetching stats: %s", e)
        stats = {}
        flash("Error fetching stats.", "error")
    return render_template("dashboard.html", stats=stats)

@app.route("/deploy_live", methods=["POST"])
def deploy_live():
    bot_id = request.form.get("bot_id")
    risk = request.form.get("risk", "medium")
    live_mode = request.form.get("live_mode", "false").lower() == "true"
    bot_config = {
        "bot_id": int(bot_id) if bot_id else None,
        "risk": risk,
        "strategy": "mean_reversion",
        "parameters": {"entry_threshold": 2.0, "exit_threshold": 1.0, "stop_loss": 0.03, "position_size": 0.2},
        "live_mode": live_mode
    }
    try:
        response = requests.post(DEPLOYMENT_URL, json=bot_config, timeout=5)
        if response.status_code == 200:
            flash("Live deployment initiated successfully.", "success")
        else:
            flash(f"Live deployment failed with status code: {response.status_code}", "error")
    except Exception as e:
        logger.error("Error initiating live deployment: %s", e)
        flash("Error initiating live deployment.", "error")
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)