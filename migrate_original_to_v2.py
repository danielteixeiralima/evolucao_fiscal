# -*- coding: utf-8 -*-
"""
Script de migração de dados do banco original (V1) para o novo banco normalizado (V2).
Lê diretamente do arquivo sqlite 'financial_data.db' e insere em 'financial_data_v2.db'.
"""
import sqlite3
import json
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_v2_pure import (
    Base_V2, Company_V2, Branch_V2, CostCenter_V2, Product_V2,
    CustomerVendor_V2, FinancialMovement_V2, MovementItem_V2,
    CostCenterApportionment_V2
)

# Configuração dos bancos
SOURCE_DB = 'instance/financial_data.db'
TARGET_DB = 'instance/financial_data_v2.db'

# Verifica se o banco de origem existe
if not os.path.exists(SOURCE_DB):
    print(f"❌ Banco de origem não encontrado: {SOURCE_DB}")
    # Tenta na raiz se não estiver em instance
    if os.path.exists('financial_data.db'):
        SOURCE_DB = 'financial_data.db'
        print(f"✅ Encontrado na raiz: {SOURCE_DB}")
    else:
        exit(1)

# Configura conexão com banco V2 (Destino)
engine_v2 = create_engine(f'sqlite:///{TARGET_DB}', echo=False)
Session_v2 = sessionmaker(bind=engine_v2)
session_v2 = Session_v2()

# Cache para evitar queries repetidas
cache = {
    'companies': {},      # code -> Company_V2
    'branches': {},       # (company_id, code) -> Branch_V2
    'cost_centers': {},   # (company_id, code) -> CostCenter_V2
    'products': {},       # (company_id, code) -> Product_V2
    'customer_vendors': {} # (company_id, code) -> CustomerVendor_V2
}

def get_col_idx(cursor, col_name):
    """Retorna o índice da coluna pelo nome"""
    return [d[0] for d in cursor.description].index(col_name)

def parse_json(value):
    """Faz parse de string JSON com segurança"""
    if not value:
        return []
    try:
        return json.loads(value)
    except:
        return []

def parse_date(value):
    """Converte string de data para objeto datetime"""
    if not value:
        return None
    try:
        # Tenta formato ISO com timezone
        return datetime.fromisoformat(value)
    except:
        try:
            # Tenta formato YYYY-MM-DD HH:MM:SS
            return datetime.strptime(value.split('.')[0], '%Y-%m-%d %H:%M:%S')
        except:
            return None

def get_or_create_company(code, name):
    if not code:
        code = "UNKNOWN"
    
    if code in cache['companies']:
        return cache['companies'][code]
    
    company = session_v2.query(Company_V2).filter_by(code=code).first()
    if not company:
        company = Company_V2(code=code, name=name or f"Empresa {code}")
        session_v2.add(company)
        session_v2.flush()
    
    cache['companies'][code] = company
    return company

def get_or_create_branch(company, code, name):
    if not code:
        code = "UNKNOWN"
        
    key = (company.id, code)
    if key in cache['branches']:
        return cache['branches'][key]
    
    branch = session_v2.query(Branch_V2).filter_by(company_id=company.id, code=code).first()
    if not branch:
        branch = Branch_V2(company_id=company.id, code=code, name=name or f"Filial {code}")
        session_v2.add(branch)
        session_v2.flush()
    
    cache['branches'][key] = branch
    return branch

def get_or_create_customer_vendor(company, code, name, cnpj):
    if not code:
        return None
        
    key = (company.id, code)
    if key in cache['customer_vendors']:
        return cache['customer_vendors'][key]
    
    cv = session_v2.query(CustomerVendor_V2).filter_by(company_id=company.id, code=code).first()
    if not cv:
        cv = CustomerVendor_V2(company_id=company.id, code=code, name=name, cnpj=cnpj)
        session_v2.add(cv)
        session_v2.flush()
    
    cache['customer_vendors'][key] = cv
    return cv

def get_or_create_product(company, code, name):
    if not code:
        return None
        
    key = (company.id, code)
    if key in cache['products']:
        return cache['products'][key]
    
    product = session_v2.query(Product_V2).filter_by(company_id=company.id, code=code).first()
    if not product:
        product = Product_V2(company_id=company.id, code=code, name=name)
        session_v2.add(product)
        session_v2.flush()
    
    cache['products'][key] = product
    return product

def get_or_create_cost_center(company, code, name):
    if not code:
        return None
        
    key = (company.id, code)
    if key in cache['cost_centers']:
        return cache['cost_centers'][key]
    
    cc = session_v2.query(CostCenter_V2).filter_by(company_id=company.id, code=code).first()
    if not cc:
        cc = CostCenter_V2(company_id=company.id, code=code, name=name)
        session_v2.add(cc)
        session_v2.flush()
    
    cache['cost_centers'][key] = cc
    return cc

