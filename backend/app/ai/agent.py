from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from app.ai.tools import leave_balance_tool, rag_tool, work_updates_tool, web_search_tool
from app.core.config import settings
from app.services.cache_service import cache_service

os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_API_KEY


def clean_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            elif isinstance(part, str):
                parts.append(part)
        return "".join(parts)
    return str(content)


# ── State ─────────────────────────────────────────────────────────────────────


class HRAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    intent: str
    context: str
    user_id: str
    rewritten_queries: list[str]
    citations: list[dict]


# global cache for combination status: (model, api_key) -> (status, timestamp)
_combo_cache = {}
CACHE_TTL = 300  # 5 minutes


async def check_combination(model: str, key: str, timeout: float = 2.0) -> bool:
    now = time.time()
    cache_key = (model, key)
    if cache_key in _combo_cache:
        status, expiry = _combo_cache[cache_key]
        if now < expiry:
            return status == "working"
            
    test_llm = ChatGoogleGenerativeAI(
        model=model,
        temperature=0.0,
        google_api_key=key,
        timeout=timeout,
        max_retries=0
    )
    try:
        await asyncio.wait_for(
            test_llm.ainvoke([HumanMessage(content="1")]),
            timeout=timeout
        )
        _combo_cache[cache_key] = ("working", now + CACHE_TTL)
        return True
    except Exception:
        _combo_cache[cache_key] = ("exhausted", now + CACHE_TTL)
        return False


async def get_llm(temperature: float = 0.3):
    primary_model = settings.GEMINI_MODEL
    fallback_models = settings.fallback_models
    
    # Get all parsed api keys
    api_keys = settings.api_keys
    if not api_keys and settings.GOOGLE_API_KEY:
        api_keys = [settings.GOOGLE_API_KEY]
        
    candidates = []
    
    # 1. Primary model with all keys
    for key in api_keys:
        candidates.append((primary_model, key))
        
    # 2. Fallback models with all keys
    for model_name in fallback_models:
        if model_name != primary_model:
            for key in api_keys:
                candidates.append((model_name, key))
                
    try:
        checks = [check_combination(m, k) for m, k in candidates]
        results = await asyncio.gather(*checks)
    except Exception:
        results = [True] * len(candidates)
        
    working_candidates = [candidates[i] for i, is_ok in enumerate(results) if is_ok]
    
    if not working_candidates:
        working_candidates = candidates
        
    runnables = []
    for model_name, key in working_candidates:
        runnables.append(
            ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                google_api_key=key
            )
        )
        
    if not runnables:
        return ChatGoogleGenerativeAI(
            model=primary_model,
            temperature=temperature,
            google_api_key=settings.GOOGLE_API_KEY
        )
        
    primary = runnables[0]
    fallbacks = runnables[1:]
    
    if fallbacks:
        return primary.with_fallbacks(fallbacks)
    return primary


async def _get_llm():
    return await get_llm(temperature=0.3)


# ── Nodes ─────────────────────────────────────────────────────────────────────


async def query_rewriting(state: HRAgentState) -> dict:
    """Clarify relative terms (relative dates, names) and generate alternative search queries."""
    llm = await _get_llm()
    query = state["messages"][-1].content

    prompt = (
        "You are an AI HR assistant. Rewrite the following user query to clarify any relative time expressions "
        "(like 'next week', 'tomorrow') or ambiguous terms (assume today is Wednesday, June 24, 2026). "
        "Also, generate 2 alternative queries for searching company policies.\n\n"
        f"Query: {query}\n\n"
        "Respond in a strict JSON format with keys:\n"
        "- primary: the clarified primary query\n"
        "- alternatives: list of 2 alternative query strings\n"
        "Do not include markdown tags like ```json in your response."
    )

    try:
        res = await llm.ainvoke(
            [
                SystemMessage(content="You generate query variants as JSON."),
                HumanMessage(content=prompt),
            ]
        )
        cleaned = clean_content(res.content).strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("\n", 1)[0]
        if cleaned.startswith("json"):
            cleaned = cleaned.split("json", 1)[1].strip()
        data = json.loads(cleaned)
        primary = data.get("primary", query)
        alternatives = data.get("alternatives", [])
        return {"rewritten_queries": [primary] + alternatives}
    except Exception:
        return {"rewritten_queries": [query]}


