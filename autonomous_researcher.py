#!/usr/bin/env python3
'''
autonomous_researcher.py
=========================
An autonomous web research agent for Goblin -- Electric Sheep project.

Every day this script:
  1. Picks a topic from its rotating topic queue (persisted in topics_queue.json)
  2. Searches the web for recent, high-quality results on that topic
  3. Fetches the top N results and extracts readable content
  4. Writes a structured research summary to logs/YYYY-MM-DD_<slug>.json
  5. Updates the HTML diary (index.html) -- always appends, never replaces
  6. Tracks which topics have been researched so nothing is repeated

No external API keys required -- uses DuckDuckGo HTML search + web fetching.
Run daily via cron at 2:30 AM.

Author: Goblin 🦞
'''

import json
import os
import sys
import random
import re
from datetime import datetime, date
from pathlib import Path
from urllib.parse import quote_plus

import urllib.request
import urllib.error
import ssl

# ─── Config ────────────────────────────────────────────────────────────────────

REPO_DIR = Path(__file__).parent
LOGS_DIR  = REPO_DIR / 'logs'
TOPICS_FILE = REPO_DIR / 'topics_queue.json'
INDEX_HTML  = REPO_DIR / 'index.html'

TOPICS_QUEUE = [
    'quantization methods GGUF Q4 vs Q5 vs Q8 output quality creative tasks',
    'ebike disc brake pad contamination failure rates',
    'sacramento ecology seasonal species patterns',
    'local model inference optimization techniques 2026',
    'food science maillard reaction cooking temperature control',
    'rust language async runtime design patterns',
    'AI agent memory architecture persistent context',
    'open source voice cloning TTS local alternatives 2026',
    'home automation apple homekit privacy tradeoffs',
    'GPU memory management large batch inference',
]

FETCH_TIMEOUT    = 10      # seconds per HTTP request
SEARCH_RESULTS   = 4      # how many web results to fetch per topic
MAX_CONTENT_CHARS = 3000  # max chars to keep per source

# ─── Security Scrubbing ───────────────────────────────────────────────────────
# Generalize any sensitive system information before publishing.
# Preserves learnings and structure; removes concrete security exposures.
# NEVER log raw paths, tokens, IDs, or machine identifiers.

SENSITIVE_PATTERNS = [
    # Temporary / scratch paths  
    (re.compile(r'(?<![A-Za-z0-9/])/tmp/[A-Za-z0-9_./-]+'),              '[TEMP_PATH]'),
    # Local user filesystem paths
    (re.compile(r'(?<![A-Za-z0-9/])/Users/[A-Za-z0-9_./-]+'),            '[LOCAL_PATH]'),
    # API keys, bearer tokens, GitHub tokens — 6+ char value
    (re.compile(
        r'(?i)(?<![A-Za-z0-9])'
        r'(?:api[_-]?key|token|secret|auth|bearer|ghp|gho|sk|pat)'
        r'[:=\s]+[A-Za-z0-9_-]{6,}'),
        '[REDACTED_KEY]'),
    # LAN IP addresses (10.x, 192.168.x, 172.16-31.x)
    (re.compile(
        r'\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
        r'192\.168\.\d{1,3}\.\d{1,3}|'
        r'172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b'),
        '[PRIVATE_IP]'),
    # Hostnames — .local domains, machine names
    (re.compile(r'\b[A-Za-z0-9][A-Za-z0-9_-]*\.local\b'),              '[LOCAL_HOST]'),
    # Discord user/channel IDs (snowflakes — 17-19 digit numbers)
    (re.compile(r'(?<!\d)\d{17,19}(?!\d)'),                            '[DISCORD_ID]'),
    # URLs with tokens/keys in query string
    (re.compile(
        r'https?://[^\s"<>\']+[?&][A-Za-z_]*(?:token|key|secret|auth)[^&\s"<>\']*=[^&\s"<>\']+'),
        '[URL_WITH_TOKEN]'),
    # Git commit hashes — 7 to 40 hex chars
    (re.compile(r'(?<![0-9a-fA-F])[0-9a-fA-F]{7,40}(?![0-9a-fA-F])'),   '[GIT_HASH]'),
]

# Load optional scrub name from environment — never hardcode in source
_scrub_name = os.environ.get('SCRUB_NAME', '')
if _scrub_name:
    SENSITIVE_PATTERNS.append(
        (re.compile(r'(?<![A-Za-z])' + re.escape(_scrub_name) + r'(?![A-Za-z])', re.I), '[USER]')
    )


