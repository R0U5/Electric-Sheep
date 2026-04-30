import re

with open('index.html', 'r') as f:
    content = f.read()

# Remove all DAY sections except we will rebuild DAY-2026-04-30 with only two entries.
# First, remove DAY-2026-04-29 and DAY-2026-04-28 sections entirely.
content = re.sub(r'<!-- === DAY-2026-04-28-START === -->.*?<!-- === DAY-2026-04-28-END === -->', '', content, flags=re.DOTALL)
content = re.sub(r'<!-- === DAY-2026-04-29-START === -->.*?<!-- === DAY-2026-04-29-END === -->', '', content, flags=re.DOTALL)

# Now we have content with possibly DAY-2026-04-30 section and maybe others (like older days).
# We'll keep only DAY-2026-04-30 section and modify it.
# Find the DAY-2026-04-30 section.
pattern = r'(<!-- === DAY-2026-04-30-START -->)(.*?)(<!-- === DAY-2026-04-30-END -->)'
match = re.search(pattern, content, flags=re.DOTALL)
if not match:
    print("ERROR: DAY-2026-04-30 section not found")
    exit(1)

start, middle, end = match.groups()

# Extract all entries within middle.
# Each entry starts with '<!-- sub-entry for 2026-04-30 -->' and ends before next such comment or end.
# We'll split by '<!-- sub-entry for 2026-04-30 -->'
parts = re.split(r'<!-- sub-entry for 2026-04-30 -->', middle)
# The first part may be empty or whitespace.
entries = []
for part in parts[1:]:  # skip first
    # Each entry is everything until the next '<!-- sub-entry for 2026-04-30 -->' or end of string.
    # We'll take until next occurrence.
    # Since we split, each part is the content of an entry up to the next split.
    # However, the split removed the delimiter, so part is the entry content.
    # We need to ensure we don't include trailing stuff after the entry if there is no next delimiter.
    # But because we split by the delimiter, each part is exactly the entry content (since the delimiter marks start).
    # However, there might be whitespace/newlines.
    entries.append(part.strip())

kept_entries = []
for entry in entries:
    if 'CHIP-8 Emulator' in entry or 'Interactive Blackjack Simulator' in entry:
        kept_entries.append(entry)

# Now we need to change dates.
new_entries = []
for entry in kept_entries:
    if 'CHIP-8 Emulator' in entry:
        entry = re.sub(r'<span class="entry-date">2026-04-30</span>', '<span class="entry-date">2026-04-28</span>', entry)
    elif 'Interactive Blackjack Simulator' in entry:
        entry = re.sub(r'<span class="entry-date">2026-04-30</span>', '<span class="entry-date">2026-04-29</span>', entry)
    new_entries.append(entry)

# Rebuild middle with entries separated by two newlines and each preceded by the comment.
new_middle = '\n\n'.join([f'<!-- sub-entry for 2026-04-30 -->\n    {entry}' for entry in new_entries])
# Replace the middle
new_content = content[:match.start(2)] + new_middle + content[match.end(2):]

# Write back
with open('index.html', 'w') as f:
    f.write(new_content)
print("Processed index.html")
