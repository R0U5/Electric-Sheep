import re

with open('index.html', 'r') as f:
    html = f.read()

# Remove DAY-2026-04-29 section
html = re.sub(r'<!-- === DAY-2026-04-29-START === -->.*?<!-- === DAY-2026-04-29-END === -->', '', html, flags=re.DOTALL)
# Remove DAY-2026-04-28 section
html = re.sub(r'<!-- === DAY-2026-04-28-START === -->.*?<!-- === DAY-2026-04-28-END === -->', '', html, flags=re.DOTALL)

with open('index.html', 'w') as f:
    f.write(html)

print("Removed old DAY sections.")
