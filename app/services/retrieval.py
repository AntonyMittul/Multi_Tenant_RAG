from typing import List, Dict
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from app.services.ingestion import qdrant_client, gemini_client, COLLECTION_NAME
from rank_bm25 import BM25Okapi
import logging

logger = logging.getLogger(__name__)

def get_tenant_filter(tenant_id: str, filename: str = None) -> Filter:
    """Helper to create a strict tenant filter for Qdrant."""
    must_conditions = [
        FieldCondition(
            key="tenant_id",
            match=MatchValue(value=tenant_id)
        )
    ]
    if filename:
        must_conditions.append(
            FieldCondition(
                key="filename",
                match=MatchValue(value=filename)
            )
        )
    return Filter(must=must_conditions)

def dense_retrieval(query: str, tenant_id: str, top_k: int = 10, filename: str = None) -> List[Dict]:
    """
    Perform semantic vector search using Gemini embeddings.
    Strictly filters by tenant_id (and optionally filename).
    """
    logger.info(f"Performing dense retrieval for tenant {tenant_id}")
    # 1. Generate query embedding using the older reliable model
    result = gemini_client.models.embed_content(
        model='models/gemini-embedding-001',
        contents=query,
    )
    query_vector = result.embeddings[0].values

    # 2. Search Qdrant
    from qdrant_client.http.exceptions import UnexpectedResponse
    try:
        search_response = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=get_tenant_filter(tenant_id, filename),
            limit=top_k,
            with_payload=True
        )
        search_result = search_response.points
    except UnexpectedResponse as e:
        if e.status_code == 404:
            logger.warning(f"Collection {COLLECTION_NAME} not found. Returning empty dense retrieval.")
            return []
        raise e
    
    # 3. Format results
    return [
        {
            "id": hit.id,
            "text": hit.payload.get("text", ""),
            "score": hit.score,
            "filename": hit.payload.get("filename", "")
        }
        for hit in search_result
    ]

def sparse_retrieval(query: str, tenant_id: str, top_k: int = 10, filename: str = None) -> List[Dict]:
    """
    Perform keyword search using BM25.
    For this implementation, we fetch all tenant docs from Qdrant and run BM25 in-memory.
    (In a massive scale system, you would use Qdrant's native sparse vectors or Elasticsearch).
    """
    logger.info(f"Performing sparse (BM25) retrieval for tenant {tenant_id}")
    
    # Fetch all chunks for the tenant (with pagination in a real app, here we limit to 1000 for simplicity)
    from qdrant_client.http.exceptions import UnexpectedResponse
    try:
        scroll_result = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=get_tenant_filter(tenant_id, filename),
            limit=1000,
            with_payload=True,
            with_vectors=False
        )[0]
    except UnexpectedResponse as e:
        if e.status_code == 404:
            logger.warning(f"Collection {COLLECTION_NAME} not found. Returning empty sparse retrieval.")
            return []
        raise e
    
    if not scroll_result:
        return []
        
    docs = [{"id": hit.id, "text": hit.payload.get("text", ""), "filename": hit.payload.get("filename", "")} for hit in scroll_result]
    corpus = [doc["text"] for doc in docs]
    
    # Tokenize corpus and query
    tokenized_corpus = [doc.split(" ") for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = query.split(" ")
    
    # Get scores
    doc_scores = bm25.get_scores(tokenized_query)
    
    # Sort by score
    sorted_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)[:top_k]
    
    results = []
    for idx in sorted_indices:
        if doc_scores[idx] > 0: # Only return matches
            doc = docs[idx]
            doc["score"] = doc_scores[idx]
            results.append(doc)
            
    return results

def reciprocal_rank_fusion(dense_results: List[Dict], sparse_results: List[Dict], k: int = 60) -> List[Dict]:
    """
    Combine Dense and Sparse results using RRF (Reciprocal Rank Fusion).
    Score = 1 / (k + rank)
    """
    rrf_scores = {}
    doc_map = {}
    
    # Process Dense
    for rank, doc in enumerate(dense_results):
        doc_id = doc["id"]
        doc_map[doc_id] = doc
        rrf_scores[doc_id] = 1.0 / (k + rank + 1)
        
    # Process Sparse
    for rank, doc in enumerate(sparse_results):
        doc_id = doc["id"]
        if doc_id not in doc_map:
            doc_map[doc_id] = doc
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))
        
    # Sort by RRF score
    sorted_docs = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
    return [doc_map[doc_id] for doc_id in sorted_docs]

def hybrid_search(query: str, tenant_id: str, top_k: int = 5, filename: str = None) -> List[Dict]:
    """
    Main retrieval pipeline:
    1. Dense Search (top 10)
    2. Sparse Search (top 10)
    3. RRF Combination
    """
    dense_hits = dense_retrieval(query, tenant_id, top_k=10, filename=filename)
    sparse_hits = sparse_retrieval(query, tenant_id, top_k=10, filename=filename)
    
    combined_hits = reciprocal_rank_fusion(dense_hits, sparse_hits)
    
    # Return top K from the combined hits
    return combined_hits[:top_k]


