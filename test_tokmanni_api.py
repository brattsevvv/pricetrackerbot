import httpx
import json
import re
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fi-FI,fi;q=0.9,en-US;q=0.8,en;q=0.7",
}

r = httpx.get("https://www.tokmanni.fi/search?q=proteiini", headers=headers, follow_redirects=True, timeout=15.0)
print("Tokmanni HTML status:", r.status_code, "Length:", len(r.text))
soup = BeautifulSoup(r.text, "html.parser")

# Look for embedded json data
for s in soup.find_all("script"):
    src = s.get("src", "")
    txt = s.string or ""
    if "api" in src.lower() or "search" in src.lower() or "klevu" in src.lower():
        print("Script src:", src)
    if "klevu" in txt.lower():
        print("Klevu in text!")
        m = re.findall(r'apiKey[\'":\s]+([^\'",\s]+)', txt)
        if m:
            print("API Key:", m)

# Search for any product urls or names in HTML
links = soup.find_all("a", href=lambda h: h and ("/tuote/" in h or "-64" in h))
print("Direct product links in HTML:", len(links))

# Check for Magento GraphQL or Rest API
print("Searching for magento or search API config in HTML...")
matches = re.findall(r'https?://[^\s"\'<>]*(?:api|search|graphql)[^\s"\'<>]*', r.text)
for m in set(matches[:15]):
    print("API url candidate:", m)