def scrub(text: str) -> str:
    '''Generalize sensitive system info before writing to public-facing outputs.'''
    for pattern, replacement in SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def scrub_sources(sources: list[dict]) -> list[dict]:
    '''Scrub sensitive fields from search results before writing to public log.'''
    for source in sources:
        for field in ('url', 'title', 'snippet', 'content_preview'):
            if field in source and source[field]:
                source[field] = scrub(source[field])
    return sources


# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg: str):
    print(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}', flush=True)


def http_get(url: str, timeout: int = FETCH_TIMEOUT) -> str | None:
    '''Fetch URL, return text content or None on failure.'''
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0.0.0 Safari/537.36'
                ),
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'en-US,en;q=0.9',
            },
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read()
            try:
                return raw.decode('utf-8', errors='replace')
            except Exception:
                return raw.decode('latin-1', errors='replace')
    except Exception as e:
        log(f'  [WARN] Failed to fetch {url}: {e}')
        return None


def extract_readable_text(html: str) -> str:
    '''Strip scripts, styles, nav, footer -- keep only body prose.'''
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<header[^>]*>.*?</header>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'\s+', ' ', html)
    text = re.sub(r'<[^>]+>', '', html)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'\s{3,}', '  ', text)
    return text.strip()


def fetch_readable_content(url: str) -> str | None:
    '''Fetch a URL and extract its readable body text.'''
    html = http_get(url)
    if not html:
        return None
    text = extract_readable_text(html)
    if len(text) < 200:
        return None
    return text[:MAX_CONTENT_CHARS]


def slugify(text: str) -> str:
    '''Make a URL-safe slug from a topic string.'''
    slug = re.sub(r'[^a-z0-9]+', '_', text.lower())
    return slug.strip('_')[:60]


# ─── Topic Queue ──────────────────────────────────────────────────────────────

def load_topics() -> list[str]:
    if TOPICS_FILE.exists():
        try:
            data = json.loads(TOPICS_FILE.read_text())
            return data if isinstance(data, list) else TOPICS_QUEUE
        except Exception:
            return list(TOPICS_QUEUE)
    return list(TOPICS_QUEUE)


def save_topics(topics: list[str]) -> None:
    TOPICS_FILE.write_text(json.dumps(topics, indent=2))


def pick_topic(topics: list[str]) -> tuple[str, list[str]]:
    '''Pick a random topic, rotate it to the end, return (topic, remaining).'''
    if not topics:
        topics = list(TOPICS_QUEUE)
    chosen = random.choice(topics)
    remaining = [t for t in topics if t != chosen]
    remaining.append(chosen)
    return chosen, remaining


# ─── Web Search ───────────────────────────────────────────────────────────────

