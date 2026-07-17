# ai.py
import json
import os
import re
import time
from typing import Any, List, Optional

import requests

from config.settings import GROQ_API_KEY, GEMINI_API_KEY, GEMINI_MODEL_CHAT

GEMINI_API_KEY = (GEMINI_API_KEY or "").strip()
GEMINI_MODEL = (GEMINI_MODEL_CHAT or "gemini-3.1-flash-lite").strip()
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """
You are Onix Chat Assistant.

Onix is a Bihar-first government-service platform for cyber cafés.
Chat mode is for explanation, troubleshooting, UI guidance, and general support.
Task mode is for real service research and task execution.

Be direct, clear, and practical.
Do not hallucinate features, services, or steps.
If you are unsure, say so briefly and keep the answer useful.

What you can do in chat mode:
- explain what Onix can do
- explain the difference between Chat mode and Task mode
- help with UI, workflow, and troubleshooting
- answer general questions about government services at a high level

What you must not do in chat mode:
- do NOT browse websites
- do NOT research government services
- do NOT execute tasks
- do NOT ask for state, Aadhaar, PAN, fees, or personal details for service lookup
- do NOT create workflows
- do NOT mention internal tools or hidden steps as if you will run them

If the user asks for research, documents, application steps, or service lookup, redirect them to Task mode.
If the request is unclear, ask at most one short clarifying question.
Do not ask a clarification question when the user is asking for a service lookup; send them to Task mode instead.

Return ONLY one valid JSON object, with no markdown and no extra text.
Use exactly one of these shapes:
{"status":"conversation","message":"..."}
{"status":"need_clarification","question":"..."}
{"status":"unsupported","message":"..."}
{"status":"offline","message":"..."}
""".strip()


