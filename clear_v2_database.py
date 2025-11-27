# -*- coding: utf-8 -*-
"""
Script para limpar o banco V2 e importar movimentos específicos.
Tipos: 1.2.09, 1.2.10, 1.2.25, 1.2.01, 1.2.04, 1.2.91, 1.2.90
Empresas: 4, 147, 148, 149
"""
import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_v2_pure import Base_V2

# Configuração do banco V2
DATABASE_V2_PATH = 'instance/financial_data_v2.db'
engine_v2 = create_engine(f'sqlite:///{DATABASE_V2_PATH}', echo=False)
Session_v2 = sessionmaker(bind=engine_v2)

def clear_database():
    """Limpa todas as tabelas do banco V2"""
    print("\n🗑️  Limpando banco de dados V2...")
    
    # Dropa todas as tabelas
    Base_V2.metadata.drop_all(engine_v2)
    print("✅ Todas as tabelas foram removidas")
    
    # Recria as tabelas vazias
    Base_V2.metadata.create_all(engine_v2)
    print("✅ Tabelas recriadas (vazias)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Limpa o banco V2")
    parser.add_argument("--confirm", action="store_true", help="Confirma a limpeza")
    args = parser.parse_args()
    
    if not args.confirm:
        print("\n⚠️  ATENÇÃO: Este script vai DELETAR todos os dados do banco V2!")
        print("Para confirmar, execute:")
        print("  python clear_v2_database.py --confirm")
    else:
        clear_database()
        print("\n✅ Banco V2 limpo com sucesso!")
        print("\nAgora execute o importador com os filtros:")
        print("  python import_v2_filtered.py --inicio 2025-08-01 --fim 2025-11-26")
