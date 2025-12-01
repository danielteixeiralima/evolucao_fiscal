import requests
from requests.auth import HTTPBasicAuth
import json

# Configuração da API
TOTVS_API_BASE = "http://192.168.18.9:8051/api/mov/v1"
TOTVS_API_USER = "INTEGRA_INOVAI"
TOTVS_API_PWD = "INOVAI.LAB"
totvs_auth = HTTPBasicAuth(TOTVS_API_USER, TOTVS_API_PWD)

# Teste com o código que você forneceu
code = "02.11.01.013"
url = f"{TOTVS_API_BASE}/FinancialBudgetaryNatures"
filter_param = f"code eq '{code}'"
params = {"$filter": filter_param}

print(f"🔍 Testando API TOTVS para código: {code}")
print(f"URL: {url}")
print(f"Filter: {filter_param}")
print("-" * 80)

try:
    response = requests.get(url, params=params, auth=totvs_auth, timeout=10)
    
    print(f"Status Code: {response.status_code}")
    print(f"URL completa: {response.url}")
    print("-" * 80)
    
    if response.status_code == 200:
        data = response.json()
        print("Resposta JSON:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("-" * 80)
        
        # Testar diferentes formatos de resposta
        if isinstance(data, dict) and 'items' in data:
            print(f"✅ Formato: dict com 'items'")
            if len(data['items']) > 0:
                description = data['items'][0].get('description')
                print(f"✅ Description encontrada: {description}")
            else:
                print(f"❌ Lista 'items' está vazia")
        elif isinstance(data, list):
            print(f"✅ Formato: lista direta")
            if len(data) > 0:
                description = data[0].get('description')
                print(f"✅ Description encontrada: {description}")
            else:
                print(f"❌ Lista está vazia")
        else:
            print(f"❌ Formato desconhecido: {type(data)}")
    else:
        print(f"❌ Erro na requisição: {response.status_code}")
        print(f"Resposta: {response.text}")
        
except Exception as e:
    print(f"❌ Erro: {str(e)}")
    import traceback
    traceback.print_exc()
