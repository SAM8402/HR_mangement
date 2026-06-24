from __future__ import annotations

import json
from unittest.mock import AsyncMock
import pytest
from httpx import AsyncClient
from langchain_core.messages import AIMessage

from app.services.doc_processor import chunk_text
from app.ai.embeddings import hybrid_search, rerank_documents_with_llm
from app.models.company_rule import CompanyRule


# ── Mocks Setup ───────────────────────────────────────────────────────────────


def get_mock_llm_response(prompt_text: str) -> str:
    prompt_lower = prompt_text.lower()
    if "intent classifier" in prompt_lower:
        if "policy" in prompt_lower or "rule" in prompt_lower:
            return "rag"
        elif "leave" in prompt_lower:
            return "leave"
        elif "work" in prompt_lower:
            return "work"
        return "rag"
    elif "relevance of each document" in prompt_lower:
        return "[0]"
    elif "verify if the ai's response is fully grounded" in prompt_lower:
        return '{"is_grounded": true, "corrected_response": ""}'
    elif "suitable title and category" in prompt_lower:
        return '{"title": "Attendance Policy", "category": "general"}'
    elif "job description text and extract" in prompt_lower:
        return '{"title": "DevOps Engineer", "description": "Manage servers", "responsibilities": "CI/CD", "skills": ["Docker", "Linux"]}'
    elif "generate query variants" in prompt_lower:
        return '{"primary": "leave policy", "alternatives": ["leave rules", "notice period"]}'
    else:
        return "Based on the policy [1], the notice period for leave is 2 weeks."


@pytest.fixture(autouse=True)
def mock_gemini(monkeypatch):
    """Automatically mock all calls to Gemini LLM and Embeddings for offline testing."""
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

    # Mock LLM ainvoke
    async def mock_ainvoke(self, input_data, *args, **kwargs):
        if isinstance(input_data, list):
            prompt = input_data[-1].content
        else:
            prompt = str(input_data)
        content = get_mock_llm_response(prompt)
        return AIMessage(content=content)

    monkeypatch.setattr(ChatGoogleGenerativeAI, "ainvoke", mock_ainvoke)

    # Mock Embeddings embed_documents & embed_query
    monkeypatch.setattr(GoogleGenerativeAIEmbeddings, "embed_documents", lambda self, texts: [[0.1] * 768 for _ in texts])
    monkeypatch.setattr(GoogleGenerativeAIEmbeddings, "embed_query", lambda self, text: [0.1] * 768)

    # Mock ChromaDB similarity_search_with_relevance_scores
    from langchain_chroma import Chroma
    class MockDocument:
        def __init__(self, content, metadata):
            self.page_content = content
            self.metadata = metadata

    def mock_similarity_search(self, query, k=5, **kwargs):
        return [
            (
                MockDocument(
                    "Employees must give 2 weeks notice before taking leave.",
                    {"title": "Leave Policy", "source": "leave_policy.pdf", "type": "company_rule"}
                ),
                0.9
            )
        ]

    monkeypatch.setattr(Chroma, "similarity_search_with_relevance_scores", mock_similarity_search)
    yield


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_chunk_text():
    """Test text chunking logic."""
    text = "Hello World. " * 200
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    # Check that chunks are split reasonably
    assert all(len(c) <= 150 for c in chunks)


@pytest.mark.asyncio
async def test_hybrid_search(db_session, test_users):
    """Test hybrid search combines database entries."""
    admin_user = test_users["admin"]
    rule = CompanyRule(
        title="Notice Period",
        content="Employees must give 2 weeks notice before taking leave.",
        category="leave",
        created_by=admin_user.id
    )
    db_session.add(rule)
    await db_session.flush()

    results = await hybrid_search("notice period", k=1)
    assert len(results) > 0
    # BM25 or Chroma mock will return matches
    assert "notice" in results[0]["content"].lower() or "leave" in results[0]["content"].lower()


