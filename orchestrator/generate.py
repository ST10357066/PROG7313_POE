# orchestrator\generate.py
import sys
import logging
from model import ImprovementModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_text(prompt, model_name="distilgpt2", max_length=100):
    model = ImprovementModel(model_name=model_name, max_length=max_length)
    outputs = model.generator(prompt, num_return_sequences=1)
    generated_text = outputs[0]['generated_text']
    suggestion = generated_text.split("|EndCoT|")[-1].strip() if "|EndCoT|" in generated_text else generated_text
    return suggestion

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate.py '<prompt>'")
        sys.exit(1)
    prompt = sys.argv[1]
    result = generate_text(prompt)
    logger.info("Generated suggestion: %s", result)
    print(result)