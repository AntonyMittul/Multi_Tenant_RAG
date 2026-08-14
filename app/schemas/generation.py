from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class GenerateRequest(BaseModel):
    query: str
    filename: Optional[str] = None
    top_k: int = 5
    temperature: float = 0.2
    stream: bool = False

class SourceDocument(BaseModel):
    id: str
    filename: str
    text: str
    score: Optional[float] = None
    rerank_score: Optional[float] = None

class GenerateResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]
    cached: bool = False

