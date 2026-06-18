from config.settings import GEMINI_API_KEY
import json
import re

# Lazy-loaded client — only initialized on first research call
_client = None

def _get_client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _parse_json(text):
    """Safely extract JSON from Gemini response."""
    if not text:
        return None
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                try:
                    return json.loads(part)
                except:
                    pass
    try:
        return json.loads(text)
    except:
        pass
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    return None


def _call_gemini(prompt_text, retries=3, delay=3):
    """
    Gemini call with automatic retry on 503 (server overload).
    Tries up to `retries` times with `delay` seconds between attempts.
    """
    import time
    client = _get_client()
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_text
            )
            return response.text
        except Exception as e:
            last_error = e
            err_str = str(e)
            # Only retry on 503 (overload) — not on auth or quota errors
            if "503" in err_str or "UNAVAILABLE" in err_str:
                if attempt < retries:
                    print(f"[gemini] 503 on attempt {attempt}/{retries} — retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2  # exponential backoff: 3s, 6s, 12s
                else:
                    print(f"[gemini] 503 after {retries} attempts — giving up")
            else:
                # Non-503 error (quota, auth, bad request) — don't retry
                print(f"[gemini] Non-retryable error: {e}")
                break

    raise last_error


# ── Stage 1: Training knowledge ───────────────────────────────────────────────
def get_service_knowledge(service, state):
    service_label = service.replace("_", " ")

    prompt_text = (
        "You are an expert on Indian government services.\n\n"
        f"Service requested: {service_label}\n"
        f"State: {state}\n\n"
        "Answer from your training knowledge. Return ONLY valid JSON, no markdown.\n\n"
        "{\n"
        '  "service_name": "full official name",\n'
        '  "has_subtypes": true or false,\n'
        '  "subtypes": [\n'
        '    {"id": "short_key", "label": "Human readable name", "description": "one line"}\n'
        "  ],\n"
        '  "official_portal_url": "deepest direct URL, not homepage",\n'
        '  "portal_name": "name of the portal",\n'
        '  "known_documents": [\n'
        '    {"name": "document name", "size": "size spec or null"}\n'
        "  ],\n"
        '  "known_fee": "fee or null",\n'
        '  "known_timeline": "timeline or null",\n'
        '  "known_eligibility": "who can apply or null",\n'
        '  "known_steps": ["step 1", "step 2"],\n'
        '  "search_query": "specific Google query to find the exact application page"\n'
        "}\n\n"
        "RULES:\n"
        "- has_subtypes = true ONLY if user must choose a type before applying.\n"
        "  TRUE examples: driving license (learning/permanent), passport (fresh/renewal/tatkal).\n"
        "  FALSE examples: PMUY, income certificate, Ayushman Bharat, PAN card, residence certificate.\n"
        "- If in doubt, set has_subtypes = false.\n"
        "- official_portal_url: give the deepest URL you know. "
        "For Bihar RTPS: serviceonline.bihar.gov.in. For Sarathi: sarathi.parivahan.gov.in. "
        "For PMUY: pmuy.gov.in.\n"
        "- search_query: specific enough to land on the actual application page, not a listing.\n"
        "- If unsure, set to null. Do NOT guess."
    )

    try:
        text = _call_gemini(prompt_text)
        result = _parse_json(text)
        if result:
            print(f"[gemini] Stage 1 done. has_subtypes={result.get('has_subtypes')}, url={result.get('official_portal_url')}")
            return result
        else:
            print(f"[gemini] Stage 1: could not parse JSON from response")
    except Exception as e:
        print(f"[gemini] Stage 1 failed: {e}")

    # Fallback — pipeline continues with no Gemini knowledge
    return {
        "service_name": service_label,
        "has_subtypes": False,
        "subtypes": [],
        "official_portal_url": None,
        "portal_name": None,
        "known_documents": [],
        "known_fee": None,
        "known_timeline": None,
        "known_eligibility": None,
        "known_steps": [],
        "search_query": f"{state} {service_label} official apply online"
    }


# ── Stage 3: Merge training knowledge + live scraped content ──────────────────
def merge_and_extract(service, state, knowledge, live_content, live_url):
    service_label = service.replace("_", " ")
    content_snippet = (live_content or "")[:4000]

    knowledge_str = json.dumps({
        "known_documents": knowledge.get("known_documents", []),
        "known_fee": knowledge.get("known_fee"),
        "known_timeline": knowledge.get("known_timeline"),
        "known_eligibility": knowledge.get("known_eligibility"),
        "known_steps": knowledge.get("known_steps", [])
    }, indent=2)

    has_live = bool(content_snippet and len(content_snippet) > 100)

    if has_live:
        source_instruction = (
            "Merge both sources. Live scraped content (Source B) takes priority "
            "for fees, documents, and steps. Fill gaps using Source A."
        )
        source_b_text = content_snippet
        source_value = "live_page"
    else:
        source_instruction = (
            "Source B is unavailable. Use Source A (training knowledge) only. "
            "Provide everything you know accurately."
        )
        source_b_text = "NOT AVAILABLE — website could not be scraped."
        source_value = "training_knowledge"

    prompt_text = (
        "You are extracting complete information about a government service.\n\n"
        f"Service: {service_label}\n"
        f"State: {state}\n"
        f"Source URL: {live_url}\n\n"
        "SOURCE A — Training knowledge:\n"
        f"{knowledge_str}\n\n"
        "SOURCE B — Live scraped page content:\n"
        f"{source_b_text}\n\n"
        f"{source_instruction}\n\n"
        "Return ONLY valid JSON, no markdown:\n"
        "{\n"
        '  "service_name": "full official name",\n'
        f'  "state": "{state}",\n'
        '  "required_documents": [\n'
        '    {"name": "document name", "size": "size spec or null"}\n'
        "  ],\n"
        '  "photo_requirements": "photo size/specs or null",\n'
        '  "signature_requirements": "signature specs or null",\n'
        '  "fee": "exact fee or Free or null",\n'
        '  "processing_time": "how long or null",\n'
        '  "application_steps": ["step 1", "step 2"],\n'
        '  "eligibility": "who can apply or null",\n'
        '  "validity": "validity period or null",\n'
        '  "subtypes_note": "mention subtypes if relevant, else null",\n'
        '  "notes": "other important info or null",\n'
        f'  "source": "{source_value}"\n'
        "}\n\n"
        "RULES:\n"
        "- List every document mentioned in either source.\n"
        "- Do NOT invent information not in either source.\n"
        "- application_steps: actual numbered steps to apply online.\n"
        "- Unknown fields: set to null."
    )

    err_msg = None
    try:
        text = _call_gemini(prompt_text)
        result = _parse_json(text)
        if result:
            print(f"[gemini] Stage 3 done. docs={len(result.get('required_documents', []))}, fee={result.get('fee')}")
            return result
        else:
            err_msg = "Could not parse JSON from Stage 3 response"
            print(f"[gemini] Stage 3: {err_msg}")
    except Exception as e:
        err_msg = str(e)
        print(f"[gemini] Stage 3 failed: {e}")

    # Fallback: return training knowledge directly
    return {
        "service_name": knowledge.get("service_name", service_label),
        "state": state,
        "required_documents": knowledge.get("known_documents", []),
        "fee": knowledge.get("known_fee"),
        "processing_time": knowledge.get("known_timeline"),
        "application_steps": knowledge.get("known_steps", []),
        "eligibility": knowledge.get("known_eligibility"),
        "source": "training_knowledge",
        "error": f"Gemini Stage 3 failed: {err_msg}"
    }
