import requests
import time
from config.settings import SERPAPI_KEY


def _duckduckgo_search(query, num=5):
    """
    Free DuckDuckGo search using their HTML endpoint.
    No API key needed. Returns same structure as SerpAPI results.
    """
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num):
                results.append({
                    "url": r["href"],
                    "title": r.get("title", "")
                })
        return results
    except ImportError:
        print("[search] duckduckgo_search not installed. Run: pip install duckduckgo-search")
        return []
    except Exception as e:
        print(f"[search] DuckDuckGo error: {e}")
        # DDG sometimes rate-limits — wait and try once more
        try:
            time.sleep(2)
            from duckduckgo_search import DDGS
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=num):
                    results.append({
                        "url": r["href"],
                        "title": r.get("title", "")
                    })
            return results
        except Exception as e2:
            print(f"[search] DuckDuckGo retry also failed: {e2}")
            return []


def search(app, query):
    if app == "google":
        # ── Primary: SerpAPI ──────────────────────────────────────────────────
        serp_ok = False
        try:
            params = {
                "q": query,
                "api_key": SERPAPI_KEY,
                "engine": "google",
                "num": 5
            }
            response = requests.get(
                "https://serpapi.com/search",
                params=params,
                timeout=15
            )
            data = response.json()
            organic = data.get("organic_results", [])

            if organic:
                serp_ok = True
                print(f"[search] SerpAPI returned {len(organic)} results")
                return {
                    "url": organic[0]["link"],
                    "title": organic[0].get("title", ""),
                    "snippet": organic[0].get("snippet", ""),
                    "all_results": [
                        {"url": r["link"], "title": r.get("title", "")}
                        for r in organic[:5]
                    ],
                    "source": "serpapi"
                }
            else:
                print(f"[search] SerpAPI returned no organic results — trying DuckDuckGo")

        except Exception as e:
            print(f"[search] SerpAPI failed: {e} — trying DuckDuckGo")

        # ── Fallback: DuckDuckGo ──────────────────────────────────────────────
        ddg_results = _duckduckgo_search(query, num=5)
        if ddg_results:
            print(f"[search] DuckDuckGo returned {len(ddg_results)} results")
            return {
                "url": ddg_results[0]["url"],
                "title": ddg_results[0]["title"],
                "snippet": "",
                "all_results": ddg_results,
                "source": "duckduckgo"
            }

        # ── Last resort: Google search URL (no scraping) ──────────────────────
        print("[search] Both SerpAPI and DuckDuckGo failed — returning bare URL")
        return {
            "url": f"https://www.google.com/search?q={query}",
            "title": "",
            "snippet": "",
            "all_results": [],
            "source": "none"
        }

    elif app == "youtube":
        return {
            "url": f"https://www.youtube.com/results?search_query={query}"
        }
