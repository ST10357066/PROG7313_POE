# orchestrator\convert.py
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

def convert_model_to_onnx(model_name="distilgpt2", output_path="orchestrator_model.onnx"):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    model.eval()
    dummy_input = tokenizer.encode("Test input for ONNX conversion", return_tensors="pt")
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}}
    )
    print(f"Model converted and saved to {output_path}")

if __name__ == "__main__":
    convert_model_to_onnx()