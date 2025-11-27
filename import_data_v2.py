# -*- coding: utf-8 -*-
"""
Script simplificado para importar dados da API usando os novos modelos.
Este script importa diretamente sem depender do app.py.
"""
import argparse
from datetime import datetime
from dateutil import tz

# Importa apenas o necessário
from api_importer import TOTVSAPIImporter

def main():
    parser = argparse.ArgumentParser(description="Importa movimentos da API TOTVS")
    parser.add_argument("--inicio", required=True, help="Data inicial (YYYY-MM-DD)")
    parser.add_argument("--fim", required=True, help="Data final (YYYY-MM-DD)")
    parser.add_argument("--empresa", required=True, help="Código da empresa")
    parser.add_argument("--filial", required=True, help="Código da filial")
    parser.add_argument("--page-size", type=int, default=50, help="Itens por página")
    parser.add_argument("--max-pages", type=int, default=10, help="Máximo de páginas")
    
    args = parser.parse_args()
    
    print("\n" + "="*72)
    print("🚀 IMPORTADOR DE DADOS - NOVA ESTRUTURA")
    print("="*72)
    print(f"\n📅 Período: {args.inicio} até {args.fim}")
    print(f"🏢 Empresa: {args.empresa}")
    print(f"🏪 Filial: {args.filial}")
    print(f"📄 Page Size: {args.page_size}")
    print(f"📊 Max Pages: {args.max_pages}")
    
    # Cria o app Flask
    from app import create_app, db
    app = create_app()
    
    with app.app_context():
        # Cria as tabelas novas (com sufixo _v2)
        print("\n📦 Criando tabelas novas...")
        
        # Importa os modelos novos aqui dentro do contexto
        from models_new import (
            Company, Branch, CostCenter, Product, CustomerVendor,
            FinancialMovement, MovementItem, MovementPayment,
            CostCenterApportionment
        )
        
        # Cria apenas as tabelas novas
        db.create_all()
        
        # Lista as tabelas
        inspector = db.inspect(db.engine)
        tables_v2 = [t for t in inspector.get_table_names() if '_v2' in t]
        print(f"✅ Tabelas novas criadas: {len(tables_v2)}")
        for table in sorted(tables_v2):
            print(f"  • {table}")
        
        # Executa a importação
        print("\n🔄 Iniciando importação...")
        importer = TOTVSAPIImporter()
        
        try:
            importer.import_movements(
                start_date=args.inicio,
                end_date=args.fim,
                company_code=args.empresa,
                branch_code=args.filial,
                page_size=args.page_size,
                max_pages=args.max_pages
            )
            
            print("\n✅ Importação concluída com sucesso!")
            
            # Mostra estatísticas
            print("\n📊 Dados importados:")
            print(f"  • Empresas: {Company.query.count()}")
            print(f"  • Filiais: {Branch.query.count()}")
            print(f"  • Centros de Custo: {CostCenter.query.count()}")
            print(f"  • Produtos: {Product.query.count()}")
            print(f"  • Movimentos: {FinancialMovement.query.count()}")
            print(f"  • Itens: {MovementItem.query.count()}")
            print(f"  • Rateios CC: {CostCenterApportionment.query.count()}")
            
        except KeyboardInterrupt:
            print("\n⚠️ Importação interrompida pelo usuário.")
        except Exception as e:
            print(f"\n❌ Erro na importação: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
