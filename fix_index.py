import re

with open('index.html', 'r') as f:
    content = f.read()

# Remove DAY-2026-04-29 section
pattern = r'<!-- === DAY-2026-04-29-START === -->.*?<!-- === DAY-2026-04-29-END === -->'
content = re.sub(pattern, '', content, flags=re.DOTALL)

# Remove DAY-2026-04-28 section
pattern = r'<!-- === DAY-2026-04-28-START === -->.*?<!-- === DAY-2026-04-28-END === -->'
content = re.sub(pattern, '', content, flags=re.DOTALL)

# Now, extract the DAY-2026-04-30 section
pattern = r'(<!-- === DAY-2026-04-30-START === -->)(.*?)(<!-- === DAY-2026-04-30-END === -->)'
match = re.search(pattern, content, flags=re.DOTALL)
if match:
    start, middle, end = match.groups()
    # Find all entries in the middle
    # Each entry starts with '<!-- sub-entry for 2026-04-30 -->' and ends before the next such comment or the end marker.
    entry_pattern = r'(<!-- sub-entry for 2026-04-30 -->.*?)(?=<!-- sub-entry for 2026-04-30 -->|<!-- === DAY-2026-04-30-END === -->)'
    entries = re.findall(entry_pattern, middle, flags=re.DOTALL)
    
    kept_entries = []
    for entry in entries:
        if 'CHIP-8 Emulator' in entry or 'Interactive Blackjack Simulator' in entry:
            kept_entries.append(entry)
    
    # Change dates
    new_entries = []
    for entry in kept_entries:
        if 'CHIP-8 Emulator' in entry:
            entry = re.sub(r'<span class="entry-date">2026-04-30</span>', '<span class="entry-date">2026-04-28</span>', entry)
        elif 'Interactive Blackjack Simulator' in entry:
            entry = re.sub(r'<span class="entry-date">2026-04-30</span>', '<span class="entry-date">2026-04-29</span>', entry)
        new_entries.append(entry)
    
    # Rebuild middle
    new_middle = '\n\n'.join(new_entries)
    content = content[:match.start(2)] + new_middle + content[match.end(2):]

with open('index.html', 'w') as f:
    f.write(content)