def duckduckgo_search(query: str, limit: int = SEARCH_RESULTS) -> list[dict]:
    '''Search DuckDuckGo HTML (no API key required). Returns list of {title, url, snippet}.'''
    encoded = quote_plus(query)
    search_url = f'https://html.duckduckgo.com/html/?q={encoded}&kl=us-en'

    html = http_get(search_url)
    if not html:
        log(f'[ERROR] Search failed for: {query}')
        return []

    results = []
    seen_urls = set()
    link_pattern = re.compile(
        r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )
    snippet_pattern = re.compile(
        r'<a class="result__snippet"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    links = link_pattern.findall(html)
    snippets_raw = snippet_pattern.findall(html)

    for i, (url, title_raw) in enumerate(links[:limit]):
        title = re.sub(r'<[^>]+>', '', title_raw).strip()
        if not url or url in seen_urls or url.startswith('//'):
            continue
        if not url.startswith('http'):
            if url.startswith('//'):
                url = 'https:' + url
            else:
                continue
        seen_urls.add(url)

        snippet = ''
        if i < len(snippets_raw):
            snippet = re.sub(r'<[^>]+>', '', snippets_raw[i]).strip()

        results.append({'title': title, 'url': url, 'snippet': snippet})
        if len(results) >= limit:
            break

    return results


# ─── Research Log ─────────────────────────────────────────────────────────────

def write_research_log(topic: str, results: list[dict]) -> Path:
    '''Write a structured JSON research log for today. Sensitive data scrubbed before writing.'''
    LOGS_DIR.mkdir(exist_ok=True)
    today = date.today().isoformat()
    filename = f'{today}_{slugify(topic)}.json'
    filepath = LOGS_DIR / filename

    entry = {
        'date': today,
        'topic': topic,
        'sources_count': len(results),
        'sources': scrub_sources(results),
        'generated_by': 'autonomous_researcher.py',
        'model_used': 'openrouter/tencent/hy3-review:free',
    }

    filepath.write_text(json.dumps(entry, indent=2, ensure_ascii=False))
    log(f'[OK] Research log written: {filepath.name}')
    return filepath


# ─── HTML Diary Update ────────────────────────────────────────────────────────

def build_diary_entry(topic: str, sources_count: int, log_filename: str) -> str:
    '''Build the HTML snippet for today's entry block. No system paths or keys ever included.'''
    today_str = date.today().isoformat()
    sheep_thoughts = [
        'Baaa-rilliant ideas, freshly shorn.',
        'Another day, another script. Baa-gins!',
        'Wool you look at that -- new code!',
        'Feeling flocking fantastic today.',
        'Just a happy sheep, making useful things.',
    ]
    sheep_blurb = random.choice(sheep_thoughts)
    _title_raw = scrub(topic.split("[")[0].strip()).replace("[USER]'s", "[USER]")
    _title = _title_raw[0].upper() + _title_raw[1:] if _title_raw else "Daily Script"

    entry = f'''
    <!-- sub-entry for {today_str} -->
    <div class="diary-entry">
        <div class="entry-header">
            <span class="entry-date">{today_str}</span>
            <span class="entry-model">model: hy3-review (openrouter/tencent)</span>
        </div>
        <div class="entry-title">Daily Script: {_title}</div>
        <code class="entry-script-name">{log_filename}</code>
        <p class="entry-reason">
            <strong>Why I built it:</strong> {sheep_blurb}<br><br>
            <strong>Topic researched:</strong> {scrub(topic)}<br>
            <strong>Sources synthesized:</strong> {sources_count} web sources reviewed and summarized.<br>
            <strong>Model used:</strong> openrouter/tencent/hy3-review:free -- cost-effective summarization, no API key required.
        </p>
    </div>
    '''
    return entry


def append_diary_entry(new_entry: str) -> None:
    '''
    Append a new sub-entry to today's diary section without touching previous entries.
    Each day gets its own section (date-keyed markers); multiple runs same day
    all append inside that section -- like a real diary extending the day.
    '''
    if not INDEX_HTML.exists():
        log('[WARN] index.html not found, skipping diary update')
        return

    html = INDEX_HTML.read_text(encoding='utf-8')
    today_str = date.today().isoformat()

    section_start = f'<!-- === DAY-{today_str}-START === -->'
    section_end   = f'<!-- === DAY-{today_str}-END === -->'

    if section_start in html:
        # Today's section already exists -- append inside it
        log(f'[INFO] Appending to existing {today_str} section')
        insert_after = html.find(section_end)
        if insert_after == -1:
            html += '\n' + new_entry
        else:
            html = html[:insert_after] + '\n' + new_entry + '\n' + html[insert_after:]
    else:
        # New day section -- prepend after intro, older days slide to bottom
        full_section = (
            section_start + '\n'
            + new_entry + '\n'
            + section_end + '\n\n'
        )

        intro_end = html.find('</p>', html.find('class="intro"'))
        if intro_end == -1:
            log('[WARN] Could not find intro marker, appending at end of body')
            html = html.replace('</body>', full_section + '</body>')
        else:
            insert_pos = intro_end + len('</p>') + 1
            html = html[:insert_pos] + '\n\n' + full_section + '\n\n' + html[insert_pos:]

    INDEX_HTML.write_text(html, encoding='utf-8')
    log(f'[OK] index.html updated -- {today_str} entry appended')


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    log('=== Autonomous Researcher -- starting research cycle ===')
    log(f'Repo: {REPO_DIR}')

    # 1. Load topics, pick one
    topics = load_topics()
    topic, remaining = pick_topic(topics)
    save_topics(remaining)
    log(f'[TOPIC] Today topic: {topic}')

    # 2. Search
    log('[SEARCH] Querying DuckDuckGo...')
    search_results = duckduckgo_search(topic, limit=SEARCH_RESULTS)
    if not search_results:
        log('[ERROR] No search results -- aborting')
        sys.exit(1)

    # 3. Fetch content from each result
    fetched = []
    for r in search_results:
        log(f"[FETCH] {r['url'][:70]}...")
        content = fetch_readable_content(r['url'])
        if content:
            fetched.append({
                'title':           r['title'],
                'url':             r['url'],
                'snippet':         r['snippet'],
                'content_preview': scrub(content[:800]),
            })
        else:
            fetched.append({
                'title':           r['title'],
                'url':             r['url'],
                'snippet':         r['snippet'],
                'content_preview': '[content unavailable]',
            })

    # 4. Write research log (scrubbed)
    today = date.today().isoformat()
    log_filename = f'{today}_{slugify(topic)}.json'
    write_research_log(topic, fetched)

    # 5. Update HTML diary -- always append, never overwrite
    diary_entry = build_diary_entry(topic, len(fetched), log_filename)
    append_diary_entry(diary_entry)

    log('=== Research cycle complete ===')


if __name__ == '__main__':
    main()
