# orchestrator\kernel.py
import time
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ORCHESTRATOR_PORT = os.getenv("ORCHESTRATOR_PORT", 5007)

def run_kernel(improve_endpoint=f"http://localhost:{ORCHESTRATOR_PORT}/improve", interval=60):
    while True:
        logger.info("Kernel: Collecting feedback from subservices...")
        feedback = {
            "service": "trainer_bot",
            "feedback": "Training loss plateauing."
        }
        try:
            response = requests.post(improve_endpoint, json=feedback, timeout=5)
            if response.status_code == 200:
                improvements = response.json().get("improvements", "")
                logger.info("Kernel: Received improvements: %s", improvements)
            else:
                logger.warning("Kernel: Non-200 status code %s", response.status_code)
        except Exception as e:
            logger.error("Kernel: Error contacting orchestrator: %s", e)
        time.sleep(interval)

if __name__ == "__main__":
    run_kernel()