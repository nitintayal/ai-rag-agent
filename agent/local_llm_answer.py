from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

MODEL_NAME = "Qwen/Qwen2-1.5B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="cpu",          # 🔴 FORCE CPU
    dtype=torch.float32  # 🔴 CPU-safe dtype
)

def answer_with_llm(question: str, context: str) -> str:
    prompt = f"""
You are a helpful assistant. OUTPUT ONLY THE ANSWER without any additional text.
Answer the question briefly in a single liner using only the context provided below without any additional justification and output only the answer.
If answer not found or valid because it is not in the given context, return answer "Not found in the Knowledge Base." .
Context:{context}

Question:{question}

Answer:
"""

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=300,
            temperature=0.2
        )

    return tokenizer.decode(output[0], skip_special_tokens=True)
