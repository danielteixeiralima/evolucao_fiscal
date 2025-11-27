# -*- coding: utf-8 -*-
"""
Importador standalone para a nova estrutura V2.
Usa um banco de dados separado (financial_data_v2.db) para evitar conflitos.
"""
import argparse
import sys
from datetime import datetime
from dateutil import tz
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# Configuração do banco V2
DATABASE_V2_PATH = 'instance/financial_data_v2.db'
engine_v2 = create_engine(f'sqlite:///{DATABASE_V2_PATH}', echo=False)
Session_v2 = scoped_session(sessionmaker(bind=engine_v2))

# Importa os modelos V2
from models_new import (
    db, Company, Branch, CostCenter, Product, CustomerVendor,
    FinancialMovement, MovementItem, MovementPayment, MovementTax,
    CostCenterApportionment, DepartmentApportionment
)

# Importa funções auxiliares
from api_importer import (
    HOST, MOV_ENDPOINT, _safe_request, _norm_code, _date_iso
)


class StandaloneEntityCache:
    """Cache para evitar duplicação de empresas, filiais, centros de custo, etc."""
    
    def __init__(self, session):
        self.session = session
        self.companies = {}
        self.branches = {}
        self.cost_centers = {}
        self.products = {}
        self.customer_vendors = {}
    
    def get_or_create_company(self, code: str, name: str = None):
        code = _norm_code(code)
        if code in self.companies:
            return self.companies[code]
        
        company = self.session.query(Company).filter_by(code=code).first()
        if not company:
            company = Company(code=code, name=name or f"Empresa {code}")
            self.session.add(company)
            self.session.flush()
            print(f"  ✅ Empresa criada: {company.code} - {company.name}")
        
        self.companies[code] = company
        return company
    
    def get_or_create_branch(self, company, code: str, name: str = None):
        code = str(code).strip()
        key = (company.id, code)
        if key in self.branches:
            return self.branches[key]
        
        branch = self.session.query(Branch).filter_by(company_id=company.id, code=code).first()
        if not branch:
            branch = Branch(company_id=company.id, code=code, name=name or f"Filial {code}")
            self.session.add(branch)
            self.session.flush()
            print(f"  ✅ Filial criada: {branch.code} - {branch.name}")
        
        self.branches[key] = branch
        return branch
    
    def get_or_create_cost_center(self, company, code: str, name: str):
        code = str(code).strip()
        key = (company.id, code)
        if key in self.cost_centers:
            return self.cost_centers[key]
        
        cc = self.session.query(CostCenter).filter_by(company_id=company.id, code=code).first()
        if not cc:
            cc = CostCenter(company_id=company.id, code=code, name=name or f"CC {code}")
            self.session.add(cc)
            self.session.flush()
            print(f"  ✅ Centro de Custo criado: {cc.code} - {cc.name}")
        
        self.cost_centers[key] = cc
        return cc
    
    def get_or_create_product(self, company, code: str, product_data: dict):
        code = str(code).strip()
        key = (company.id, code)
        if key in self.products:
            return self.products[key]
        
        product = self.session.query(Product).filter_by(company_id=company.id, code=code).first()
        if not product:
            product = Product(
                company_id=company.id,
                code=code,
                product_id=product_data.get('productId'),
                name=product_data.get('name'),
                fantasy_name=product_data.get('fantasyName'),
                measure_unit=product_data.get('measureUnitCode')
            )
            self.session.add(product)
            self.session.flush()
        
        self.products[key] = product
        return product
    
    def get_or_create_customer_vendor(self, company, code: str, name: str = None, cnpj: str = None):
        code = str(code).strip()
        key = (company.id, code)
        if key in self.customer_vendors:
            return self.customer_vendors[key]
        
        cv = self.session.query(CustomerVendor).filter_by(company_id=company.id, code=code).first()
        if not cv:
            cv = CustomerVendor(company_id=company.id, code=code, name=name, cnpj=cnpj)
            self.session.add(cv)
            self.session.flush()
        
        self.customer_vendors[key] = cv
        return cv


