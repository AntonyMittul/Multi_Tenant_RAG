import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)

class GuardrailManager:
    """
    Handles input validation and output verification for the RAG pipeline.
    """
    
    @staticmethod
    def verify_input(query: str) -> Tuple[bool, str]:
        """
        Validates the user's input query before sending it to the LLM.
        Returns (is_valid, reason).
        """
        if not query or not query.strip():
            return False, "Query cannot be empty."

        # 1. Length check
        if len(query) > 3000:
            logger.warning(f"Input rejected: Query too long ({len(query)} chars)")
            return False, "Query is too long. Please summarize your request."
            
        # 2. Simple Heuristics for Prompt Injection / Jailbreaks
        # In production, this can be swapped with a model-based guardrail (e.g., NeMo or LiteLLM Guardrails).
        suspicious_patterns = [
            r"ignore previous instructions",
            r"ignore all previous",
            r"system prompt",
            r"forget all previous",
            r"you are now",
            r"bypass",
            r"override",
            r"do not follow"
        ]
        
        query_lower = query.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, query_lower):
                logger.warning(f"Input rejected: Suspicious pattern detected '{pattern}'")
                return False, "Query blocked due to security policies (potential prompt injection)."
                
        return True, ""

    @staticmethod
    def verify_output(answer: str) -> Tuple[bool, str]:
        """
        Validates the generated output from the LLM before sending to user.
        Returns (is_valid, reason).
        """
        # Check for blocked terms or data leaks
        blocked_terms = [
            "internal confidential",
            "classified information"
        ]
        
        answer_lower = answer.lower()
        for term in blocked_terms:
            if term in answer_lower:
                logger.warning(f"Output rejected: Blocked term detected '{term}'")
                return False, "The generated response was blocked due to safety guidelines."
                
        return True, ""

