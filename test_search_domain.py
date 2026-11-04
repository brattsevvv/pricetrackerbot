import httpx
import re

r = httpx.get("https://js.klevu.com/klevu-js-v1/js/klevu-webstore.js")
for m in re.finditer(r'klevu_searchDomain', r.text):
    start = max(0, m.start() - 60)
    end = min(len(r.text), m.end() + 100)
    print(r.text[start:end])
    print("---")
