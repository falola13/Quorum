import json
import logging
import os
import re

import requests
import trafilatura
from bs4 import BeautifulSoup
from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException, TimeoutException
from dotenv import load_dotenv
from exa_py import Exa
from exa_py.errors import ExaTimeoutError
from langchain.tools import tool
from readability import Document
from readability.readability import Unparseable
from tavily import TavilyClient
from tavily.errors import (
    InvalidAPIKeyError,
    MissingAPIKeyError,
    UsageLimitExceededError,
)

load_dotenv()

logger = logging.getLogger(__name__)

TAVILY_FALLBACK_ERRORS = (
    InvalidAPIKeyError,
    MissingAPIKeyError,
    UsageLimitExceededError,
    TimeoutError,
    ConnectionError,
)

DDGS_FALLBACK_ERRORS = (
    DDGSException,
    RatelimitException,
    TimeoutException,
    TimeoutError,
    ConnectionError,
)

MAX_CHARS = 5000
MIN_CHARS = 200

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}

NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]


def _tavily_search(query: str, max_results: int = 5) -> str:
    """Search the web for recent and reliable information on a topic . Returns Titles, URLs and content"""

    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    results = tavily.search(query=query, max_results=max_results)

    out = []

    for r in results["results"]:
        out.append(
            f"Title: {r['title']}\nURL: {r['url']}\nSnippet:{r['content'][:300]}\n"
        )

    return "\n----\n".join(out)


def _ddg_search(query: str, max_results: int = 5) -> str:
    """Search the web using ddg"""

    with DDGS() as ddgs:
        results = ddgs.text(
            query,
            max_results=max_results,
            backend="auto",
        )

    out = []

    for r in results:
        out.append(f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}\n")

    return "\n----\n".join(out)


def _exa_search(query: str, max_results: int = 5) -> str:
    exa = Exa(api_key=os.getenv("EXA_API_KEY"))
    results = exa.search(
        query,
        num_results=max_results,
        text={"max_characters": 1000},
    )
    out = [
        f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['text']}\n"
        for r in results.results
    ]

    return "\n---\n".join(out)


def _clean(text: str) -> str:
    """Collapse whitespace and trim to MAX_CHARS."""
    return re.sub(r"\s+", " ", text).strip()[:MAX_CHARS]


def _strip_noise(html: str) -> str:
    """Remove non-content tags and return plain text."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def _extract_trafilatura(html: str) -> str | None:
    """Strategy 1: trafilatura (best for articles and blogs)."""
    text = trafilatura.extract(html, include_comments=False, include_tables=True)
    return text if text and len(text) > MIN_CHARS else None


def _extract_readability(html: str) -> str | None:
    """Strategy 2: readability, then clean with BeautifulSoup."""
    try:
        summary_html = Document(html).summary()
    except (Unparseable, ValueError) as e:
        logger.debug("Readability failed: %s", e)
        return None
    text = _strip_noise(summary_html)
    return text if len(text) > MIN_CHARS else None


def _extract_full_page(html: str) -> str | None:
    """Strategy 3: whole page text, minus noise. Last resort."""
    text = _strip_noise(html)
    return text or None


@tool
def search(query: str, max_results: int = 5) -> str:
    """Try Tavily first. Fall back to Exa then fallback to DuckDuckGo if it fails or runs out."""
    if os.getenv("TAVILY_API_KEY"):
        try:
            return _tavily_search(query, max_results)
        except TAVILY_FALLBACK_ERRORS as e:
            logger.warning("Tavily failed (%s), switching to Exa", e)
    elif os.getenv("EXA_API_KEY"):
        try:
            return _exa_search(query, max_results)
        except ExaTimeoutError as e:
            logger.warning("Exa failed (%s), Switching to DuckDuckGo", e)

    try:
        return _ddg_search(query, max_results)
    except DDGS_FALLBACK_ERRORS as e:
        logger.warning("DuckDockGo failed (%s)", e)
        return "Search is unavailable right now. No results were found for this query."


@tool
def scrape_url(url: str) -> str:
    """
    Scrape and extract clean readable content from a URL.
    Tries trafilatura, then readability, then full-page text.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return "Request timed out while scraping the URL."
    except requests.exceptions.HTTPError as e:
        return f"HTTP error occurred: {e!s}"
    except requests.RequestException as e:
        return f"Could not reach URL: {e!s}"

    content_type = response.headers.get("Content-Type", "")
    if "html" not in content_type:
        return f"Skipped: page is not HTML ({content_type or 'unknown type'})."

    html = response.text

    for strategy in (_extract_trafilatura, _extract_readability, _extract_full_page):
        text = strategy(html)
        if text:
            logger.debug("Extracted %s using %s", url, strategy.__name__)
            return _clean(text)

    return "Could not extract meaningful content from the page."
