import httpx
import re

url = "https://www.tokmanni.fi/static/version1793103710/_cache/merged/58fa6f0ef256224c3a7bae0906c895ef.min.js"
print("Downloading merged js...")
r = httpx.get(url, timeout=30.0)
print("Length:", len(r.text))
for m in re.finditer(r'(klevu_server_url|cloudSearchURL|ksearchnet|api\.klevu|\.klevu\.com)', r.text, re.IGNORECASE):
    start = max(0, m.start() - 50)
    end = min(len(r.text), m.end() + 100)
    print(r.text[start:end])
