"""
Script de teste para verificar se a conversão de natureza orçamentária está funcionando
"""
import sys
import os

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configura o Flask app
os.environ['DATABASE_URL'] = 'sqlite:///instance/financial_data.db'

from app import create_app
from models import FinancialMovement
from routes import MovementAdapter

app = create_app()

with app.app_context():
    # Busca um movimento qualquer
    movement = FinancialMovement.query.first()
    
    if not movement:
        print("❌ Nenhum movimento encontrado no banco de dados")
        sys.exit(1)
    
    print(f"✅ Movimento encontrado: {movement.internal_id}")
    print(f"   Empresa: {movement.company.name if movement.company else 'N/A'}")
    print(f"   Número de itens: {len(movement.items)}")
    print("-" * 80)
    
    # Cria o adapter
    adapter = MovementAdapter(movement)
    
    # Busca os itens
    items = adapter.get_json_field('movement_items')
    
    print(f"📦 Itens processados: {len(items)}")
    print("-" * 80)
    
    for i, item in enumerate(items, 1):
        print(f"\n🔹 Item {i}:")
        print(f"   Produto: {item.get('name', 'N/A')}")
        
        # Verifica ambos os campos
        bugdet_code = item.get('bugdetNatureCode')
        budget_code = item.get('budgetNatureCode')
        
        print(f"   bugdetNatureCode: {bugdet_code}")
        print(f"   budgetNatureCode: {budget_code}")
        
        if bugdet_code and len(bugdet_code) > 20:
            print(f"   ✅ Descrição encontrada (bugdet): {bugdet_code}")
        elif budget_code and len(budget_code) > 20:
            print(f"   ✅ Descrição encontrada (budget): {budget_code}")
        elif bugdet_code or budget_code:
            print(f"   ⚠️  Ainda mostrando código: {bugdet_code or budget_code}")
        else:
            print(f"   ℹ️  Sem natureza orçamentária")
