from typing import List, Dict, AsyncGenerator
import litellm
from litellm import completion, acompletion
from app.core.config import settings
from langfuse import observe
from langfuse import Langfuse
import logging

logger = logging.getLogger(__name__)

# Basic LiteLLM configuration for resilience
litellm.num_retries = 3               # Rate limiting/retries
litellm.cache = litellm.Cache(type="local") # Caching

# Initialize Langfuse
langfuse = Langfuse(
  secret_key=settings.LANGFUSE_SECRET_KEY,
  public_key=settings.LANGFUSE_PUBLIC_KEY,
  host=settings.LANGFUSE_HOST
)

SYSTEM_PROMPT = """
You are a highly capable AI assistant for a multi-tenant platform.
You will be provided with a user's query and a set of retrieved documents from their knowledge base.
Your task is to answer the query ONLY using the provided documents.
Provide a highly detailed, comprehensive, and well-structured explanation. 
Break down complex topics into clear, easy-to-understand points with proper headings and bullet points where appropriate.
If the answer is not contained in the documents, state clearly that you do not have enough information to answer.
Do not make up facts or use outside knowledge.

At the very end of your response, always provide exactly 3 suggested follow-up questions based on the documents. 
Format them exactly like this:
<FOLLOW_UP>
- Question 1
- Question 2
- Question 3
</FOLLOW_UP>
"""

@observe()
def construct_prompt(query: str, documents: List[Dict]) -> str:
    """Constructs the final prompt with context from retrieved documents."""
    context = ""
    for i, doc in enumerate(documents):
        filename = doc.get("filename", "Unknown Source")
        text = doc.get("text", "")
        context += f"--- Document [{i+1}] (Source: {filename}) ---\n{text}\n\n"
        
    prompt = f"Context Information:\n{context}\n\nUser Query: {query}\n\nAnswer:"
    return prompt

@observe(as_type="generation")
def generate_answer(query: str, documents: List[Dict], temperature: float = 0.2) -> str:
    """Generate a single string answer using LiteLLM (Gateway)."""
    prompt = construct_prompt(query, documents)
    
    # Define models for fallback routing
    model_list = [
        "gemini/gemini-3.1-flash-lite", # Primary
        "gemini/gemini-2.5-flash"       # Fallback
    ]
    
    response = litellm.completion(
        model=model_list[0],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        fallbacks=[model_list[1]],
        api_key=settings.GEMINI_API_KEY
    )
    return response.choices[0].message.content

@observe(as_type="generation")
async def generate_answer_stream(query: str, documents: List[Dict], temperature: float = 0.2) -> AsyncGenerator[str, None]:
    """Generate a streaming response using LiteLLM."""
    prompt = construct_prompt(query, documents)
    
    model_list = [
        "gemini/gemini-3.1-flash-lite",
        "gemini/gemini-2.5-flash"
    ]
    
    response = await litellm.acompletion(
        model=model_list[0],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        fallbacks=[model_list[1]],
        api_key=settings.GEMINI_API_KEY,
        stream=True,
        caching=False # Disable caching on stream for better TTFT latency
    )
    
    async for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta

