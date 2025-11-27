# -*- coding: utf-8 -*-
"""
Script para importar Naturezas Orçamentárias da API TOTVS.
"""
import requests
from requests.auth import HTTPBasicAuth
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_v2_pure import Base_V2, Company_V2, BudgetaryNature_V2

# Configuração da API
HOST = "http://192.168.18.9:8051"
USER = "INTEGRA_INOVAI"
PWD = "INOVAI.LAB"
ENDPOINT = "/api/framework/v1/financialBudgetaryNatures" # Endpoint provável

# Configuração do Banco
DATABASE_V2_PATH = 'instance/financial_data_v2.db'
engine_v2 = create_engine(f'sqlite:///{DATABASE_V2_PATH}', echo=False)
Session_v2 = sessionmaker(bind=engine_v2)
session_v2 = Session_v2()

def import_natures():
    print(f"🚀 Iniciando importação de Naturezas Orçamentárias...")
    
    # Cria a tabela se não existir
    Base_V2.metadata.create_all(engine_v2)
    
    # Busca empresas para iterar (ou usa a padrão 4)
    companies = session_v2.query(Company_V2).all()
    if not companies:
        print("❌ Nenhuma empresa encontrada no banco V2. Rode a migração primeiro.")
        return

    auth = HTTPBasicAuth(USER, PWD)
    
    for company in companies:
        print(f"📡 Buscando naturezas para empresa {company.code}...")
        
        params = {
            "companyId": company.code,
            "pageSize": 1000
        }
        
        # Lista de endpoints para tentar
        endpoints = [
            "/api/mov/v1/FinancialBudgetaryNatures", # Endpoint fornecido pelo usuário
            "/api/framework/v1/financialBudgetaryNatures",
            "/api/backoffice/v1/financialBudgetaryNatures",
            "/api/financial/v1/financialBudgetaryNatures",
            "/api/v1/financialBudgetaryNatures"
        ]
        
        success = False
        response = None
        
        for endpoint in endpoints:
            url = f"{HOST}{endpoint}"
            print(f"  🔄 Tentando: {url}")
            
            try:
                # Tenta filtrar por nature=394 como solicitado para debug, mas vamos trazer tudo para popular o banco
                # Se a API suportar OData, poderíamos usar $filter=internalId eq 394
                response = requests.get(url, auth=auth, params=params, timeout=30)
                
                if response.status_code == 200:
                    print(f"  ✅ Sucesso no endpoint: {endpoint}")
                    success = True
                    break
                elif response.status_code == 404:
                    continue
                else:
                    print(f"  ❌ Erro API {response.status_code}: {response.text}")
            except Exception as e:
                print(f"  ❌ Erro de conexão: {e}")
        
        if not success:
            print("  ❌ Falha: Nenhum endpoint funcionou.")
            continue
            
        try:
            data = response.json()
            items = data.get('items', []) if isinstance(data, dict) else data
            
            print(f"  ✅ {len(items)} naturezas encontradas.")
            
            count = 0
            for item in items:
                code = item.get('code') or item.get('natureCode')
                desc = item.get('description') or item.get('name')
                
                if not code:
                    continue
                    
                # Verifica se já existe
                nature = session_v2.query(BudgetaryNature_V2).filter_by(
                    company_id=company.id, 
                    code=code
                ).first()
                
                if not nature:
                    nature = BudgetaryNature_V2(
                        company_id=company.id,
                        code=code,
                        description=desc
                    )
                    session_v2.add(nature)
                    count += 1
                elif nature.description != desc:
                    nature.description = desc
                    count += 1
            
            session_v2.commit()
            print(f"  💾 {count} naturezas importadas/atualizadas.")
            
        except Exception as e:
            print(f"  ❌ Erro ao processar dados: {e}")

    print("\n✅ Importação concluída!")

if __name__ == "__main__":
    import_natures()
