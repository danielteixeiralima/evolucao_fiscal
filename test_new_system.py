# -*- coding: utf-8 -*-
"""
Script de teste para validar a importação da API.
Este script cria as tabelas e testa a importação com um pequeno conjunto de dados.
"""
from app import create_app, db
from models_new import Company, Branch, CostCenter, FinancialMovement
from api_importer import TOTVSAPIImporter

def test_database_creation():
    """Testa a criação das tabelas no banco"""
    print("\n" + "="*72)
    print("🧪 Teste 1: Criação das Tabelas")
    print("="*72)
    
    app = create_app()
    
    with app.app_context():
        # Cria todas as tabelas
        print("📦 Criando tabelas...")
        db.create_all()
        print("✅ Tabelas criadas com sucesso!")
        
        # Lista as tabelas criadas
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"\n📋 Tabelas no banco ({len(tables)}):")
        for table in sorted(tables):
            print(f"  • {table}")
        
        return True

def test_entity_cache():
    """Testa o cache de entidades"""
    print("\n" + "="*72)
    print("🧪 Teste 2: Cache de Entidades")
    print("="*72)
    
    app = create_app()
    
    with app.app_context():
        from api_importer import EntityCache
        
        cache = EntityCache()
        
        # Testa criação de empresa
        print("\n📝 Testando criação de empresa...")
        company = cache.get_or_create_company("4", "Empresa Teste")
        print(f"  ✅ Empresa criada: {company}")
        
        # Testa criação de filial
        print("\n📝 Testando criação de filial...")
        branch = cache.get_or_create_branch(company, "17", "Filial Teste")
        print(f"  ✅ Filial criada: {branch}")
        
        # Testa criação de centro de custo
        print("\n📝 Testando criação de centro de custo...")
        cc = cache.get_or_create_cost_center(company, "01.001", "Centro de Custo Teste")
        print(f"  ✅ Centro de Custo criado: {cc}")
        
        # Verifica que o cache está funcionando (não cria duplicatas)
        print("\n📝 Testando cache (não deve criar duplicatas)...")
        company2 = cache.get_or_create_company("4", "Empresa Teste 2")
        assert company.id == company2.id, "Cache não está funcionando!"
        print(f"  ✅ Cache funcionando: mesma empresa retornada")
        
        db.session.commit()
        
        # Verifica no banco
        print("\n📝 Verificando dados no banco...")
        companies = Company.query.all()
        branches = Branch.query.all()
        cost_centers = CostCenter.query.all()
        
        print(f"  • Empresas: {len(companies)}")
        print(f"  • Filiais: {len(branches)}")
        print(f"  • Centros de Custo: {len(cost_centers)}")
        
        return True

def test_api_connection():
    """Testa a conexão com a API"""
    print("\n" + "="*72)
    print("🧪 Teste 3: Conexão com a API")
    print("="*72)
    
    from api_importer import _safe_request, HOST, MOV_ENDPOINT
    
    print(f"\n📡 Testando conexão com {HOST}{MOV_ENDPOINT}...")
    
    # Testa uma requisição simples
    url = f"{HOST}{MOV_ENDPOINT}"
    params = {"page": 1, "pageSize": 1}
    
    r, exc = _safe_request("GET", url, params=params)
    
    if r and r.status_code == 200:
        print(f"  ✅ Conexão OK! Status: {r.status_code}")
        try:
            data = r.json()
            items = data.get('items', [])
            print(f"  ✅ API respondeu com {len(items)} item(ns)")
            return True
        except Exception as e:
            print(f"  ⚠️ Erro ao parsear JSON: {e}")
            return False
    else:
        print(f"  ❌ Erro na conexão! Status: {r.status_code if r else 'N/A'}")
        if exc:
            print(f"  ❌ Exception: {exc}")
        return False

def run_all_tests():
    """Executa todos os testes"""
    print("\n" + "="*72)
    print("🚀 INICIANDO TESTES DO SISTEMA")
    print("="*72)
    
    results = []
    
    # Teste 1: Criação das tabelas
    try:
        result = test_database_creation()
        results.append(("Criação das Tabelas", result))
    except Exception as e:
        print(f"\n❌ Erro no Teste 1: {e}")
        results.append(("Criação das Tabelas", False))
    
    # Teste 2: Cache de entidades
    try:
        result = test_entity_cache()
        results.append(("Cache de Entidades", result))
    except Exception as e:
        print(f"\n❌ Erro no Teste 2: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Cache de Entidades", False))
    
    # Teste 3: Conexão com API
    try:
        result = test_api_connection()
        results.append(("Conexão com API", result))
    except Exception as e:
        print(f"\n❌ Erro no Teste 3: {e}")
        results.append(("Conexão com API", False))
    
    # Resumo
    print("\n" + "="*72)
    print("📊 RESUMO DOS TESTES")
    print("="*72)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"  {status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for _, r in results if r)
    
    print(f"\n  Total: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 Todos os testes passaram! Sistema pronto para uso.")
    else:
        print("\n⚠️ Alguns testes falharam. Verifique os erros acima.")
    
    print("="*72 + "\n")

if __name__ == "__main__":
    run_all_tests()