class StandaloneImporter:
    """Importador que usa banco separado"""
    
    def __init__(self, session):
        self.session = session
        self.cache = StandaloneEntityCache(session)
        self.stats = {'movements': 0, 'items': 0, 'payments': 0, 'taxes': 0, 'apportionments': 0}
    
    def _get_movements_page(self, page, page_size, odata_filter):
        url = f"{HOST}{MOV_ENDPOINT}"
        params = {"page": max(1, page), "pageSize": max(1, page_size)}
        if odata_filter:
            params["$filter"] = odata_filter
        
        r, exc = _safe_request("GET", url, params=params)
        if not r or r.status_code >= 400:
            return [], r.status_code if r else -1
        
        try:
            j = r.json()
            items = j.get("items", []) if isinstance(j, dict) else (j if isinstance(j, list) else [])
            return items, r.status_code
        except:
            return [], r.status_code
    
    def _parse_datetime(self, value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                from dateutil import parser as dtparser
                return dtparser.isoparse(value)
            except:
                return None
        return None
    
    def _import_movement(self, mov_data, company, branch):
        # Cliente/Fornecedor
        customer_vendor = None
        cv_code = mov_data.get('customerVendorCode')
        if cv_code:
            customer_vendor = self.cache.get_or_create_customer_vendor(
                company, cv_code,
                name=mov_data.get('customerVendorName'),
                cnpj=mov_data.get('customerVendorCNPJ')
            )
        
        # Cria movimento
        movement = FinancialMovement(
            internal_id=mov_data.get('internalId'),
            movement_id=mov_data.get('movementId'),
            company_id=company.id,
            branch_id=branch.id,
            customer_vendor_id=customer_vendor.id if customer_vendor else None,
            number=mov_data.get('number'),
            series=mov_data.get('series'),
            movement_type_code=mov_data.get('movementTypeCode'),
            type=mov_data.get('type'),
            status=mov_data.get('status'),
            date=self._parse_datetime(mov_data.get('date')),
            gross_value=mov_data.get('grossValue', 0.0),
            net_value=mov_data.get('netValue', 0.0),
            warehouse_code=mov_data.get('warehouseCode'),
            observation=mov_data.get('observation'),
        )
        
        self.session.add(movement)
        self.session.flush()
        self.stats['movements'] += 1
        
        # Importa itens
        for item_data in mov_data.get('movementItems', []):
            self._import_item(movement, company, item_data)
        
        # Importa rateios
        for app_data in mov_data.get('costCenterApportionments', []):
            self._import_apportionment(movement, company, app_data)
        
        return movement
    
    def _import_item(self, movement, company, item_data):
        product = None
        if item_data.get('productCode'):
            product = self.cache.get_or_create_product(company, item_data['productCode'], item_data)
        
        cost_center = None
        cc_data = item_data.get('costCenter', {})
        if cc_data.get('costCenterCode'):
            cost_center = self.cache.get_or_create_cost_center(
                company,
                cc_data['costCenterCode'],
                cc_data.get('costCenterName', f"CC {cc_data['costCenterCode']}")
            )
        
        item = MovementItem(
            movement_id=movement.id,
            product_id=product.id if product else None,
            cost_center_id=cost_center.id if cost_center else None,
            sequential_number=item_data.get('sequentialNumber'),
            quantity=item_data.get('quantity', 0.0),
            unit_price=item_data.get('unitPrice', 0.0),
            total_value=item_data.get('totalValue', 0.0),
        )
        
        self.session.add(item)
        self.stats['items'] += 1
    
    def _import_apportionment(self, movement, company, app_data):
        cost_center = self.cache.get_or_create_cost_center(
            company,
            app_data['costCenterCode'],
            app_data.get('costCenterName', f"CC {app_data['costCenterCode']}")
        )
        
        apportionment = CostCenterApportionment(
            movement_id=movement.id,
            cost_center_id=cost_center.id,
            value=app_data.get('value', 0.0) or app_data.get('amount', 0.0),
        )
        
        self.session.add(apportionment)
        self.stats['apportionments'] += 1
    
    def import_movements(self, start_date, end_date, company_code, branch_code, page_size=50, max_pages=1000):
        TZBR = tz.gettz("America/Sao_Paulo")
        dt_ini = datetime.strptime(start_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, tzinfo=TZBR)
        dt_fim = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=TZBR)
        
        print(f"\n{'='*72}")
        print(f"🚀 Importando movimentos da API TOTVS (V2)")
        print(f"{'='*72}")
        print(f"Período: {dt_ini.date()} até {dt_fim.date()}")
        print(f"Empresa: {company_code} | Filial: {branch_code}")
        
        company = self.cache.get_or_create_company(company_code)
        branch = self.cache.get_or_create_branch(company, branch_code)
        
        odata_filter = f"companyId eq {company_code} and branchId eq {branch_code} and date ge {_date_iso(dt_ini)} and date le {_date_iso(dt_fim)}"
        
        print(f"\n📡 Buscando movimentos...")
        
        page = 1
        while page <= max_pages:
            print(f"\n  📄 Página {page}...")
            movements_data, status = self._get_movements_page(page, page_size, odata_filter)
            
            if status >= 400 or not movements_data:
                print(f"  ✅ Fim dos dados (status={status})")
                break
            
            print(f"  ✅ {len(movements_data)} movimentos encontrados")
            
            for mov_data in movements_data:
                try:
                    self._import_movement(mov_data, company, branch)
                    if self.stats['movements'] % 10 == 0:
                        self.session.commit()
                        print(f"  💾 {self.stats['movements']} movimentos importados...")
                except Exception as e:
                    print(f"  ⚠️ Erro: {e}")
                    self.session.rollback()
            
            self.session.commit()
            
            if len(movements_data) < page_size:
                break
            page += 1
        
        print(f"\n{'='*72}")
        print(f"✅ Importação concluída!")
        print(f"📊 Movimentos: {self.stats['movements']} | Itens: {self.stats['items']} | Rateios: {self.stats['apportionments']}")
        print(f"{'='*72}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inicio", required=True)
    parser.add_argument("--fim", required=True)
    parser.add_argument("--empresa", required=True)
    parser.add_argument("--filial", required=True)
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--max-pages", type=int, default=1000)
    args = parser.parse_args()
    
    print("\n" + "="*72)
    print("🔧 IMPORTADOR V2 - BANCO SEPARADO")
    print("="*72)
    
    print("\n📦 Criando tabelas...")
    db.metadata.create_all(bind=engine_v2)
    print("✅ Tabelas criadas!")
    
    session = Session_v2()
    importer = StandaloneImporter(session)
    
    try:
        importer.import_movements(
            args.inicio, args.fim, args.empresa, args.filial,
            args.page_size, args.max_pages
        )
        
        print("\n📊 Dados no banco V2:")
        print(f"  • Empresas: {session.query(Company).count()}")
        print(f"  • Filiais: {session.query(Branch).count()}")
        print(f"  • Centros de Custo: {session.query(CostCenter).count()}")
        print(f"  • Movimentos: {session.query(FinancialMovement).count()}")
        print(f"  • Itens: {session.query(MovementItem).count()}")
        
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
