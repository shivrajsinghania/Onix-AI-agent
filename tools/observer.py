import requests
from bs4 import BeautifulSoup

def observe_website(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # Remove noisy tags
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title = ""
        if soup.title:
            title = soup.title.get_text(strip=True)

        content = soup.get_text(
            separator = "",
            strip=True
        )

        # Keep memory usage low
        content = content[:2500]

        print(
            f"[observer] Scraped {url} "
            f"({len(content)} chars)"
        )

        return {
            "url": url,
            "title": title,
            "status_code": response.status_code,
            "content": content,
            "pdf_count": 0,
            "faq_count": 0
        }

    except Exception as e:
        print(f"[observer] Failed {url}: {e}")

        return {
            "url": url,
            "title": "",
            "status_code": 0,
            "content": "",
            "error": str(e)
        }