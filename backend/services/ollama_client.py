import os
from typing import List, Optional

import httpx

from config import settings


class OllamaClient:
    """Client for Ollama local LLM inference."""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT_SECONDS

    async def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text using Ollama."""
        if not settings.OLLAMA_ENABLED:
            return ""

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                }
                
                if system_prompt:
                    payload["system"] = system_prompt

                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                return response.json().get("response", "")
        except Exception as e:
            print(f"Ollama generation error: {e}")
            return ""

    async def embed(self, text: str) -> Optional[List[float]]:
        """Generate embeddings using Ollama."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                response.raise_for_status()
                return response.json().get("embedding")
        except Exception as e:
            print(f"Ollama embedding error: {e}")
            return None

    def list_models(self) -> List[str]:
        """List available models in Ollama."""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m["name"] for m in models]
        except Exception:
            pass
        return []


# Global client instance
ollama_client = OllamaClient()
