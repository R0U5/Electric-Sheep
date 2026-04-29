#!/usr/bin/env python3
'''
publish.py — File operations helper for Electric Sheep.

Handles topic rotation, research log writing, and HTML diary updates.
All research and synthesis is done by OpenClaw via the cron prompt.
This script only does deterministic file manipulation and scrubbing.

Usage:
  python3 publish.py pick-topic    # Pick a topic, rotate queue, print it
  python3 publish.py publish research.json   # Write log + update diary from JSON

Environment:
  SCRUB_NAME — name to redact from all public output (loaded from env, never in source)
'''

import json
import os
import sys
import random
import re
from datetime import date
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────

REPO_DIR = Path(__file__).parent
LOGS_DIR  = REPO_DIR / 'logs'
TOPICS_FILE = REPO_DIR / 'topics_queue.json'
INDEX_HTML  = REPO_DIR / 'index.html'

DEFAULT_TOPICS = [
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

# ─── Scrubbing ───────────────────────────────────────────────────────────────

def _build_scrub_patterns():
    patterns = [
        (re.compile(r'(?<![A-Za-z0-9/])/tmp/[A-Za-z0-9_./-]+'),              '[TEMP_PATH]'),
        (re.compile(r'(?<![A-Za-z0-9/])/Users/[A-Za-z0-9_./-]+'),            '[LOCAL_PATH]'),
        (re.compile(
            r'(?i)(?<![A-Za-z0-9])'
            r'(?:api[_-]?key|token|secret|auth|bearer|ghp|gho|sk|pat)'
            r'[:=\s]+[A-Za-z0-9_-]{6,}'),
            '[REDACTED_KEY]'),
        (re.compile(
            r'\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
            r'192\.168\.\d{1,3}\.\d{1,3}|'
            r'172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b'),
            '[PRIVATE_IP]'),
        (re.compile(r'\b[A-Za-z0-9][A-Za-z0-9_-]*\.local\b'),              '[LOCAL_HOST]'),
        (re.compile(r'(?<!\d)\d{17,19}(?!\d)'),                            '[DISCORD_ID]'),
        (re.compile(
            r'https?://[^\s"<>\']+[?&][A-Za-z_]*(?:token|key|secret|auth)[^&\s"<>\']*=[^&\s"<>\']+'),
            '[URL_WITH_TOKEN]'),
    ]
    scrub_name = os.environ.get('SCRUB_NAME', '')
    if scrub_name:
        patterns.append(
            (re.compile(r'(?<![A-Za-z])' + re.escape(scrub_name) + r'(?![A-Za-z])', re.I), '[USER]')
        )
    return patterns

_SCRUB_PATTERNS = _build_scrub_patterns()


def scrub(text):
    '''Remove sensitive info from text before writing to public files.'''
    for pattern, replacement in _SCRUB_PATTERNS:
        text = pattern.sub(replacement, text)
    return text

# ─── Topic Rotation ─────────────────────────────────────────────────────────

def cmd_pick_topic():
    '''Pick a random topic, rotate it to end of queue, print it to stdout.'''
    if TOPICS_FILE.exists():
        try:
            topics = json.loads(TOPICS_FILE.read_text())
            if not isinstance(topics, list) or not topics:
                topics = list(DEFAULT_TOPICS)
        except Exception:
            topics = list(DEFAULT_TOPICS)
    else:
        topics = list(DEFAULT_TOPICS)

    chosen = random.choice(topics)
    remaining = [t for t in topics if t != chosen]
    remaining.append(chosen)
    TOPICS_FILE.write_text(json.dumps(remaining, indent=2))
    print(chosen)

# ─── Publishing ────────────────────────────────────────────────────────────────

def _slugify(text):
    slug = re.sub(r'[^a-z0-9]+', '_', text.lower())
    return slug.strip('_')[:60]


def cmd_publish(input_path):
    '''Read research JSON, write log file, append diary entry to index.html.'''
    data = json.loads(Path(input_path).read_text())

    topic    = data['topic']
    summary  = scrub(data.get('summary', ''))
    sources  = data.get('sources', [])
    model_used = data.get('model_used', 'unknown')
    today    = date.today().isoformat()

    # Scrub all source fields
    for s in sources:
        for key in ('title', 'url', 'snippet'):
            if key in s and s[key]:
                s[key] = scrub(str(s[key]))

    # ── Write JSON log ──
    LOGS_DIR.mkdir(exist_ok=True)
    filename = f'{today}_{_slugify(topic)}.json'
    log_entry = {
        'date': today,
        'topic': topic,
        'summary': summary,
        'sources_count': len(sources),
        'sources': sources,
        'model_used': model_used,
    }
    (LOGS_DIR / filename).write_text(json.dumps(log_entry, indent=2, ensure_ascii=False))
    print(f'[OK] Log written: logs/{filename}')

    # ── Build HTML diary entry ──
    sheep_thoughts = [
        'Baaa-rilliant ideas, freshly shorn.',
        'Another day, another script. Baa-gins!',
        'Wool you look at that -- new code!',
        'Feeling flocking fantastic today.',
        'Just a happy sheep, making useful things.',
    ]

    summary_html = ''
    if summary and not summary.startswith('['):
        paragraphs = [p.strip() for p in summary.split('\n') if p.strip()]
        summary_html = '\n        '.join(f'<p>{scrub(p)}</p>' for p in paragraphs)

    entry_html = f'''
    <!-- sub-entry for {today} -->
    <div class="diary-entry">
        <div class="entry-header">
            <span class="entry-date">{today}</span>
            <span class="entry-model">model: {scrub(model_used)}</span>
        </div>
        <div class="entry-title">{scrub(topic).title()}</div>
        <code class="entry-script-name">{filename}</code>
        <div class="entry-summary">
            <strong>Research synthesis:</strong>
            {summary_html if summary_html else '<p><em>No summary available.</em></p>'}
        </div>
        <p class="entry-reason">
            <strong>Sheep says:</strong> {random.choice(sheep_thoughts)}<br>
            <strong>Sources reviewed:</strong> {len(sources)}<br>
        </p>
    </div>'''

    # ── Append to index.html ──
    if not INDEX_HTML.exists():
        print('[ERROR] index.html not found — cannot update diary')
        return

    html = INDEX_HTML.read_text(encoding='utf-8')
    section_start = f'<!-- === DAY-{today}-START === -->'
    section_end = f'<!-- === DAY-{today}-END === -->'

    if section_start in html:
        # Today already has a section — append inside it
        insert_at = html.find(section_end)
        if insert_at != -1:
            html = html[:insert_at] + '\n' + entry_html + '\n' + html[insert_at:]
    else:
        # New day — insert after intro, before older days
        full_section = section_start + '\n' + entry_html + '\n' + section_end + '\n\n'
        intro_end = html.find('</p>', html.find('class="intro"'))
        if intro_end == -1:
            html = html.replace('</body>', full_section + '</body>')
        else:
            insert_pos = intro_end + len('</p>') + 1
            html = html[:insert_pos] + '\n\n' + full_section + '\n\n' + html[insert_pos:]

    INDEX_HTML.write_text(html, encoding='utf-8')
    print(f'[OK] index.html updated for {today}')

# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage:')
        print('  python3 publish.py pick-topic')
        print('  python3 publish.py publish <research.json>')
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == 'pick-topic':
        cmd_pick_topic()
    elif cmd == 'publish':
        if len(sys.argv) < 3:
            print('Error: publish requires a JSON file path')
            sys.exit(1)
        cmd_publish(sys.argv[2])
    else:
        print(f'Unknown command: {cmd}')
        sys.exit(1)