def migrate():
    print(f"🚀 Iniciando migração de {SOURCE_DB} para {TARGET_DB}...")
    
    # Conecta ao banco de origem
    conn = sqlite3.connect(SOURCE_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Limpa banco de destino (opcional, mas bom para garantir consistência no teste)
    print("🗑️  Limpando banco de destino...")
    Base_V2.metadata.drop_all(engine_v2)
    Base_V2.metadata.create_all(engine_v2)
    
    # Busca movimentos
    print("📦 Lendo movimentos do banco original...")
    cursor.execute("SELECT * FROM financial_movement")
    rows = cursor.fetchall()
    print(f"📋 Encontrados {len(rows)} movimentos para migrar.")
    
    count = 0
    for row in rows:
        try:
            # Dados básicos
            empresa_code = str(row['company_id']) # V1 usa company_id como código as vezes, ou empresa_code
            if row['empresa_code']:
                empresa_code = str(row['empresa_code'])
            
            filial_code = str(row['branch_id'])
            if row['filial_code']:
                filial_code = str(row['filial_code'])
            
            # Cria/Obtém Empresa e Filial
            company = get_or_create_company(empresa_code, row['empresa_nome'])
            branch = get_or_create_branch(company, filial_code, row['filial_nome'])
            
            # Cliente/Fornecedor
            cv = get_or_create_customer_vendor(
                company, 
                row['customer_vendor_code'], 
                row['customer_vendor_name'], 
                row['customer_vendor_cnpj']
            )
            
            # Cria Movimento V2
            mov_v2 = FinancialMovement_V2(
                internal_id=row['internal_id'],
                movement_id=row['movement_id'],
                company_id=company.id,
                branch_id=branch.id,
                customer_vendor_id=cv.id if cv else None,
                number=str(row['number']) if row['number'] else None,
                series=row['series'],
                movement_type_code=row['movement_type_code'],
                type=row['type'],
                status=row['status'],
                date=parse_date(row['date']),
                gross_value=row['gross_value'],
                net_value=row['net_value'],
                warehouse_code=row['warehouse_code'],
                observation=row['observation']
            )
            session_v2.add(mov_v2)
            session_v2.flush()
            
            # Migra Itens (JSON)
            items_json = parse_json(row['movement_items'])
            for item_data in items_json:
                prod_code = item_data.get('productCode')
                prod_name = item_data.get('productName') or item_data.get('name')
                
                product = get_or_create_product(company, prod_code, prod_name)
                
                cc_data = item_data.get('costCenter') or {}
                cc_code = cc_data.get('costCenterCode')
                cc_name = cc_data.get('costCenterName')
                cc = get_or_create_cost_center(company, cc_code, cc_name)
                
                item_v2 = MovementItem_V2(
                    movement_id=mov_v2.id,
                    product_id=product.id if product else None,
                    cost_center_id=cc.id if cc else None,
                    sequential_number=item_data.get('sequentialNumber'),
                    quantity=item_data.get('quantity', 0),
                    unit_price=item_data.get('unitPrice', 0),
                    total_value=item_data.get('totalValue', 0),
                    original_data=json.dumps(item_data) # Salva o JSON original completo
                )
                session_v2.add(item_v2)
            
            # Migra Rateios (JSON)
            app_json = parse_json(row['cost_center_apportionments'])
            for app_data in app_json:
                cc_code = app_data.get('costCenterCode')
                cc_name = app_data.get('costCenterName')
                cc = get_or_create_cost_center(company, cc_code, cc_name)
                
                if cc:
                    app_v2 = CostCenterApportionment_V2(
                        movement_id=mov_v2.id,
                        cost_center_id=cc.id,
                        value=app_data.get('value', 0) or app_data.get('amount', 0)
                    )
                    session_v2.add(app_v2)
            
            count += 1
            if count % 50 == 0:
                session_v2.commit()
                print(f"  ... {count} movimentos migrados")
                
        except Exception as e:
            print(f"❌ Erro ao migrar movimento ID {row['id']}: {e}")
            session_v2.rollback()
    
    session_v2.commit()
    conn.close()
    
    print(f"\n✅ Migração concluída! {count} movimentos migrados com sucesso.")
    print(f"📊 Dados no banco V2:")
    print(f"  • Empresas: {session_v2.query(Company_V2).count()}")
    print(f"  • Filiais: {session_v2.query(Branch_V2).count()}")
    print(f"  • Movimentos: {session_v2.query(FinancialMovement_V2).count()}")

if __name__ == "__main__":
    migrate()
