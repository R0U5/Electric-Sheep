import re

with open('index.html', 'r') as f:
    html = f.read()

# Find the DAY-2026-04-30 section
pattern = r'(<!-- === DAY-2026-04-30-START === -->)(.*?)(<!-- === DAY-2026-04-30-END === -->)'
match = re.search(pattern, html, re.DOTALL)
if not match:
    print("DAY-2026-04-30 section not found")
    exit(1)

start, middle, end = match.groups()

# Split the middle into entries. Each entry starts with '<!-- sub-entry for 2026-04-30 -->'
# We'll split by that delimiter, but keep the delimiter for each entry.
parts = re.split(r'(<!-- sub-entry for 2026-04-30 -->)', middle)
# The first part is possibly empty or whitespace before the first entry.
# Then we have alternating: delimiter, entry content, delimiter, entry content, ...
# We'll reconstruct entries by pairing.

entries = []
i = 1  # skip first if empty
while i < len(parts):
    delim = parts[i]
    content = parts[i+1] if i+1 < len(parts) else ''
    entries.append(delim + content)
    i += 2

# We expect 4 entries.
if len(entries) != 4:
    print(f"Expected 4 entries, got {len(entries)}")
    # For safety, we'll just take the last two entries (which are CHIP-8 and Blackjack)
    # But let's check by looking for the titles.
    pass

# We'll keep only entries that contain CHIP-8 Emulator or Interactive Blackjack Simulator.
kept_entries = []
for entry in entries:
    if 'CHIP-8 Emulator' in entry:
        # Change date to 2026-04-28
        entry = entry.replace('<span class="entry-date">2026-04-30</span>', '<span class="entry-date">2026-04-28</span>')
        kept_entries.append(entry)
    elif 'Interactive Blackjack Simulator' in entry:
        # Change date to 2026-04-29
        entry = entry.replace('<span class="entry-date">2026-04-30</span>', '<span class="entry-date">2026-04-29</span>')
        kept_entries.append(entry)

# Now we have two entries.
# Build new middle: each entry separated by two newlines.
new_middle = '\n\n'.join(kept_entries)

# Replace the middle
new_html = html[:match.start(2)] + new_middle + html[match.end(2):]

with open('index.html', 'w') as f:
    f.write(new_html)

print("Updated index.html with only CHIP-8 Emulator and Interactive Blackjack Simulator, dates updated.")
