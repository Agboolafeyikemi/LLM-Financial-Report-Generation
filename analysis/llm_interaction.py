#### analysis/llm_interaction.py
####
#### This script is responsible for interacting with Language Models (LLMs).
#### Supports multiple providers: OpenAI, Anthropic, Ollama (local), or Demo mode.
#### It provides a function to query the LLM with a given prompt and retrieve its
#### response. The script constructs a specific prompt that instructs the LLM to
#### act as a data analyst assistant, providing factual analysis based solely on
#### the provided data and avoiding speculative statements.
####
#### Configure via environment variables:
####   LLM_PROVIDER=openai|anthropic|ollama|demo
####   For OpenAI: OPENAI_API_KEY=your_key
####   For Anthropic: ANTHROPIC_API_KEY=your_key


import requests
import logging
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def query_llm(prompt: str, model: str, temperature: float, max_tokens: int) -> str | None:
    """Queries LLM with data-focused prompting.
    
    Supports multiple providers:
    - OpenAI (cloud API)
    - Anthropic Claude (cloud API)
    - Ollama (local)
    - Demo mode (pre-generated responses)
    
    Provider is determined by LLM_PROVIDER environment variable.
    """
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    
    # Demo mode check (highest priority)
    if provider == "demo" or os.getenv("DEMO_MODE", "false").lower() == "true":
        return _get_demo_response(prompt)
    
    system_prompt = """You are a data analyst assistant. Your task is to analyze and describe 
    the provided data in a factual manner. Follow these rules:
    1. Only use information explicitly provided in the data
    2. Do not make assumptions beyond what's in the numbers
    3. Avoid speculative language like "might", "could", "possibly"
    4. State exact percentages and values from the data
    5. If no notable patterns exist, say so directly
    6. Use clear, concise business language"""

    # Route to appropriate provider
    if provider == "openai":
        return _query_openai(system_prompt, prompt, model, temperature, max_tokens)
    elif provider == "anthropic":
        return _query_anthropic(system_prompt, prompt, model, temperature, max_tokens)
    elif provider == "ollama":
        return _query_ollama(system_prompt, prompt, model, temperature, max_tokens)
    else:
        logging.warning(f"Unknown LLM_PROVIDER: {provider}. Falling back to demo mode.")
        return _get_demo_response(prompt)


def _query_openai(system_prompt: str, user_prompt: str, model: str, temperature: float, max_tokens: int) -> Optional[str]:
    """Query OpenAI API."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error("OPENAI_API_KEY not set. Set LLM_PROVIDER=demo or provide API key.")
        print("❌ OPENAI_API_KEY not found. Set it in environment or use LLM_PROVIDER=demo")
        return None
    
    try:
        # Map Ollama model names to OpenAI models if needed
        model_mapping = {
            "phi4:latest": "gpt-4o-mini",  # Fallback to smaller model
            "gemma3:12b": "gpt-4o-mini",
            "deepseek-r1:1.5b": "gpt-4o-mini"
        }
        openai_model = model_mapping.get(model, model if model.startswith("gpt") else "gpt-4o-mini")
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": openai_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error querying OpenAI: {e}")
        print(f"❌ OpenAI API error: {e}")
        return None
    except Exception as e:
        logging.error(f"Error querying OpenAI: {e}")
        print(f"❌ Error: {e}")
        return None


def _query_anthropic(system_prompt: str, user_prompt: str, model: str, temperature: float, max_tokens: int) -> Optional[str]:
    """Query Anthropic Claude API."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logging.error("ANTHROPIC_API_KEY not set. Set LLM_PROVIDER=demo or provide API key.")
        print("❌ ANTHROPIC_API_KEY not found. Set it in environment or use LLM_PROVIDER=demo")
        return None
    
    try:
        # Map Ollama model names to Anthropic models if needed
        model_mapping = {
            "phi4:latest": "claude-3-5-sonnet-20241022",
            "gemma3:12b": "claude-3-5-sonnet-20241022",
            "deepseek-r1:1.5b": "claude-3-haiku-20240307"  # Smaller/faster model
        }
        anthropic_model = model_mapping.get(model, model if model.startswith("claude") else "claude-3-5-sonnet-20241022")
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": anthropic_model,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"].strip()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error querying Anthropic: {e}")
        print(f"❌ Anthropic API error: {e}")
        return None
    except Exception as e:
        logging.error(f"Error querying Anthropic: {e}")
        print(f"❌ Error: {e}")
        return None


def _query_ollama(system_prompt: str, user_prompt: str, model: str, temperature: float, max_tokens: int) -> Optional[str]:
    """Query local Ollama API."""
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    
    try:
        timeout = int(os.getenv("OLLAMA_TIMEOUT", "300"))  # 5 minutes default for CPU
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": full_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            },
            timeout=timeout
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.Timeout:
        logging.warning("LLM request timed out. This is normal in CPU-only environments like Codespaces.")
        print("⚠️ LLM request timed out. Consider using LLM_PROVIDER=demo or cloud APIs for faster testing.")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error querying Ollama (Connection Error): {e}")
        print(f"❌ Ollama connection error: {e}")
        print("💡 Tip: Start Ollama with 'ollama serve' or use LLM_PROVIDER=openai/anthropic/demo")
        return None
    except Exception as e:
        logging.error(f"Error querying Ollama: {e}")
        print(f"❌ Error: {e}")
        return None


def _get_demo_response(prompt: str) -> str:
    """Returns a demo response for testing without Ollama."""
    # Simple keyword-based demo responses
    prompt_lower = prompt.lower()
    
    if "annual revenue" in prompt_lower or "year-over-year" in prompt_lower:
        return """**Annual Revenue Analysis**

The data shows clear revenue trends across the reporting period. Key observations:

- Revenue growth patterns indicate consistent performance
- Property-level analysis reveals varying contribution levels
- Year-over-year changes demonstrate the overall business trajectory

**Key Metrics:**
- Total revenue shows steady growth trajectory
- Top properties contribute significantly to overall performance
- Revenue distribution across properties is well-balanced"""
    
    elif "tenant" in prompt_lower or "distribution" in prompt_lower:
        return """**Tenant Performance Analysis**

The tenant distribution analysis reveals important insights:

- Top tenants show strong revenue contribution
- Property-level tenant mix demonstrates balanced portfolio
- Concentration risk appears manageable with diversified tenant base

**Key Findings:**
- Top 3 tenants represent significant portion of property revenue
- Tenant distribution supports stable revenue streams
- Performance varies appropriately across properties"""
    
    elif "change" in prompt_lower or "revenue change" in prompt_lower:
        return """**Revenue Change Analysis**

Significant revenue changes have been identified:

- Several tenants show notable growth contributions
- Some tenants experienced revenue decreases
- Net impact analysis shows overall positive trajectory

**Key Changes:**
- Largest gains come from top-performing tenants
- Losses are offset by strong performers
- Overall net change supports continued growth"""
    
    else:
        return """**Data Analysis Summary**

Based on the provided financial data:

- The dataset shows consistent patterns and trends
- Key metrics indicate stable performance
- Analysis reveals actionable insights for decision-making

**Recommendations:**
- Continue monitoring key performance indicators
- Focus on high-performing segments
- Address areas showing decline"""