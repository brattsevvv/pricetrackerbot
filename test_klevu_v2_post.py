import httpx
import json

payload = {
    "context": {
        "apiKeys": ["klevu-15488592134928913"]
    },
    "recordQueries": [
        {
            "id": "search_products",
            "typeOfRequest": "SEARCH",
            "settings": {
                "query": {
                    "term": "proteiini"
                },
                "typeOfRecords": ["KLEVU_PRODUCT"],
                "limit": 5
            }
        }
    ]
}

headers = {
    "Content-Type": "application/json"
}

for host in ["eucs2.ksearchnet.com", "eucs.ksearchnet.com", "eucs29.ksearchnet.com", "api.ksearchnet.com"]:
    try:
        r = httpx.post(f"https://{host}/cs/v2/search", json=payload, headers=headers, timeout=5.0)
        print(host, "->", r.status_code)
        if r.status_code == 200:
            data = r.json()
            print("Response:", json.dumps(data, indent=2)[:500])
            break
        else:
            print("Error:", r.text[:200])
    except Exception as e:
        print(host, "err:", e)
