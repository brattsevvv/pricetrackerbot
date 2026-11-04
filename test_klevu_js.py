import httpx
import re

r = httpx.get("https://js.klevu.com/klevu-js-v1/js-1-1/klevu-landing.js")
for m in re.finditer(r'(createElement|jsonp|callback|protocol|\.src\s*=)', r.text, re.IGNORECASE):
    start = max(0, m.start() - 60)
    end = min(len(r.text), m.end() + 150)
    print(r.text[start:end])
    print("=" * 50)
