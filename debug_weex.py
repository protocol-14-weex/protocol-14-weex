import requests
url = "https://api-contract.weex.com/capi/v2/time"
try:
    print(f"GET {url}")
    r = requests.get(url, timeout=10)
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
