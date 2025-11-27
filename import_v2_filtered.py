# -*- coding: utf-8 -*-
"""
Importador V2 com filtros específicos.
Tipos de movimento: 1.2.09, 1.2.10, 1.2.25, 1.2.01, 1.2.04, 1.2.91, 1.2.90
Empresas (coligadas): 4, 147, 148, 149
"""
import argparse
import sys
from datetime import datetime
from dateutil import tz, parser as dtparser
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_v2_pure import (
    Base_V2, Company_V2, Branch_V2, CostCenter_V2, Product_V2,
    CustomerVendor_V2, FinancialMovement_V2, MovementItem_V2,
    CostCenterApportionment_V2
)
from api_importer import HOST, MOV_ENDPOINT, _safe_request, _norm_code, _date_iso

# Configuração
DATABASE_V2_PATH = 'instance/financial_data_v2.db'
engine_v2 = create_engine(f'sqlite:///{DATABASE_V2_PATH}', echo=False)
Session_v2 = sessionmaker(bind=engine_v2)

# FILTROS ESPECÍFICOS
MOVEMENT_TYPES = ['1.2.09', '1.2.10', '1.2.25', '1.2.01', '1.2.04', '1.2.91', '1.2.90']
COMPANIES = ['4', '147', '148', '149']

