import requests
from requests.auth import HTTPBasicAuth

# Test API call with auth
url = "http://192.168.18.9:8051/api/mov/v1/FinancialBudgetaryNatures"
code = "02.11.01.013"
params = {"$filter": f"code eq '{code}'"}
auth = HTTPBasicAuth("INTEGRA_INOVAI", "INOVAI.LAB")

print(f"URL: {url}")
print(f"Params: {params}")

response = requests.get(url, params=params, auth=auth, timeout=10)

print(f"\nStatus Code: {response.status_code}")
print(f"Final URL: {response.url}")
print(f"\nResponse:")
print(response.text)

if response.status_code == 200:
    data = response.json()
    print(f"\nParsed JSON type: {type(data)}")
    print(f"Data: {data}")
    
    if isinstance(data, dict) and 'items' in data:
        print(f"\nItems count: {len(data['items'])}")
        if len(data['items']) > 0:
            print(f"First item description: {data['items'][0].get('description')}")
    elif isinstance(data, list):
        print(f"\nList length: {len(data)}")
        if len(data) > 0:
            print(f"First item description: {data[0].get('description')}")
