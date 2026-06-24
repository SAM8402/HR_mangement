from __future__ import annotations

import os

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings

_embedding_model: GoogleGenerativeAIEmbeddings | None = None
_embedding_key: str | None = None
_vector_store: Chroma | None = None


def _build_embedding_model(api_key: str) -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=api_key,
    )


def get_embedding_model() -> GoogleGenerativeAIEmbeddings:
    global _embedding_model, _embedding_key
    if _embedding_model is None:
        _embedding_key = settings.GOOGLE_API_KEY
        _embedding_model = _build_embedding_model(_embedding_key)
    return _embedding_model


def _rotate_embedding_key() -> bool:
    global _embedding_model, _embedding_key
    keys = settings.api_keys
    if not keys or len(keys) < 2:
        return False
    idx = (keys.index(_embedding_key) + 1) % len(keys) if _embedding_key in keys else 0
    _embedding_key = keys[idx]
    _embedding_model = _build_embedding_model(_embedding_key)
    return True


def get_vector_store() -> Chroma:
    global _vector_store
    if _vector_store is None:
        _vector_store = Chroma(
            collection_name="hr_knowledge",
            embedding_function=get_embedding_model(),
            persist_directory=settings.CHROMA_PERSIST_DIR,
            collection_metadata={"hnsw:space": "cosine"},
        )
    return _vector_store


def delete_embeddings(doc_id: str) -> None:
    """Delete embeddings for a document from the vector store."""
    try:
        vector_store = get_vector_store()
        vector_store.delete(where={"id": str(doc_id)})
    except Exception:
        pass


async def embed_document(text: str, metadata: dict) -> None:
    """Add a document to the vector store after chunking."""
    from app.services.doc_processor import chunk_text
    from app.services.cache_service import cache_service

    chunks = chunk_text(text)
    if not chunks:
        return

    doc_id = metadata.get("id")
    if doc_id:
        delete_embeddings(doc_id)

    keys = settings.api_keys or [settings.GOOGLE_API_KEY]
    for attempt in range(len(keys)):
        try:
            vector_store = get_vector_store()
            vector_store.add_texts(
                texts=chunks,
                metadatas=[metadata.copy() for _ in chunks],
            )
            break
        except Exception:
            if attempt < len(keys) - 1:
                _rotate_embedding_key()
            else:
                raise
    try:
        await cache_service.invalidate_rag_cache()
    except Exception:
        pass



async def search_similar(query: str, k: int = 5) -> list[dict]:
    """Search the vector store for similar documents."""
    vector_store = get_vector_store()
    results = vector_store.similarity_search_with_relevance_scores(query, k=k)
    return [
        {
            "content": doc.page_content,
            "metadata": doc.metadata,
            "score": score,
        }
        for doc, score in results
    ]


