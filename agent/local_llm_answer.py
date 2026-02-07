from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

MODEL_NAME = "Qwen/Qwen2-1.5B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="cpu",          # 🔴 FORCE CPU
    torch_dtype=torch.float32  # 🔴 CPU-safe dtype
)

def answer_with_llm(question: str, context: str) -> str:
    prompt = f"""
You are a helpful assistant.
Answer the question briefly in a single liner using the context below without any additional justification.
If the question can be answered, answer it. Else if the question cannot be answered because it is not in the context, say "Not found in the Knowledge Base."

Context:
{context}

Question:
{question}

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
