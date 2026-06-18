import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


def _extract_pdf_text(url, headers):
    """
    Download a PDF and extract its text using pdfplumber.
    Returns extracted text string, or None if failed.
    Zero extra API credits — pure local processing.
    """
    try:
        import pdfplumber
        import io

        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None

        # Must actually be a PDF
        content_type = resp.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
            return None

        with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
            pages_text = []
            for page in pdf.pages[:6]:  # Max 6 pages — enough for any gov doc
                t = page.extract_text()
                if t:
                    pages_text.append(t.strip())
            text = "\n".join(pages_text)

        if len(text) > 100:
            print(f"[observer] PDF extracted: {url} ({len(text)} chars)")
            return text[:4000]  # Cap at 4000 chars
        return None

    except ImportError:
        print("[observer] pdfplumber not installed. Run: pip install pdfplumber")
        return None
    except Exception as e:
        print(f"[observer] PDF extract failed {url}: {e}")
        return None


def _find_pdf_and_faq_links(soup, base_url):
    """
    Scan the already-downloaded page HTML for PDF links and FAQ/help pages.
    No extra HTTP requests here — just parsing what we already have.
    Returns list of useful URLs found.
    """
    useful_urls = []
    seen = set()

    # Keywords that indicate a useful secondary page
    GOOD_KEYWORDS = [
        "pdf", "user guide", "userguide", "help", "faq",
        "instructions", "how to apply", "howto", "document",
        "guideline", "manual", "procedure", "checklist",
        "notification", "circular", "annexure"
    ]

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript"):
            continue

        full_url = urljoin(base_url, href)
        if full_url in seen:
            continue
        seen.add(full_url)

        href_lower = href.lower()
        text_lower = a.get_text(strip=True).lower()
        combined = href_lower + " " + text_lower

        # Direct PDF link
        if href_lower.endswith(".pdf"):
            useful_urls.append(("pdf", full_url))
            continue

        # Page whose URL or link text suggests useful content
        if any(kw in combined for kw in GOOD_KEYWORDS):
            useful_urls.append(("page", full_url))

    # Deduplicate and limit — max 3 PDFs, max 2 FAQ pages
    pdf_links = [u for t, u in useful_urls if t == "pdf"][:3]
    page_links = [u for t, u in useful_urls if t == "page"][:2]

    return pdf_links, page_links


def observe_website(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    # Remove noise tags
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title else ""
    html_text = soup.get_text(separator="\n", strip=True)[:3000]

    # Find PDF and FAQ links embedded in the page — no extra search credits
    pdf_links, faq_links = _find_pdf_and_faq_links(soup, url)

    # Extract PDF text (local processing, zero API cost)
    pdf_texts = []
    for pdf_url in pdf_links:
        text = _extract_pdf_text(pdf_url, headers)
        if text:
            pdf_texts.append(f"[PDF: {pdf_url}]\n{text}")

    # Scrape FAQ/help pages found on the main page
    faq_texts = []
    for faq_url in faq_links:
        try:
            r = requests.get(faq_url, headers=headers, timeout=8)
            if r.status_code == 200:
                s = BeautifulSoup(r.text, "html.parser")
                for tag in s(["script", "style", "nav", "footer"]):
                    tag.decompose()
                t = s.get_text(separator="\n", strip=True)[:2000]
                if len(t) > 200:
                    faq_texts.append(f"[Page: {faq_url}]\n{t}")
                    print(f"[observer] FAQ/help page scraped: {faq_url} ({len(t)} chars)")
        except Exception as e:
            print(f"[observer] FAQ page failed {faq_url}: {e}")

    # Combine all sources into one content blob
    all_content_parts = [html_text]
    if pdf_texts:
        all_content_parts.append("\n\n=== PDF DOCUMENTS FOUND ===\n" + "\n\n".join(pdf_texts))
    if faq_texts:
        all_content_parts.append("\n\n=== HELP/FAQ PAGES ===\n" + "\n\n".join(faq_texts))

    combined_content = "\n\n".join(all_content_parts)

    print(f"[observer] Content: HTML={len(html_text)}c, PDFs={len(pdf_texts)}, FAQs={len(faq_texts)}, Total={len(combined_content)}c")

    return {
        "url": url,
        "title": title,
        "status_code": response.status_code,
        "content": combined_content,
        "pdf_count": len(pdf_texts),
        "faq_count": len(faq_texts)
    }