async def classify_intent(state: HRAgentState) -> dict:
    """Classify the user's query intent using the primary rewritten query."""
    llm = await _get_llm()
    primary_query = state.get("rewritten_queries", [""])[0] or state["messages"][-1].content

    classification_prompt = (
        "You are an intent classifier for an HR assistant. "
        "Classify the following query into exactly one category:\n"
        "- rag: questions about company policies, roles, rules, or general HR knowledge\n"
        "- leave: questions about leave balance, leave history, applying for leave\n"
        "- work: questions about work updates, tasks, or progress\n"
        "- web_search: questions about external/industry trends, generic info not present in internal docs\n"
        "- direct: general greeting or conversational queries that don't need any tool search\n\n"
        f"Query: {primary_query}\n\n"
        "Respond with ONLY the category name (rag, leave, work, web_search, or direct)."
    )

    response = await llm.ainvoke(
        [
            SystemMessage(content="You are a precise classifier."),
            HumanMessage(content=classification_prompt),
        ]
    )
    intent = clean_content(response.content).strip().lower()

    # Map variations
    if intent not in ("rag", "leave", "work", "web_search", "direct"):
        if "leave" in intent:
            intent = "leave"
        elif "work" in intent or "update" in intent:
            intent = "work"
        elif "web" in intent or "search" in intent or "internet" in intent:
            intent = "web_search"
        elif any(kw in intent for kw in ("policy", "rule", "role", "company")):
            intent = "rag"
        else:
            intent = "direct"

    return {"intent": intent}


async def rag_retriever(state: HRAgentState) -> dict:
    """Search vector store using hybrid retrieval + reranking + context compression."""
    queries = state.get("rewritten_queries", [])
    if not queries:
        queries = [state["messages"][-1].content]

    # Cache check: hash the concatenated queries
    cache_key = hashlib.md5("|".join(queries).encode()).hexdigest()
    cached = await cache_service.get_rag_query(cache_key)
    if cached is not None and isinstance(cached, dict):
        return cached

    from app.ai.embeddings import hybrid_search, rerank_documents_with_llm

    # Multi-query retrieval: retrieve from vector/BM25 for all queries
    all_docs = []
    seen_contents = set()
    for q in queries:
        results = await hybrid_search(q, k=8)
        for r in results:
            if r["content"] not in seen_contents:
                seen_contents.add(r["content"])
                all_docs.append(r)

    # Reranking: filter down to top 5 using LLM
    reranked_docs = await rerank_documents_with_llm(queries[0], all_docs, top_n=5)

    # Citations compilation
    context_parts = []
    citations = []
    for idx, doc in enumerate(reranked_docs):
        doc_id = idx + 1
        source_name = doc["metadata"].get("source", "Company Policy")
        title = doc["metadata"].get("title", "Policy Document")
        doc_type = doc["metadata"].get("type", "company_rule")

        context_parts.append(f"[{doc_id}] (Source: {source_name} - {title})\n{doc['content']}")
        citations.append({
            "id": doc_id,
            "source": source_name,
            "title": title,
            "type": doc_type
        })

    context = "\n\n---\n\n".join(context_parts)

    # Context compression if excessively large
    if len(context) > 10000:
        llm = await _get_llm()
        compression_prompt = (
            f"Summarize the following retrieved documents to preserve only facts relevant to the query '{queries[0]}'. "
            f"Maintain the citation indices [1], [2] etc. where appropriate.\n\n{context}"
        )
        try:
            res = await llm.ainvoke(compression_prompt)
            context = clean_content(res.content)
        except Exception:
            pass

    result = {"context": context, "citations": citations}

    # Write to cache
    try:
        await cache_service.cache_rag_query(cache_key, result)
    except Exception:
        pass

    return result


async def db_leave_tool_node(state: HRAgentState) -> dict:
    """Query leave data for the user."""
    user_id = state.get("user_id", "")
    if not user_id:
        return {"context": "User ID not available. Please log in to check leave balance."}
    context = await leave_balance_tool(user_id)
    return {"context": context, "citations": []}


async def db_work_tool_node(state: HRAgentState) -> dict:
    """Query work update data for the user."""
    user_id = state.get("user_id", "")
    if not user_id:
        return {"context": "User ID not available. Please log in to check work updates."}
    context = await work_updates_tool(user_id)
    return {"context": context, "citations": []}


async def web_search_node(state: HRAgentState) -> dict:
    """Fallback web search when query doesn't match internal knowledge."""
    query = state.get("rewritten_queries", [""])[0] or state["messages"][-1].content
    context = await web_search_tool(query)
    citations = [{
        "id": 1,
        "source": "Web Search Fallback",
        "title": "DuckDuckGo Search",
        "type": "web"
    }]
    return {"context": context, "citations": citations}


