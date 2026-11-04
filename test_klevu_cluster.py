import httpx

for i in range(1, 35):
    domain = f"eucs{i}.ksearchnet.com" if i > 1 else "eucs.ksearchnet.com"
    url = f"https://{domain}/cloud-search/n-search/search?ticket=klevu-15488592134928913&term=proteiini"
    try:
        r = httpx.get(url, timeout=1.5)
        if r.status_code == 200:
            print("FOUND! Domain:", domain)
            data = r.json()
            print("Total found:", data.get("meta", {}).get("totalResultsFound"))
            for p in data.get("result", [])[:3]:
                print("-", p.get("name"), p.get("salePrice"), p.get("url"))
            break
        elif "webstore-not-found" not in r.text:
            print(domain, r.status_code, r.text[:100])
    except Exception as e:
        pass
