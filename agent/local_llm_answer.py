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
    print("Generating answer with LLM with Context:", context)
    prompt = f"""
You are a helpful assistant. OUTPUT ONLY THE ANSWER without any additional text.
Answer the question briefly in a single liner using only the context provided below without any additional justification and output only the answer.
Answer ONLY in the given context.
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
    # Extract only the newly generated tokens
    input_length = inputs["input_ids"].shape[1]
    generated_tokens = output[0][input_length:]
    return tokenizer.decode(generated_tokens, skip_special_tokens=True)
