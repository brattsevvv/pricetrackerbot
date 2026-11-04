import httpx

# Test Klevu V2 search
params = {
    "apiKey": "klevu-15488592134928913",
    "q": "proteiini",
}
for host in ["eucs.ksearchnet.com", "eucs2.ksearchnet.com", "eucs3.ksearchnet.com", "eucs4.ksearchnet.com"]:
    try:
        r = httpx.get(f"https://{host}/cs/v2/search", params=params, timeout=5.0)
        print(host, "->", r.status_code, r.text[:300])
    except Exception as e:
        print(host, "err:", e)
