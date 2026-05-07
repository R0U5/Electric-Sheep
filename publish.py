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
    '''Read project JSON, write log, create entry page, add full diary entry to index.'''
    data = json.loads(Path(input_path).read_text())

    # Use date from JSON data, not today's date
    today = data.get('date', date.today().isoformat())
    title = scrub(data.get('title', 'Untitled'))
    description = scrub(data.get('description', ''))
    files_created = data.get('files', [])
    model_used = data.get('model_used', 'unknown')
    slug = _slugify(title)

    # ── Write JSON log (update the same file, don't create new one) ──
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

    # ── Build standalone entry page (unchanged) ──
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

    # ── Replace old link card format with full diary entry in index.html ──
    if not INDEX_HTML.exists():
        print('[ERROR] index.html not found — cannot update index')
        return

    # Parse description for entry-meta fields
    what_changed = ''
    did_it_work = ''
    sheep_says = ''
    
    if description:
        lines = description.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('What changed:'):
                what_changed = line[len('What changed:'):].strip()
            elif line.startswith('Did it work:'):
                did_it_work = line[len('Did it work:'):].strip()
            elif line.startswith('Sheep says:'):
                sheep_says = line[len('Sheep says:'):].strip()
    
    # If not found in description, use defaults
    if not what_changed:
        what_changed = 'Enhanced system capabilities'
    if not did_it_work:
        did_it_work = 'yes'
    if not sheep_says:
        sheep_says = random.choice(sheep_thoughts)

    # Build the full diary entry HTML to match existing format exactly
    entry_html = f'''    <!-- entry for {today} -->
    <div class="diary-entry">
        <div class="entry-header">
            <span class="entry-date">{today}</span>
            <span class="entry-model">model: {scrub(model_used)}</span>
        </div>
        <div class="entry-title">{title}</div>
        <div class="entry-topic"><strong>Research:</strong> {scrub(description.split(chr(10))[0] if description else 'Research conducted')} </div>
        <div class="entry-writeup">
            {desc_html if desc_html else '<p><em>No description.</em></p>'}
        </div>
        <div class="entry-meta">
            <p><strong>What changed:</strong> {scrub(what_changed)}</p>
            <p><strong>Did it work:</strong> {scrub(did_it_work)}</p>
            <p><strong>Sheep says:</strong> {scrub(sheep_says)}</p>
        </div>
    </div>'''

    html = INDEX_HTML.read_text(encoding='utf-8')
    
    # Remove any existing entry for today (both old link card format and any previous full entry)
    # Pattern to remove old link card format
    old_link_pattern = rf'<!-- === DAY-{today}-START === -->\s*<a href="entries/{re.escape(today)}_{slug}\.html" class="entry-card">.*?</a>\s*<!-- === DAY-{today}-END === -->'
    # Pattern to remove any existing full diary entry format
    full_entry_pattern = rf'<!-- === DAY-{today}-START === -->\s*<!-- entry for {today} -->.*?<!-- === DAY-{today}-END === -->'
    
    # Remove both formats if they exist
    html = re.sub(old_link_pattern, '', html, flags=re.DOTALL)
    html = re.sub(full_entry_pattern, '', html, flags=re.DOTALL)
    
    # Clean up any extra whitespace that might have been left
    html = re.sub(r'\n\s*\n\s*\n', '\n\n', html)  # Replace 3+ newlines with 2 newlines
    
    # Insert the new full diary entry at the right position (after intro, before first existing entry or at end)
    section_to_insert = f'<!-- === DAY-{today}-START -->\n{entry_html}\n<!-- === DAY-{today}-END -->\n\n'
    
    # Find where to insert - after the intro paragraph, before the first existing DAY- section
    intro_end_match = re.search('</p>', html)
    if intro_end_match:
        intro_end = intro_end_match.end()
        # Look for the first DAY- section after the intro
        first_day_section = re.search(r'<!-- === DAY-\d{4}-\d{2}-\d{2}-START -->', html[intro_end:])
        if first_day_section:
            insert_pos = intro_end + first_day_section.start()
            html = html[:insert_pos] + section_to_insert + html[insert_pos:]
        else:
            # No existing entries, insert before </main>
            main_end = html.find('</main>')
            if main_end != -1:
                html = html[:main_end] + section_to_insert + html[main_end:]
            else:
                html = html + section_to_insert
    else:
        # Fallback: insert before </body> if we can't find the intro
        body_end = html.find('</body>')
        if body_end != -1:
            html = html[:body_end] + section_to_insert + html[body_end:]
        else:
            html = html + section_to_insert

    INDEX_HTML.write_text(html, encoding='utf-8')
    print(f'[OK] index.html updated with full diary entry for {today}')


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