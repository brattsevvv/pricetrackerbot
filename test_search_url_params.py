import httpx
import re

r = httpx.get("https://js.klevu.com/klevu-js-v1/js/klevu-webstore.js")
for m in re.finditer(r'klevu_searchUrl\s*\+\s*"\?ticket="', r.text):
    start = max(0, m.start() - 20)
    end = min(len(r.text), m.end() + 400)
    print(r.text[start:end])
