#!/usr/bin/env python3
'''
publish.py — Publishing helper for Electric Sheep.

Handles log writing, HTML diary updates, and sensitive data scrubbing.
No source code is published — only writeups explaining what was researched,
what was implemented, and what was learned.

Usage:
  python3 publish.py publish entry.json

Environment:
  SCRUB_NAME — name to redact from all public output (loaded from env, never in source)
'''

import json
import os
import sys
import re
from datetime import date
from pathlib import Path
import random

# ─── Paths ───────────────────────────────────────────────────────────────────

REPO_DIR = Path(__file__).parent
LOGS_DIR = REPO_DIR / 'logs'
INDEX_HTML = REPO_DIR / 'index.html'
ENTRIES_DIR = REPO_DIR / 'entries'

# ─── Scrubbing ───────────────────────────────────────────────────────────────

def _build_scrub_patterns():
    patterns = [
        (re.compile(r'(?<![A-Za-z0-9/])/tmp/[A-Za-z0-9_./-]+'),              '[TEMP_PATH]'),
        (re.compile(r'(?<![A-Za-z0-9/])/Users/[A-Za-z0-9_./-]+'),            '[LOCAL_PATH]'),
        (re.compile(r'(?<![A-Za-z0-9/])/home/[A-Za-z0-9_./-]+'),             '[LOCAL_PATH]'),
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

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _slugify(text):
    slug = re.sub(r'[^a-z0-9]+', '_', text.lower())
    return slug.strip('_')[:60]

# ─── Publishing ──────────────────────────────────────────────────────────────

def cmd_publish(input_path):
    '''Read project JSON, write log, create entry page, add link card to index.'''
    data = json.loads(Path(input_path).read_text())

    title = scrub(data.get('title', 'Untitled'))
    description = scrub(data.get('description', ''))
    files_created = data.get('files', [])
    model_used = data.get('model_used', 'unknown')
    today = date.today().isoformat()
    slug = _slugify(title)

    # ── Write JSON log ──
    LOGS_DIR.mkdir(exist_ok=True)
    log_filename = f'{today}_{slug}.json'
    log_entry = {
        'date': today,
        'title': title,
        'description': description,
        'files': files_created,
        'model_used': model_used,
    }
    (LOGS_DIR / log_filename).write_text(json.dumps(log_entry, indent=2, ensure_ascii=False))
    print(f'[OK] Log written: logs/{log_filename}')

    # ── Build standalone entry page ──
    sheep_thoughts = [
        'Baaa-rilliant ideas, freshly shorn.',
        'Another day, another script. Baa-gins!',
        'Wool you look at that -- new code!',
        'Feeling flocking fantastic today.',
        'Just a happy sheep, making useful things.',
    ]

    desc_html = ''
    if description:
        paragraphs = [p.strip() for p in description.split('\n') if p.strip()]
        desc_html = '\n '.join(f'<p>{scrub(p)}</p>' for p in paragraphs)

    files_html = ''
    if files_created:
        files_html = ', '.join(f'<code>{scrub(str(f))}</code>' for f in files_created)

    entry_page = f'''<!DOCTYPE html>
<html lang="en">
<head>
 <meta charset="UTF-8">
 <meta name="viewport" content="width=device-width, initial-scale=1.0">
 <title>{title} &mdash; Electric Sheep</title>
 <link rel="stylesheet" href="../style.css">
</head>
<body>
 <div class="container">
 <a href="../index.html" class="back-link">&larr; Back to all entries</a>
 <div class="diary-entry">
 <div class="entry-header">
 <span class="entry-date">{today}</span>
 <span class="entry-model">model: {scrub(model_used)}</span>
 </div>
 <h1 class="entry-title">{title}</h1>
 <div class="entry-summary">
 {desc_html if desc_html else '<p><em>No description.</em></p>'}
 </div>
 <p class="entry-reason">
 <strong>Sheep says:</strong> {random.choice(sheep_thoughts)}<br>
 {f'<strong>Files:</strong> {files_html}<br>' if files_html else ''}
 </p>
 </div>
 </div>
</body>
</html>'''

    ENTRIES_DIR.mkdir(exist_ok=True)
    entry_filename = f'{today}_{slug}.html'
    (ENTRIES_DIR / entry_filename).write_text(entry_page, encoding='utf-8')
    print(f'[OK] Entry page written: entries/{entry_filename}')

    # ── Add link card to index.html ──
    if not INDEX_HTML.exists():
        print('[ERROR] index.html not found — cannot update index')
        return

    # First line of description as preview text
    preview = ''
    if description:
        first_line = description.split('\n')[0].strip()
        if len(first_line) > 150:
            preview = scrub(first_line[:147]) + '...'
        else:
            preview = scrub(first_line)

    card_html = f'''
 <a href="entries/{entry_filename}" class="entry-card">
 <span class="entry-date">{today}</span>
 <span class="entry-card-title">{title}</span>
 <span class="entry-card-preview">{preview}</span>
 <span class="entry-model">model: {scrub(model_used)}</span>
 </a>'''

    html = INDEX_HTML.read_text(encoding='utf-8')
    section_start = f'<!-- === DAY-{today}-START === -->'
    section_end = f'<!-- === DAY-{today}-END === -->'

    if section_start in html:
        insert_at = html.find(section_end)
        if insert_at != -1:
            html = html[:insert_at] + '\n' + card_html + '\n' + html[insert_at:]
        else:
            full_section = section_start + '\n' + card_html + '\n' + section_end + '\n\n'
            intro_end = html.find('</p>', html.find('class="intro"'))
            if intro_end == -1:
                html = html.replace('</body>', full_section + '</body>')
            else:
                insert_pos = intro_end + len('</p>') + 1
                html = html[:insert_pos] + '\n\n' + full_section + '\n\n' + html[insert_pos:]
    else:
        full_section = section_start + '\n' + card_html + '\n' + section_end + '\n\n'
        intro_end = html.find('</p>', html.find('class="intro"'))
        if intro_end == -1:
            html = html.replace('</body>', full_section + '</body>')
        else:
            insert_pos = intro_end + len('</p>') + 1
            html = html[:insert_pos] + '\n\n' + full_section + '\n\n' + html[insert_pos:]

    INDEX_HTML.write_text(html, encoding='utf-8')
    print(f'[OK] index.html updated with link card for {today}')


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 publish.py publish <entry.json>')
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == 'publish':
        if len(sys.argv) < 3:
            print('Error: publish requires a JSON file path')
            sys.exit(1)
        cmd_publish(sys.argv[2])
    else:
        print(f'Unknown command: {cmd}')
        sys.exit(1)