async def hybrid_search(query: str, k: int = 5) -> list[dict]:
    """Perform hybrid search combining ChromaDB vector search + BM25 keyword search."""
    import json
    from rank_bm25 import BM25Okapi
    from sqlalchemy import select
    from app.db.session import async_session
    from app.models.company_rule import CompanyRule
    from app.models.company_role import CompanyRole

    # 1. Vector Search (retrieve top 15)
    vector_results = await search_similar(query, k=15)

    # 2. Fetch all rules & roles from DB for BM25 indexing
    db_docs = []
    try:
        async with async_session() as db:
            rules_res = await db.execute(select(CompanyRule).where(CompanyRule.is_active == True))
            for r in rules_res.scalars().all():
                db_docs.append({
                    "content": f"Company Rule - {r.category}: {r.title}\n{r.content}",
                    "metadata": {
                        "type": "company_rule",
                        "title": r.title,
                        "category": r.category,
                        "id": str(r.id),
                    }
                })

            roles_res = await db.execute(select(CompanyRole))
            for r in roles_res.scalars().all():
                db_docs.append({
                    "content": (
                        f"Role: {r.title}\n"
                        f"Description: {r.description}\n"
                        f"Responsibilities: {r.responsibilities}\n"
                        f"Skills: {', '.join(r.required_skills) if r.required_skills else ''}"
                    ),
                    "metadata": {
                        "type": "company_role",
                        "title": r.title,
                        "id": str(r.id),
                    }
                })
    except Exception:
        pass

    # Filter vector results to keep only active DB rules/roles and apply threshold
    active_ids = {doc["metadata"]["id"] for doc in db_docs}
    filtered_vector_results = []
    for vr in vector_results:
        v_id = vr["metadata"].get("id")
        if v_id and v_id not in active_ids:
            continue
        # Apply similarity threshold check (AURA's threshold is 0.35)
        if vr.get("score", 0.0) < 0.35:
            continue
        filtered_vector_results.append(vr)

    if not db_docs:
        return filtered_vector_results[:k]

    # Tokenize corpus for BM25
    corpus = [doc["content"] for doc in db_docs]
    tokenized_corpus = [doc.lower().split(" ") for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)

    tokenized_query = query.lower().split(" ")
    bm25_scores = bm25.get_scores(tokenized_query)

    max_bm25 = max(bm25_scores) if len(bm25_scores) > 0 else 0

    # Create a map of content to score for BM25
    bm25_results = []
    for idx, score in enumerate(bm25_scores):
        if score > 0:
            norm_score = score / max_bm25 if max_bm25 > 0 else 0
            bm25_results.append({
                "content": db_docs[idx]["content"],
                "metadata": db_docs[idx]["metadata"],
                "score": norm_score,
            })

    # Combine results (0.7 Vector, 0.3 BM25)
    combined = {}
    for vr in filtered_vector_results:
        content = vr["content"]
        combined[content] = {
            "content": content,
            "metadata": vr["metadata"],
            "vector_score": vr["score"],
            "bm25_score": 0.0,
            "score": 0.7 * vr["score"],
        }

    for br in bm25_results:
        content = br["content"]
        if content in combined:
            combined[content]["bm25_score"] = br["score"]
            combined[content]["score"] = 0.7 * combined[content]["vector_score"] + 0.3 * br["score"]
        else:
            combined[content] = {
                "content": content,
                "metadata": br["metadata"],
                "vector_score": 0.0,
                "bm25_score": br["score"],
                "score": 0.3 * br["score"],
            }

    sorted_combined = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
    return [
        {
            "content": sc["content"],
            "metadata": sc["metadata"],
            "score": sc["score"],
        }
        for sc in sorted_combined[:k]
    ]


async def rerank_documents_with_llm(query: str, docs: list[dict], top_n: int = 5) -> list[dict]:
    """Use Gemini to rerank retrieved documents based on relevance."""
    import json
    from langchain_core.messages import SystemMessage, HumanMessage
    from app.ai.agent import get_llm

    if not docs:
        return []
    if len(docs) <= top_n:
        return docs

    llm = await get_llm(temperature=0.0)
    
    doc_format = []
    for idx, doc in enumerate(docs):
        doc_format.append(f"Document [{idx}]:\n{doc['content']}\n---")
    
    prompt = (
        "You are an expert search engine reranker. "
        "Determine the relevance of each document to the user query.\n\n"
        f"Query: {query}\n\n"
        "Documents:\n" + "\n".join(doc_format) + "\n\n"
        f"Select the top {top_n} most relevant document indices. "
        "Respond ONLY with a JSON list of integers representing the indices in order of relevance, e.g., [2, 0, 4]. "
        "Do not include any other text or markdown code blocks."
    )
    
    try:
        from app.ai.agent import clean_content
        res = await llm.ainvoke([
            SystemMessage(content="You are an expert search engine reranker. Determine the relevance of each document to the user query."),
            HumanMessage(content=prompt)
        ])
        cleaned = clean_content(res.content).strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("\n", 1)[0]
        if cleaned.startswith("json"):
            cleaned = cleaned.split("json", 1)[1].strip()
        indices = json.loads(cleaned)
        
        reranked = []
        for idx in indices:
            if 0 <= idx < len(docs):
                reranked.append(docs[idx])
        
        seen = {d["content"] for d in reranked}
        for d in docs:
            if d["content"] not in seen and len(reranked) < top_n:
                reranked.append(d)
                
        return reranked[:top_n]
    except Exception:
        return docs[:top_n]