class ImporterV2Filtered:
    def __init__(self, session):
        self.session = session
        self.cache = {'companies': {}, 'branches': {}, 'cost_centers': {}, 'products': {}, 'customer_vendors': {}}
        self.stats = {'movements': 0, 'items': 0, 'apportionments': 0, 'filtered_out': 0}
    
    def get_or_create_company(self, code, name=None):
        code = _norm_code(code)
        if code in self.cache['companies']:
            return self.cache['companies'][code]
        
        company = self.session.query(Company_V2).filter_by(code=code).first()
        if not company:
            company = Company_V2(code=code, name=name or f"Empresa {code}")
            self.session.add(company)
            self.session.flush()
            print(f"  ✅ Empresa criada: {company.code}")
        
        self.cache['companies'][code] = company
        return company
    
    def get_or_create_branch(self, company, code, name=None):
        key = (company.id, code)
        if key in self.cache['branches']:
            return self.cache['branches'][key]
        
        branch = self.session.query(Branch_V2).filter_by(company_id=company.id, code=code).first()
        if not branch:
            branch = Branch_V2(company_id=company.id, code=code, name=name or f"Filial {code}")
            self.session.add(branch)
            self.session.flush()
            print(f"  ✅ Filial criada: {branch.code}")
        
        self.cache['branches'][key] = branch
        return branch
    
    def get_or_create_cost_center(self, company, code, name):
        key = (company.id, code)
        if key in self.cache['cost_centers']:
            return self.cache['cost_centers'][key]
        
        cc = self.session.query(CostCenter_V2).filter_by(company_id=company.id, code=code).first()
        if not cc:
            cc = CostCenter_V2(company_id=company.id, code=code, name=name or f"CC {code}")
            self.session.add(cc)
            self.session.flush()
        
        self.cache['cost_centers'][key] = cc
        return cc
    
    def get_or_create_product(self, company, code, data):
        key = (company.id, code)
        if key in self.cache['products']:
            return self.cache['products'][key]
        
        product = self.session.query(Product_V2).filter_by(company_id=company.id, code=code).first()
        if not product:
            product = Product_V2(
                company_id=company.id,
                code=code,
                name=data.get('name'),
                fantasy_name=data.get('fantasyName'),
                measure_unit=data.get('measureUnitCode')
            )
            self.session.add(product)
            self.session.flush()
        
        self.cache['products'][key] = product
        return product
    
    def get_or_create_customer_vendor(self, company, code, name=None, cnpj=None):
        key = (company.id, code)
        if key in self.cache['customer_vendors']:
            return self.cache['customer_vendors'][key]
        
        cv = self.session.query(CustomerVendor_V2).filter_by(company_id=company.id, code=code).first()
        if not cv:
            cv = CustomerVendor_V2(company_id=company.id, code=code, name=name, cnpj=cnpj)
            self.session.add(cv)
            self.session.flush()
        
        self.cache['customer_vendors'][key] = cv
        return cv
    
    def parse_datetime(self, value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return dtparser.isoparse(value)
            except:
                return None
        return None
    
    def get_movements_page(self, page, page_size, odata_filter):
        url = f"{HOST}{MOV_ENDPOINT}"
        params = {"page": page, "pageSize": page_size}
        if odata_filter:
            params["$filter"] = odata_filter
        
        r, exc = _safe_request("GET", url, params=params)
        if not r or r.status_code >= 400:
            return [], r.status_code if r else -1
        
        try:
            j = r.json()
            return j.get("items", []) if isinstance(j, dict) else (j if isinstance(j, list) else []), r.status_code
        except:
            return [], r.status_code
    
    def should_import_movement(self, mov_data):
        """Verifica se o movimento deve ser importado baseado nos filtros"""
        movement_type = mov_data.get('movementTypeCode', '')
        
        # Verifica se o tipo de movimento está na lista
        if movement_type not in MOVEMENT_TYPES:
            return False
        
        return True
    
    def import_movement(self, data, company, branch):
        # Cliente/Fornecedor
        cv = None
        if data.get('customerVendorCode'):
            cv = self.get_or_create_customer_vendor(
                company, data['customerVendorCode'],
                data.get('customerVendorName'), data.get('customerVendorCNPJ')
            )
        
        # Movimento
        movement = FinancialMovement_V2(
            internal_id=data['internalId'],
            movement_id=data.get('movementId'),
            company_id=company.id,
            branch_id=branch.id,
            customer_vendor_id=cv.id if cv else None,
            number=data.get('number'),
            series=data.get('series'),
            movement_type_code=data.get('movementTypeCode'),
            type=data.get('type'),
            status=data.get('status'),
            date=self.parse_datetime(data.get('date')),
            gross_value=data.get('grossValue', 0.0),
            net_value=data.get('netValue', 0.0),
            warehouse_code=data.get('warehouseCode'),
            observation=data.get('observation'),
        )
        
        self.session.add(movement)
        self.session.flush()
        self.stats['movements'] += 1
        
        # Itens
        for item_data in data.get('movementItems', []):
            product = None
            if item_data.get('productCode'):
                product = self.get_or_create_product(company, item_data['productCode'], item_data)
            
            cc = None
            cc_data = item_data.get('costCenter', {})
            if cc_data.get('costCenterCode'):
                cc = self.get_or_create_cost_center(company, cc_data['costCenterCode'], cc_data.get('costCenterName', ''))
            
            item = MovementItem_V2(
                movement_id=movement.id,
                product_id=product.id if product else None,
                cost_center_id=cc.id if cc else None,
                sequential_number=item_data.get('sequentialNumber'),
                quantity=item_data.get('quantity', 0.0),
                unit_price=item_data.get('unitPrice', 0.0),
                total_value=item_data.get('totalValue', 0.0),
            )
            self.session.add(item)
            self.stats['items'] += 1
        
        # Rateios
        for app_data in data.get('costCenterApportionments', []):
            cc = self.get_or_create_cost_center(
                company,
                app_data['costCenterCode'],
                app_data.get('costCenterName', '')
            )
            
            app = CostCenterApportionment_V2(
                movement_id=movement.id,
                cost_center_id=cc.id,
                value=app_data.get('value', 0.0) or app_data.get('amount', 0.0),
            )
            self.session.add(app)
            self.stats['apportionments'] += 1
    
    def import_for_company(self, company_code, start_date, end_date, page_size=100, max_pages=1000):
        """Importa movimentos para uma empresa específica"""
        TZBR = tz.gettz("America/Sao_Paulo")
        dt_ini = datetime.strptime(start_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, tzinfo=TZBR)
        dt_fim = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=TZBR)
        
        print(f"\n{'='*72}")
        print(f"📊 Empresa {company_code}")
        print(f"{'='*72}")
        
        company = self.get_or_create_company(company_code)
        
        # Monta filtro OData (sem filtro de filial - pega todas)
        odata_filter = f"companyId eq {company_code} and date ge {_date_iso(dt_ini)} and date le {_date_iso(dt_fim)}"
        
        page = 1
        while page <= max_pages:
            print(f"  📄 Página {page}...", end=" ")
            movements_data, status = self.get_movements_page(page, page_size, odata_filter)
            
            if status >= 400 or not movements_data:
                print(f"Fim (status={status})")
                break
            
            print(f"{len(movements_data)} movimentos")
            
            imported_this_page = 0
            for mov_data in movements_data:
                try:
                    # Verifica se deve importar baseado no tipo
                    if not self.should_import_movement(mov_data):
                        self.stats['filtered_out'] += 1
                        continue
                    
                    # Obtém ou cria a filial
                    branch_code = str(mov_data.get('branchId', ''))
                    branch = self.get_or_create_branch(company, branch_code)
                    
                    self.import_movement(mov_data, company, branch)
                    imported_this_page += 1
                    
                    if self.stats['movements'] % 50 == 0:
                        self.session.commit()
                        print(f"    💾 {self.stats['movements']} movimentos importados...")
                
                except Exception as e:
                    print(f"    ⚠️ Erro: {e}")
                    self.session.rollback()
            
            self.session.commit()
            print(f"    ✅ {imported_this_page} importados desta página")
            
            if len(movements_data) < page_size:
                break
            page += 1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inicio", required=True, help="Data inicial (YYYY-MM-DD)")
    parser.add_argument("--fim", required=True, help="Data final (YYYY-MM-DD)")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=1000)
    args = parser.parse_args()
    
    print("\n" + "="*72)
    print("🔧 IMPORTADOR V2 - FILTRADO")
    print("="*72)
    print(f"\n📋 Filtros:")
    print(f"  • Tipos de movimento: {', '.join(MOVEMENT_TYPES)}")
    print(f"  • Empresas: {', '.join(COMPANIES)}")
    print(f"  • Período: {args.inicio} até {args.fim}")
    
    session = Session_v2()
    importer = ImporterV2Filtered(session)
    
    try:
        # Importa para cada empresa
        for company_code in COMPANIES:
            importer.import_for_company(
                company_code, args.inicio, args.fim,
                args.page_size, args.max_pages
            )
        
        print(f"\n{'='*72}")
        print(f"✅ Importação concluída!")
        print(f"{'='*72}")
        print(f"📊 Estatísticas:")
        print(f"  • Movimentos importados: {importer.stats['movements']}")
        print(f"  • Movimentos filtrados: {importer.stats['filtered_out']}")
        print(f"  • Itens: {importer.stats['items']}")
        print(f"  • Rateios: {importer.stats['apportionments']}")
        print(f"{'='*72}\n")
        
        print("\n📊 Dados no banco V2:")
        print(f"  • Empresas: {session.query(Company_V2).count()}")
        print(f"  • Filiais: {session.query(Branch_V2).count()}")
        print(f"  • Centros de Custo: {session.query(CostCenter_V2).count()}")
        print(f"  • Movimentos: {session.query(FinancialMovement_V2).count()}")
        print(f"  • Itens: {session.query(MovementItem_V2).count()}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrompido")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
    finally:
        session.close()

if __name__ == "__main__":
    main()
