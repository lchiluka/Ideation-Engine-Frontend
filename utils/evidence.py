"""Evidence harvesting utilities."""

from __future__ import annotations

import asyncio
import aiohttp
import logging
from typing import List, Dict
from utils.query_generator import generate_academic_search_query
import feedparser
import time

# WARNING: SSL verification is disabled for all outgoing requests in this module
# by setting ``ssl=False`` and using connectors with ``ssl=False``. This bypasses
# certificate checks and should only be used in trusted environments.

from .llm import serp_lookup
from agents import AGENTS

Evidence = Dict[str, str]

MAX_SNIPPET_LEN = 300
MAX_RESULTS = 15

# Escape backslashes and quotes to avoid JSON issues downstream
def sanitize_snippet(snippet: str) -> str:
    """Return *snippet* safe for inclusion in prompts."""
    return snippet.replace("\\", "\\\\").replace('"', '\\"')

# Backoff handler to log retry attempts
def _on_backoff(details):
    logging.warning(
        "Backing off %.1fs after %s tries calling %s",
        details['wait'],
        details['tries'],
        details['target'],
    )


def retry_async(max_tries: int = 4, initial: float = 1.0, factor: float = 2.0):
    """Retry decorator for async functions with exponential backoff."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            delay = initial
            for attempt in range(1, max_tries + 1):
                try:
                    return await func(*args, **kwargs)
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    if attempt == max_tries:
                        raise
                    _on_backoff({
                        'wait': delay,
                        'tries': attempt,
                        'target': func.__name__,
                    })
                    await asyncio.sleep(delay)
                    delay *= factor
        return wrapper

    return decorator


@retry_async()
async def _fetch_json(session: aiohttp.ClientSession, url: str, **params) -> dict:
    """Fetch JSON with retries and a longer timeout."""
    async with session.get(url, params=params, timeout=15, ssl=False) as resp:
        resp.raise_for_status()
        return await resp.json()


async def fetch_crossref(query: str, k: int = 5,
                         session: aiohttp.ClientSession | None = None) -> List[Evidence]:
    sess = session or aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))
    try:
        try:
            core_query = generate_academic_search_query(query, max_keywords=14)
        except Exception:
            # Fallback if LLM call fails; shorten manually
            core_query = query[:100]

        data = await _fetch_json(
            sess,
            "https://api.crossref.org/works",
            query=core_query,
            rows=k,
        )
        items = data.get("message", {}).get("items", [])[:k]
        return [
            {
                "title": it.get("title", [""])[0],
                "snippet": (it.get("abstract") or "")[:MAX_SNIPPET_LEN],
                "source_url": it.get("URL"),
            }
            for it in items
        ]
    except Exception as e:  # pragma: no cover - network
        logging.warning(
            "CrossRef fetch failed for query '%s': %s",
            query,
            e,
            exc_info=True,
        )
        return []
    finally:
        if session is None:
            await sess.close()


@retry_async()

async def fetch_arxiv(query: str, k: int = 5,
                      session: aiohttp.ClientSession | None = None) -> List[Evidence]:
    """
    1) Attempt to shorten `query` via generate_academic_search_query (sync)
       inside asyncio.to_thread, with a 60s timeout. If it fails or times out,
       fall back to the first 100 chars of `query`.
    2) Send HTTPS GET to arXiv with a 60s timeout, retrying up to 3 times
       (exponential backoff 1s→2s→4s). Return a list of dicts or [].
    """

    # === 1) Condense via LLM (run in thread + 60s timeout) ===
    llm_timeout = 60  # seconds

    # Log the length of the incoming query
    logging.info(f"LLM‐shortener received input of length {len(query)} characters")

    try:
        start_time = time.time()
        core_query = await asyncio.wait_for(
            asyncio.to_thread(generate_academic_search_query, query, 8),
            timeout=llm_timeout
        )
        elapsed = time.time() - start_time

        core_query = core_query.strip()
        if core_query:
            logging.info(f"LLM helper returned in {elapsed:.1f}s; core_query='{core_query}'")
        else:
            # If LLM returned an empty string, fall back to truncation
            core_query = query[:100].strip()
            logging.info(
                f"LLM helper returned empty string in {elapsed:.1f}s; "
                f"falling back to first 100 chars: '{core_query}'"
            )

    except asyncio.TimeoutError:
        logging.warning(
            "LLM query generation timed out after %.1fs; falling back to truncation.",
            llm_timeout
        )
        core_query = query[:100].strip()

    except Exception as e:
        elapsed = time.time() - start_time
        logging.warning(
            "LLM query generation raised exception after %.1fs: %s. "
            "Falling back to truncation.",
            elapsed, e
        )
        core_query = query[:100].strip()

    if not core_query:
        logging.info("After fallback, core_query is empty—returning []")
        return []

    # === 2) Prepare HTTP session (if not provided) ===
    own_session = False
    if session is None:
        own_session = True
        session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))

    # === 3) Retry loop with exponential backoff ===
    max_attempts = 3
    backoff = 1.0  # seconds

    for attempt in range(1, max_attempts + 1):
        try:
            params = {
                "search_query": core_query,
                "start": 0,
                "max_results": k
            }
            # Log each arXiv attempt
            logging.info(f"arXiv fetch attempt {attempt}/3 for query '{core_query}'")

            async with session.get(
                "https://export.arxiv.org/api/query",
                params=params,
                timeout=60
            ) as resp:
                resp.raise_for_status()
                text = await resp.text()

            feed = feedparser.parse(text)
            results: List[Evidence] = []
            for entry in feed.entries[:k]:
                title = getattr(entry, "title", "")
                summary = getattr(entry, "summary", "")
                snippet = summary[:MAX_SNIPPET_LEN]
                link = getattr(entry, "link", "")
                results.append({
                    "title": title,
                    "snippet": snippet,
                    "source_url": link
                })

            logging.info(f"arXiv fetch succeeded on attempt {attempt}")
            return results[:MAX_RESULTS]

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logging.warning(
                "arXiv fetch attempt %d/%d failed for query '%s': %s",
                attempt, max_attempts, core_query, e
            )
            if attempt == max_attempts:
                logging.error(f"arXiv fetch failed after {max_attempts} attempts; returning []")
                break

            logging.info(f"Waiting {backoff:.1f}s before retrying arXiv fetch")
            await asyncio.sleep(backoff)
            backoff *= 2  # backoff: 1s → 2s → 4s

        except Exception as e:
            logging.error("Unexpected error in fetch_arxiv: %s", e, exc_info=True)
            break

    if own_session:
        await session.close()

    return []


@retry_async()
async def fetch_patents(query: str, k: int = 5,
                        session: aiohttp.ClientSession | None = None) -> List[Evidence]:
    sess = session or aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))
    try:
        params = {"q": query, "o": {"per_page": k}}
        body = {"q": query, "o": {"per_page": k}}
        async with sess.get("https://search.patentsview.org/api/v1/patents/query",
                            json=body, timeout=15, ssl=False) as resp:
            resp.raise_for_status()
            data = await resp.json()
        items = data.get("patents", [])[:k]
        return [
            {
                "title": it.get("patent_title"),
                "snippet": (it.get("patent_abstract") or "")[:MAX_SNIPPET_LEN],
                "source_url": f"https://patents.google.com/patent/{it.get('patent_number')}"
            }
            for it in items
        ]
    except Exception as e:  # pragma: no cover - network
        logging.warning(
            "PatentsView fetch failed for query '%s': %s",
            query,
            e,
            exc_info=True,
        )
        return []
    finally:
        if session is None:
            await sess.close()


async def fetch_open_web(query: str, k: int = 5) -> List[Evidence]:
    raw = await asyncio.to_thread(serp_lookup, query, k)
    out = []
    for item in raw:
        title = item.get("title") or item.get("snippet")
        snippet = item.get("snippet") or ""
        url = item.get("link")
        out.append(
            {"title": title, "snippet": snippet[:MAX_SNIPPET_LEN], "source_url": url}
        )
    return out


async def validate_urls(evidence: List[Evidence]) -> List[Evidence]:
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as sess:
        # SSL verification is disabled for this validation session.
        async def _ok(url: str) -> bool:
            try:
                async with sess.head(url, timeout=5, ssl=False) as resp:
                    return resp.status < 400
            except Exception:
                return False

        tasks = [_ok(ev["source_url"]) for ev in evidence]
        ok_list = await asyncio.gather(*tasks)
    return [ev for ev, ok in zip(evidence, ok_list) if ok]


async def gather_evidence(query: str) -> List[Evidence]:
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as sess:
        # SSL verification is disabled for this session as well.
        tasks = [
            fetch_arxiv(query, 5, sess),
            fetch_crossref(query, 5, sess),
            #fetch_patents(query, 2, sess),
            fetch_open_web(query, 3),
        ]
        chunks = await asyncio.gather(*tasks, return_exceptions=True)
    evidence: List[Evidence] = []
    for chunk in chunks:
        if isinstance(chunk, Exception):
            logging.warning("Evidence task failed: %s", chunk)
        else:
            evidence.extend(chunk)
    evidence = evidence[:MAX_RESULTS]
    evidence = await validate_urls(evidence)
    return evidence
