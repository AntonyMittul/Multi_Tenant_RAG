import os
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from google import genai
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from app.core.config import settings
import uuid

# Initialize Gemini Client
gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Initialize Qdrant Client
if settings.QDRANT_URL and settings.QDRANT_API_KEY:
    qdrant_client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
else:
    qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)

COLLECTION_NAME = "rag_documents"

def ensure_collection():
    """Ensure the Qdrant collection exists."""
    collections = qdrant_client.get_collections().collections
    if not any(c.name == COLLECTION_NAME for c in collections):
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
        )

def parse_document(file_path: str) -> str:
    """Extract text from PDF or TXT."""
    text = ""
    if file_path.endswith(".pdf"):
        reader = PdfReader(file_path)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    elif file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    return text

def chunk_text(text: str) -> list[str]:
    """Split text into manageable chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )
    return splitter.split_text(text)

def generate_embeddings(chunks: list[str]) -> list[list[float]]:
    """Generate embeddings using Gemini API."""
    # Using older reliable embedding model
    response = gemini_client.models.embed_content(
        model='models/gemini-embedding-001',
        contents=chunks,
    )
    # result.embeddings is a list of Embedding objects
    return [e.values for e in response.embeddings]

def store_in_qdrant(chunks: list[str], embeddings: list[list[float]], tenant_id: str, filename: str):
    """Store chunks and embeddings in Qdrant, filtered by tenant_id."""
    ensure_collection()
    
    points = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        point_id = str(uuid.uuid4())
        points.append(
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "tenant_id": tenant_id,
                    "filename": filename,
                    "text": chunk,
                    "chunk_index": i
                }
            )
        )
    
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )

