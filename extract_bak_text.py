import re
import io
import sys

# Set default stdout encoding to utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open("templates/dashboard/admin_print_batch_cards.html.bak", "r", encoding="utf-8") as f:
    content = f.read()
    # Extract small text pieces, ignoring large base64
    text_nodes = re.findall(r'>([^<]+)<', content)
    for txt in text_nodes:
        txt = txt.strip()
        if txt and len(txt) < 200:  # only short bits of text
            print(txt)
