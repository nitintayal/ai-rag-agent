from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from typing import Optional
from configs.config import settings
from .agent_state import AgentState
from .router import gemini_structured_router, keyword_fallback_router

MODEL_NAME = settings.LLM_MODEL

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="cpu",          # 🔴 FORCE CPU
    dtype=torch.float32  # 🔴 CPU-safe dtype
)

def llm_generate(prompt: str, max_new_tokens: Optional[int] = 300, temperature: Optional[float] = 0.2) -> str:
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    generation_kwargs = {
        **inputs,
        "max_new_tokens": max_new_tokens,
    }

    if temperature is None or temperature <= 0:
        generation_kwargs["do_sample"] = False
    else:
        generation_kwargs["do_sample"] = True
        generation_kwargs["temperature"] = temperature

    with torch.no_grad():
        output = model.generate(**generation_kwargs)
    # Extract only the newly generated tokens
    input_length = inputs["input_ids"].shape[1]
    generated_tokens = output[0][input_length:]
    return tokenizer.decode(generated_tokens, skip_special_tokens=True)

def answer_with_llm(question: str, context: str) -> str:
    print("Generating answer with LLM with Context:", context)
    prompt = f"""
Role: You are a helpful assistant that answers questions based only on the provided context. If the answer is not in the context, say 'I don't know'.
Output Format: Just provide the answer without any additional text or formatting.
Context:{context}

Question:{question}

Answer:
"""

    return llm_generate(prompt)

def local_prompt_router(question: str) -> str:
    prompt = f"""
    Answer which tool to use, output a single tool name without any explanation. Choose between "web" and "rag" based on the question.:

    Tools:
    - web: only when question contains keywords like "current", "latest", "news", "trending", "today", "recent", "update", "weather", "sports scores", "stock price", "COVID cases", etc.
    - rag: for all other questions

    Query: {question}

    Output have to a single word and MUST BE EITHER "rag" or "web". Do not provide any explanation, just the tool name.

    Output Example: "web". Format MUST be exactly as in the example, without any additional text, quotes, or formatting.
    """

    tool = llm_generate(prompt, max_new_tokens=4, temperature=0)
    normalized = tool.strip().lower()
    return normalized if normalized in {"web", "rag"} else keyword_fallback_router(question)


def decide_llm_tool(state: AgentState) -> dict:
    question = state["question"]

    provider = settings.ROUTER_PROVIDER.strip().lower()

    if provider == "gemini":
        try:
            tool = gemini_structured_router(question)
        except Exception as exc:
            print(f"Structured router failed, falling back to local router: {exc}")
            tool = local_prompt_router(question)
    else:
        tool = local_prompt_router(question)

    print(f"LLM decided to use tool: {tool}")
    return {"tool": tool}