@pytest.mark.asyncio
async def test_rerank_documents():
    """Test LLM-based document rerank query selector."""
    docs = [
        {"content": "Relevant leave rule: 2 weeks notice required.", "metadata": {}},
        {"content": "Irrelevant info about office cafeteria.", "metadata": {}}
    ]
    reranked = await rerank_documents_with_llm("leave notice", docs, top_n=1)
    assert len(reranked) == 1


@pytest.mark.asyncio
async def test_chat_agent_rag_workflow(client: AsyncClient, test_users):
    """Test end-to-end chat flow runs through all graph nodes and includes citations."""
    login_res = await client.post(
        "/api/auth/login",
        json={"email": "employee@test.com", "password": "password123"}
    )
    token = login_res.json()["access_token"]

    response = await client.post(
        "/api/chat",
        json={"query": "What is the notice period policy?"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "answer" in res_data
    assert "citations" in res_data
    assert len(res_data["citations"]) > 0
    assert res_data["citations"][0]["source"] == "leave_policy.pdf"


@pytest.mark.asyncio
async def test_get_llm_with_multiple_keys_and_fallbacks(monkeypatch):
    """Test get_llm constructs fallbacks correctly based on multiple api keys and fallback models."""
    from app.core.config import settings
    from app.ai.agent import get_llm
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.runnables import RunnableWithFallbacks

    # Save original values
    orig_api_keys = settings.api_keys
    orig_google_api_key = settings.GOOGLE_API_KEY
    orig_fallback_chain = settings.LLM_FALLBACK_CHAIN
    orig_gemini_model = settings.GEMINI_MODEL

    try:
        # Scenario 1: Only single key, no fallbacks
        settings.api_keys = ["mock-key-1"]
        settings.GOOGLE_API_KEY = "mock-key-1"
        settings.LLM_FALLBACK_CHAIN = ""
        settings.GEMINI_MODEL = "gemini-2.5-flash"
        
        llm = await get_llm(temperature=0.2)
        assert isinstance(llm, ChatGoogleGenerativeAI)
        assert llm.model == "models/gemini-2.5-flash"
        assert llm.temperature == 0.2
        assert llm.google_api_key.get_secret_value() == "mock-key-1"

        # Scenario 2: Multiple keys, no fallbacks
        settings.api_keys = ["mock-key-1", "mock-key-2"]
        settings.GOOGLE_API_KEY = "mock-key-1"
        settings.LLM_FALLBACK_CHAIN = ""
        
        llm_keys = await get_llm(temperature=0.5)
        assert isinstance(llm_keys, RunnableWithFallbacks)
        # Primary model with key 1
        assert llm_keys.runnable.model == "models/gemini-2.5-flash"
        assert llm_keys.runnable.google_api_key.get_secret_value() == "mock-key-1"
        assert llm_keys.runnable.temperature == 0.5
        # Fallbacks (primary model with key 2)
        assert len(llm_keys.fallbacks) == 1
        assert llm_keys.fallbacks[0].model == "models/gemini-2.5-flash"
        assert llm_keys.fallbacks[0].google_api_key.get_secret_value() == "mock-key-2"
        assert llm_keys.fallbacks[0].temperature == 0.5

        # Scenario 3: Multiple keys AND fallback models
        settings.api_keys = ["mock-key-1", "mock-key-2"]
        settings.GOOGLE_API_KEY = "mock-key-1"
        settings.LLM_FALLBACK_CHAIN = "gemini-2.5-flash, gemini-1.5-flash"
        
        llm_full = await get_llm(temperature=0.1)
        assert isinstance(llm_full, RunnableWithFallbacks)
        # Primary: gemini-2.5-flash with mock-key-1
        assert llm_full.runnable.model == "models/gemini-2.5-flash"
        assert llm_full.runnable.google_api_key.get_secret_value() == "mock-key-1"
        
        # Fallbacks:
        # 1. gemini-2.5-flash with mock-key-2
        # 2. gemini-1.5-flash with mock-key-1
        # 3. gemini-1.5-flash with mock-key-2
        assert len(llm_full.fallbacks) == 3
        
        assert llm_full.fallbacks[0].model == "models/gemini-2.5-flash"
        assert llm_full.fallbacks[0].google_api_key.get_secret_value() == "mock-key-2"
        
        assert llm_full.fallbacks[1].model == "models/gemini-1.5-flash"
        assert llm_full.fallbacks[1].google_api_key.get_secret_value() == "mock-key-1"
        
        assert llm_full.fallbacks[2].model == "models/gemini-1.5-flash"
        assert llm_full.fallbacks[2].google_api_key.get_secret_value() == "mock-key-2"
        
        # All of them should have the configured temperature
        assert all(f.temperature == 0.1 for f in llm_full.fallbacks)
        assert llm_full.runnable.temperature == 0.1

    finally:
        settings.api_keys = orig_api_keys
        settings.GOOGLE_API_KEY = orig_google_api_key
        settings.LLM_FALLBACK_CHAIN = orig_fallback_chain
        settings.GEMINI_MODEL = orig_gemini_model


@pytest.mark.asyncio
async def test_get_llm_filters_exhausted_keys(monkeypatch):
    """Test get_llm filters out exhausted API key/model combinations."""
    from app.core.config import settings
    from app.ai.agent import get_llm
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.runnables import RunnableWithFallbacks
    from langchain_core.messages import AIMessage

    orig_api_keys = settings.api_keys
    orig_google_api_key = settings.GOOGLE_API_KEY
    orig_fallback_chain = settings.LLM_FALLBACK_CHAIN
    orig_gemini_model = settings.GEMINI_MODEL

    # Custom mock_ainvoke that fails for mock-key-2 but succeeds for others
    async def mock_ainvoke_with_selective_failure(self, input_data, *args, **kwargs):
        key = self.google_api_key.get_secret_value() if self.google_api_key else ""
        if key == "mock-key-2":
            raise Exception("429 Resource Exhausted")
        return AIMessage(content="mock-response")

    monkeypatch.setattr(ChatGoogleGenerativeAI, "ainvoke", mock_ainvoke_with_selective_failure)

    try:
        # Scenario: Multiple keys, but mock-key-2 is exhausted/failed
        settings.api_keys = ["mock-key-1", "mock-key-2"]
        settings.GOOGLE_API_KEY = "mock-key-1"
        settings.LLM_FALLBACK_CHAIN = ""
        settings.GEMINI_MODEL = "gemini-2.5-flash"
        
        # Clear health check cache to force clean run
        from app.ai.agent import _combo_cache
        _combo_cache.clear()

        # (gemini-2.5-flash, mock-key-1) -> succeeds
        # (gemini-2.5-flash, mock-key-2) -> fails (429)
        # So only mock-key-1 should be included in the chain!
        llm = await get_llm(temperature=0.3)
        
        # Since only 1 combination is working, it should return a single ChatGoogleGenerativeAI instance directly, NOT a RunnableWithFallbacks
        assert isinstance(llm, ChatGoogleGenerativeAI)
        assert llm.model == "models/gemini-2.5-flash"
        assert llm.google_api_key.get_secret_value() == "mock-key-1"

    finally:
        settings.api_keys = orig_api_keys
        settings.GOOGLE_API_KEY = orig_google_api_key
        settings.LLM_FALLBACK_CHAIN = orig_fallback_chain
        settings.GEMINI_MODEL = orig_gemini_model


def test_clean_content():
    """Test clean_content helper processes strings and list of parts correctly."""
    from app.ai.agent import clean_content

    assert clean_content("hello") == "hello"
    assert clean_content(["hello", " ", "world"]) == "hello world"
    assert clean_content([{"type": "text", "text": "foo"}, "bar", {"type": "other"}]) == "foobar"
    assert clean_content(123) == "123"
