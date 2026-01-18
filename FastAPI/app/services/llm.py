import httpx
from app.config import get_settings

settings = get_settings()

OLLAMA_BASE_URL = "http://localhost:11434"  # Default Ollama URL

async def generate_response(prompt: str, model: str = "gemma3:1b") -> str:
    """
    Generate a response from the LLM using Ollama.
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
    except Exception as e:
        print(f"Error calling LLM: {str(e)}")
        # Fallback or re-raise
        return "I apologize, but I encountered an error processing your request."
