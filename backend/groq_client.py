import os
import json
from typing import AsyncGenerator, List, Dict, Any
from groq import AsyncGroq

# Using the AsyncGroq client
# The GROQ_API_KEY environment variable should be set
client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))

async def call_groq_streaming(messages: List[Dict[str, Any]], model: str = "llama-3.3-70b-versatile") -> AsyncGenerator[str, None]:
    """
    Calls Groq API and yields tokens one by one asynchronously.
    """
    try:
        response = await client.chat.completions.create(
            messages=messages,
            model=model,
            stream=True,
            temperature=0.0,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as e:
        yield f" Error calling Groq API: {str(e)}"

async def call_groq(messages: List[Dict[str, Any]], model: str = "llama-3.3-70b-versatile", response_format: str = "text") -> str:
    """
    Calls Groq API non-streaming.
    """
    try:
        kwargs: Dict[str, Any] = {
            "messages": messages,
            "model": model,
            "stream": False,
            "temperature": 0.0,
        }
        if response_format == "json_object":
            kwargs["response_format"] = {"type": "json_object"}
            
        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        if response_format == "json_object":
            return "{}"
        return ""
