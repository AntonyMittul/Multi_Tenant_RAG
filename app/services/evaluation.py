from google import genai
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

# Reusing the gemini client
gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

def evaluate_faithfulness(question: str, context: str, answer: str) -> float:
    """
    Evaluates whether the generated answer is faithful to the provided context.
    Returns a score from 0.0 to 1.0.
    """
    prompt = f"""
    You are an impartial judge. Your task is to determine if the given Answer is completely supported by the provided Context.
    
    Question: {question}
    Context: {context}
    Answer: {answer}
    
    Does the Answer hallucinate any details not present in the Context?
    Respond with ONLY a JSON object containing a "score" (0.0 for unfaithful/hallucinated, 1.0 for faithful) and a "reason" (a short string).
    """
    
    response = gemini_client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
        )
    )
    
    try:
        result = json.loads(response.text)
        return float(result.get("score", 0.0))
    except Exception as e:
        logger.error(f"Failed to parse evaluation response: {str(e)}")
        return 0.0

def evaluate_answer_relevance(question: str, answer: str) -> float:
    """
    Evaluates whether the generated answer directly addresses the user's question.
    Returns a score from 0.0 to 1.0.
    """
    prompt = f"""
    You are an impartial judge. Your task is to determine if the given Answer directly and adequately addresses the Question.
    
    Question: {question}
    Answer: {answer}
    
    Does the Answer answer the Question?
    Respond with ONLY a JSON object containing a "score" (0.0 to 1.0, where 1.0 is a perfect direct answer) and a "reason" (a short string).
    """
    
    response = gemini_client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
        )
    )
    
    try:
        result = json.loads(response.text)
        return float(result.get("score", 0.0))
    except Exception as e:
        logger.error(f"Failed to parse evaluation response: {str(e)}")
        return 0.0