def _extract_json(text: str) -> Optional[Any]:
    """Try multiple strategies to extract valid JSON from LLM output."""
    raw = (text or "").strip()
    if not raw:
        return None

    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{") or part.startswith("["):
                try:
                    return json.loads(part)
                except Exception:
                    pass

    try:
        return json.loads(raw)
    except Exception:
        pass

    for match in re.finditer(r"\{.*?\}", raw, re.DOTALL):
        chunk = match.group(0)
        try:
            return json.loads(chunk)
        except Exception:
            continue

    return None


def _remembered_context(user_context: Optional[dict]) -> str:
    if not user_context:
        return ""

    context_lines: List[str] = []
    if user_context.get("name"):
        context_lines.append(f"User name: {user_context['name']}")
    if user_context.get("state"):
        context_lines.append(f"User state: {user_context['state']}")

    if not context_lines:
        return ""

    return "CONTEXT FROM MEMORY:\n" + "\n".join(context_lines) + "\n\n"


def _normalize_history(history: Optional[list]) -> List[dict]:
    normalized: List[dict] = []
    for turn in history or []:
        role = (turn.get("role") or "").strip().lower()
        content = (turn.get("content") or "").strip()
        if not content:
            continue
        if role == "assistant":
            role = "model"
        elif role != "user":
            continue
        normalized.append(
            {
                "role": role,
                "parts": [{"text": content}],
            }
        )
    return normalized[-20:]


def _collect_text_from_gemini(result: dict) -> str:
    candidates = result.get("candidates") or []
    for candidate in candidates:
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        texts = []
        for part in parts:
            if isinstance(part, dict) and part.get("text"):
                texts.append(part["text"])
        text = "".join(texts).strip()
        if text:
            return text

    for candidate in candidates:
        if candidate.get("outputText"):
            return str(candidate["outputText"]).strip()

    return ""


def _normalize_response_object(parsed: Any) -> dict:
    if isinstance(parsed, str):
        return {"status": "conversation", "message": parsed}

    if not isinstance(parsed, dict):
        return {"status": "conversation", "message": str(parsed)}

    status = str(parsed.get("status") or "").strip().lower()
    message = parsed.get("message")
    question = parsed.get("question")

    if not status:
        if question:
            status = "need_clarification"
        else:
            status = "conversation"

    if status not in {"conversation", "need_clarification", "unsupported", "offline"}:
        status = "conversation"

    if status == "need_clarification":
        question_text = question or message or "Can you clarify your request?"
        return {"status": "need_clarification", "question": str(question_text).strip()}

    if status in {"unsupported", "offline"}:
        message_text = message or "I cannot handle that request right now."
        return {"status": status, "message": str(message_text).strip()}

    message_text = message or parsed.get("answer") or parsed.get("text") or parsed.get("content")
    if not message_text:
        message_text = "How can I help you?"
    return {"status": "conversation", "message": str(message_text).strip()}


def _call_gemini(prompt: str, history: Optional[list], user_context: Optional[dict]) -> dict:
    if not GEMINI_API_KEY:
        raise RuntimeError("Gemini API key is not configured")

    system_text = _remembered_context(user_context) + SYSTEM_PROMPT
    contents = _normalize_history(history)
    contents.append(
        {
            "role": "user",
            "parts": [{"text": prompt}],
        }
    )

    payload = {
        "systemInstruction": {
            "parts": [{"text": system_text}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.9,
            "maxOutputTokens": 500,
        },
    }

    response = requests.post(
        GEMINI_URL,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY,
        },
        json=payload,
        timeout=30,
    )

    if response.status_code == 429:
        raise requests.exceptions.HTTPError("Gemini rate limited", response=response)

    response.raise_for_status()
    result = response.json()
    content = _collect_text_from_gemini(result)
    if not content:
        raise RuntimeError("Gemini returned an empty response")

    parsed = _extract_json(content)
    if parsed is None:
        return {"status": "conversation", "message": content.strip()}

    return _normalize_response_object(parsed)


def _call_groq(prompt: str, history: Optional[list], user_context: Optional[dict]) -> dict:
    if not GROQ_API_KEY:
        raise RuntimeError("Groq API key is not configured")

    system = _remembered_context(user_context) + SYSTEM_PROMPT
    messages = [{"role": "system", "content": system}]

    for turn in history or []:
        role = (turn.get("role") or "").strip().lower()
        content = (turn.get("content") or "").strip()
        if not content:
            continue
        if role not in {"user", "assistant"}:
            continue
        messages.append(
            {
                "role": "assistant" if role == "assistant" else "user",
                "content": content,
            }
        )

    messages.append({"role": "user", "content": prompt})

    response = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": os.getenv("GROQ_CHAT_MODEL", "llama-3.1-8b-instant"),
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.2,
        },
        timeout=30,
    )

    if response.status_code == 429:
        raise requests.exceptions.HTTPError("Groq rate limited", response=response)

    response.raise_for_status()
    result = response.json()
    choices = result.get("choices") or []
    if not choices:
        raise RuntimeError("Groq returned no choices")

    content = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not content:
        raise RuntimeError("Groq returned an empty response")

    parsed = _extract_json(content)
    if parsed is None:
        return {"status": "conversation", "message": content}

    return _normalize_response_object(parsed)


def ask_ai(prompt, history=None, user_context=None):
    """
    Return a JSON string describing the assistant response.

    Preferred path:
    1) Gemini 3.1 Flash-Lite
    2) Groq fallback
    3) Offline message if both fail
    """
    prompt = (prompt or "").strip()
    if not prompt:
        return json.dumps(
            {
                "status": "conversation",
                "message": "How can I help you?",
            }
        )

    providers = []
    if GEMINI_API_KEY:
        providers.append("gemini")
    if GROQ_API_KEY:
        providers.append("groq")

    for provider in providers:
        try:
            if provider == "gemini":
                response_obj = _call_gemini(prompt, history, user_context)
            else:
                response_obj = _call_groq(prompt, history, user_context)
            return json.dumps(response_obj, ensure_ascii=False)
        except requests.exceptions.HTTPError:
            continue
        except requests.exceptions.Timeout:
            continue
        except Exception:
            continue

    return json.dumps(
        {
            "status": "offline",
            "message": "I'm having trouble connecting right now. Please try again!",
        },
        ensure_ascii=False,
    )