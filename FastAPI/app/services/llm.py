import httpx
import google.generativeai as genai
from app.config import get_settings

settings = get_settings()

OLLAMA_BASE_URL = "http://localhost:11434"  # Default Ollama URL
GENERATION_MODEL = settings.OLLAMA_GENERATION_MODEL

async def generate_response(prompt: str, model: str = GENERATION_MODEL) -> str:
    """
    Generate a response from the LLM using Ollama.
    """
    try:
        # Timeout lebih lama untuk model yang lebih besar (5 menit)
        timeout = httpx.Timeout(300.0, connect=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            print(f"🔄 Calling Ollama with model: {model}")
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
            print(f"✅ LLM response received successfully")
            return data.get("response", "")
    except httpx.TimeoutException as e:
        print(f"⏱️ Timeout error calling LLM ({model}): {str(e)}")
        return "Maaf, request timeout. Model mungkin membutuhkan waktu lebih lama untuk memproses."
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP error calling LLM ({model}): {e.response.status_code} - {e.response.text}")
        return f"I apologize, but I encountered an HTTP error: {e.response.status_code}"
    except Exception as e:
        print(f"❌ Error calling LLM ({model}): {type(e).__name__} - {str(e)}")
        # Fallback or re-raise
        return "I apologize, but I encountered an error processing your request."


async def generate_response_test(prompt: str) -> str:
    """
    Generate a response from the LLM using Google Gemini.
    """
    api_key = settings.GOOGLE_API_KEY or settings.GEMINI_API_KEY
    if not api_key:
        return "Error: Google/Gemini API key not configured."

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(settings.GOOGLE_GENERATION_MODEL)
        
        response = await model.generate_content_async(prompt)
        
        return response.text
    except Exception as e:
        print(f"Error calling Google LLM: {str(e)}")
        return f"I apologize, but I encountered an error with Google Gemini: {str(e)}"

