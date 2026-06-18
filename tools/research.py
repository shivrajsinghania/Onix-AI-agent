from tools.search import search
from tools.observer import observe_website
from tools.gemini_helper import get_service_knowledge, merge_and_extract
import re
from urllib.parse import urlparse


def _is_gov_url(url):
    patterns = [r'\.gov\.in', r'\.nic\.in', r'parivahan\.gov', r'sarathi\.', r'rtps\.', r'edistrict\.', r'serviceonline\.']
    return any(re.search(p, url, re.IGNORECASE) for p in patterns)


def _is_deep_page(url):
    path = urlparse(url).path.strip("/")
    return len(path) > 5 and path not in ["index.html", "index.php", "home", "en", "index"]


def _score_url(url, service):
    score = 0
    if _is_gov_url(url):
        score += 15
    if _is_deep_page(url):
        score += 8
    words = service.replace("_", " ").lower().split()
    for w in words:
        if len(w) > 3 and w in url.lower():
            score += 3
    if any(x in url.lower() for x in ["login", "signin", "register", "news", "contact", "about"]):
        score -= 10
    return score


def _scrape_best(urls, service):
    """Try URLs in order, return first one with real content."""
    for url in urls:
        try:
            obs = observe_website(url)
            content = obs.get("content", "")
            status = obs.get("status_code", 0)
            pdf_count = obs.get("pdf_count", 0)
            faq_count = obs.get("faq_count", 0)

            if status == 200 and len(content) > 400:
                extras = []
                if pdf_count: extras.append(f"{pdf_count} PDF(s)")
                if faq_count: extras.append(f"{faq_count} FAQ page(s)")
                extra_str = f" + {', '.join(extras)}" if extras else ""
                print(f"[research] Scraped OK: {url} ({len(content)} chars{extra_str})")
                return url, obs
            else:
                print(f"[research] Skipped {url}: status={status}, len={len(content)}")
        except Exception as e:
            print(f"[research] Failed {url}: {e}")
    return None, None


def research_service(service, state, subtype=None):
    service_label = service.replace("_", " ")
    if subtype:
        service_label = f"{subtype} {service_label}"

    print(f"\n[research] Starting: {service_label} in {state}")

    # ── Stage 1: Gemini knowledge ──────────────────────────────────────────────
    print("[research] Stage 1: Gemini knowledge...")
    knowledge = get_service_knowledge(service_label, state)

    if knowledge.get("has_subtypes") and knowledge.get("subtypes") and not subtype:
        print(f"[research] Subtypes found: {[s['label'] for s in knowledge['subtypes']]}")
        return {
            "service": service,
            "state": state,
            "needs_subtype": True,
            "subtypes": knowledge["subtypes"],
            "service_name": knowledge.get("service_name", service_label),
            "analysis": None
        }

    # ── Stage 2: Search → scrape + PDF/FAQ extraction ─────────────────────────
    search_query = knowledge.get("search_query") or f"{state} {service_label} official apply online"
    print(f"[research] Stage 2: SerpAPI query: '{search_query}'")

    search_result = search("google", search_query)
    all_results = search_result.get("all_results", [])

    candidate_urls = []
    gemini_url = knowledge.get("official_portal_url")
    if gemini_url:
        candidate_urls.append(gemini_url)
        print(f"[research] Gemini suggested URL: {gemini_url}")

    serp_urls = [r["url"] for r in sorted(all_results, key=lambda r: _score_url(r.get("url", ""), service), reverse=True)]
    for u in serp_urls:
        if u not in candidate_urls:
            candidate_urls.append(u)

    print(f"[research] Candidate URLs: {candidate_urls[:4]}")

    # observe_website now automatically finds and reads PDFs + FAQ pages inside
    successful_url, observation = _scrape_best(candidate_urls[:5], service)

    # ── Stage 3: Gemini merges everything ─────────────────────────────────────
    print("[research] Stage 3: Gemini merge...")

    live_content = observation.get("content", "") if observation else ""
    live_title = observation.get("title", "") if observation else ""
    final_url = successful_url or gemini_url or (candidate_urls[0] if candidate_urls else "")

    analysis = merge_and_extract(service_label, state, knowledge, live_content, final_url)

    return {
        "service": service,
        "state": state,
        "query": search_query,
        "url": final_url,
        "page_title": live_title,
        "analysis": analysis
    }
