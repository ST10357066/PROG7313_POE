# orchestrator\model.py
import logging
from transformers import pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImprovementModel:
    """Model for generating improvement suggestions using a transformer."""
    def __init__(self, model_name="distilgpt2", max_length=100):
        self.generator = pipeline("text-generation", model=model_name, max_length=max_length)
        logger.info("ImprovementModel: Loaded model %s with max_length=%d", model_name, max_length)

    def suggest_improvements(self, service, prompt):
        """Generate improvement suggestions based on a prompt."""
        suggestions = self.generate_text(prompt, num_return_sequences=1)
        generated_text = suggestions[0]['generated_text']
        return generated_text.split("|EndCoT|")[-1].strip() if "|EndCoT|" in generated_text else generated_text

    def generate_text(self, prompt, num_return_sequences=1):
        """Generate text using the transformer pipeline."""
        return self.generator(prompt, num_return_sequences=num_return_sequences)