async def generate_response(state: HRAgentState) -> dict:
    """Generate the final response using Gemini with retrieved context/structured data."""
    llm = await _get_llm()
    query = state["messages"][-1].content
    context = state.get("context", "")
    intent = state.get("intent", "direct")

    system_prompt = (
        "You are a helpful HR assistant. Answer questions accurately based on the provided context. "
        "Be concise and professional. If you don't have enough information, say so. "
        "Use inline citations like [1], [2] referencing the source indices in the context if applicable.\n\n"
    )

    if intent == "rag":
        system_prompt += (
            f"Context from knowledge base:\n{context}\n\n"
            "Use this context to answer the user's question. Output inline citations like [1], [2] at the end of statements."
        )
    elif intent == "leave":
        system_prompt += (
            f"Leave information:\n{context}\n\n"
            "Help the user with their leave-related question."
        )
    elif intent == "work":
        system_prompt += (
            f"Work update information:\n{context}\n\n"
            "Help the user with their work update question."
        )
    elif intent == "web_search":
        system_prompt += (
            f"Web search fallback context:\n{context}\n\n"
            "Synthesize this web context to answer the user's question, citing the source details."
        )
    else:
        system_prompt += "Answer the user's question directly."

    # Incorporate history/conversation memory
    chat_history = []
    # Feed last 10 messages of history
    for msg in state["messages"][:-1]:
        chat_history.append(msg)

    response = await llm.ainvoke(
        chat_history + [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query),
        ]
    )

    return {"messages": [AIMessage(content=clean_content(response.content))]}


async def hallucination_check(state: HRAgentState) -> dict:
    """Verify if the generated response is factually grounded in the retrieved context."""
    intent = state.get("intent", "direct")
    if intent not in ("rag", "web_search") or not state.get("context"):
        return {}

    context = state.get("context", "")
    # Find last AI message
    response = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage):
            response = msg.content
            break

    if not response:
        return {}

    llm = await _get_llm()
    prompt = (
        "Verify if the AI's response is fully grounded in and supported by the retrieved context. "
        "If there are claims in the response that are NOT supported by the context, flag them as hallucinated.\n\n"
        f"Retrieved Context:\n{context}\n\n"
        f"AI Response:\n{response}\n\n"
        "Respond in strict JSON format with keys:\n"
        "- is_grounded: boolean (true if fully supported, false if contains unsupported claims)\n"
        "- corrected_response: string (only if is_grounded is false, rewrite the response to only use supported claims, else empty string)\n"
        "Do not include markdown tags like ```json."
    )

    try:
        res = await llm.ainvoke(
            [
                SystemMessage(content="You verify factual grounding."),
                HumanMessage(content=prompt),
            ]
        )
        cleaned = clean_content(res.content).strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("\n", 1)[0]
        if cleaned.startswith("json"):
            cleaned = cleaned.split("json", 1)[1].strip()
        data = json.loads(cleaned)
        if not data.get("is_grounded", True) and data.get("corrected_response"):
            corrected = data["corrected_response"]
            # Overwrite the last AI message with the corrected response
            return {"messages": [AIMessage(content=corrected)]}
    except Exception:
        pass
    return {}


# ── Router ────────────────────────────────────────────────────────────────────


def route_intent(state: HRAgentState) -> str:
    """Route to the appropriate tool based on intent."""
    intent = state.get("intent", "direct")
    mapping = {
        "rag": "rag_retriever",
        "leave": "db_leave_tool",
        "work": "db_work_tool",
        "web_search": "web_search",
        "direct": "generate_response",
    }
    return mapping.get(intent, "generate_response")


# ── Graph ─────────────────────────────────────────────────────────────────────


def get_agent():
    """Build and compile the LangGraph agent."""
    graph = StateGraph(HRAgentState)

    # Add nodes
    graph.add_node("query_rewriting", query_rewriting)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("rag_retriever", rag_retriever)
    graph.add_node("db_leave_tool", db_leave_tool_node)
    graph.add_node("db_work_tool", db_work_tool_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("generate_response", generate_response)
    graph.add_node("hallucination_check", hallucination_check)

    # Set entry point
    graph.set_entry_point("query_rewriting")

    # Connect query_rewriting -> classify_intent
    graph.add_edge("query_rewriting", "classify_intent")

    # Add conditional routing from classifier
    graph.add_conditional_edges(
        "classify_intent",
        route_intent,
        {
            "rag_retriever": "rag_retriever",
            "db_leave_tool": "db_leave_tool",
            "db_work_tool": "db_work_tool",
            "web_search": "web_search",
            "generate_response": "generate_response",
        },
    )

    # All search nodes go to generate_response
    graph.add_edge("rag_retriever", "generate_response")
    graph.add_edge("db_leave_tool", "generate_response")
    graph.add_edge("db_work_tool", "generate_response")
    graph.add_edge("web_search", "generate_response")

    # generate_response goes to hallucination check
    graph.add_edge("generate_response", "hallucination_check")

    # hallucination_check ends
    graph.add_edge("hallucination_check", END)

    return graph.compile()
