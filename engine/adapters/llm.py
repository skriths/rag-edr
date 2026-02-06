"""
Ollama/Mistral adapter for RAG generation.

Simple wrapper for LLM calls with context.
"""
import httpx
from typing import List, Dict, Any, Optional
import config


class LLMAdapter:
    """
    Wrapper for Ollama API.

    Handles RAG generation with retrieved context.
    """

    def __init__(self, base_url: str = config.OLLAMA_BASE_URL, model: str = config.OLLAMA_MODEL):
        self.base_url = base_url
        self.model = model

    async def generate(
        self,
        query: str,
        context_docs: List[Dict[str, Any]],
        fallback_message: Optional[str] = None
    ) -> str:
        """
        Generate answer using RAG context.

        Args:
            query: User query
            context_docs: Retrieved documents (list of dicts with 'content' key, or list of strings)
            fallback_message: If no clean docs available, return this

        Returns:
            Generated answer or fallback message
        """
        if not context_docs:
            return fallback_message or "No information available to answer this query."

        # Build context prompt - handle both dict format and string format
        context_parts = []
        for i, doc in enumerate(context_docs):
            if isinstance(doc, dict):
                content = doc.get('content', str(doc))
            else:
                content = str(doc)
            context_parts.append(f"Document {i+1}:\n{content}")

        context = "\n\n".join(context_parts)

        prompt = f"""You are a security analyst assistant. Answer the following question using ONLY the provided context documents. Be concise and accurate.

Context:
{context}

Question: {query}

Answer:"""

        # Call Ollama API
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "").strip()
        except httpx.HTTPError as e:
            return f"Error generating response: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    async def check_ollama_status(self) -> bool:
        """
        Check if Ollama service is running and model is available.

        Returns:
            True if Ollama is accessible
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                tags = response.json()

                # Check if our model is available
                models = [m["name"] for m in tags.get("models", [])]
                return any(self.model in m for m in models)
        except Exception:
            return False


# Global instance
llm = LLMAdapter()
