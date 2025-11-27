# -*- coding: utf-8 -*-
"""
Importador Movements - Usa modelos Flask-SQLAlchemy (models.py).
"""
import argparse
import sys
import json
from datetime import datetime
from dateutil import tz, parser as dtparser
from app import create_app, db
from models import (
    Company, Branch, CostCenter, Product, CustomerVendor, 
    FinancialMovement, MovementItem, CostCenterApportionment, BudgetaryNature
)

# Importa funções da API
from api_importer import HOST, MOV_ENDPOINT, _safe_request, _norm_code, _date_iso

class Importer:
    def __init__(self):
        self.cache = {'companies': {}, 'branches': {}, 'cost_centers': {}, 'products': {}, 'customer_vendors': {}}
        self.stats = {'movements': 0, 'items': 0, 'apportionments': 0}
    
    def get_or_create_company(self, code):
        code = _norm_code(code)
        if code in self.cache['companies']:
            return self.cache['companies'][code]
        
        company = Company.query.filter_by(code=code).first()
        if not company:
            company = Company(code=code, name=f"Empresa {code}")
            db.session.add(company)
            db.session.flush()
            print(f"  ✅ Empresa criada: {company.code}")
        
        self.cache['companies'][code] = company
        return company
    
    def get_or_create_branch(self, company, code):
        key = (company.id, code)
        if key in self.cache['branches']:
            return self.cache['branches'][key]
        
        branch = Branch.query.filter_by(company_id=company.id, code=code).first()
        if not branch:
            branch = Branch(company_id=company.id, code=code, name=f"Filial {code}")
            db.session.add(branch)
            db.session.flush()
            print(f"  ✅ Filial criada: {branch.code}")
        
        self.cache['branches'][key] = branch
        return branch
    
    def get_or_create_cost_center(self, company, code, name):
        key = (company.id, code)
        if key in self.cache['cost_centers']:
            return self.cache['cost_centers'][key]
        
        cc = CostCenter.query.filter_by(company_id=company.id, code=code).first()
        if not cc:
            cc = CostCenter(company_id=company.id, code=code, name=name or f"CC {code}")
            db.session.add(cc)
            db.session.flush()
        
        self.cache['cost_centers'][key] = cc
        return cc
    
    def get_or_create_product(self, company, code, data):
        key = (company.id, code)
        if key in self.cache['products']:
            return self.cache['products'][key]
        
        product = Product.query.filter_by(company_id=company.id, code=code).first()
        if not product:
            product = Product(
                company_id=company.id,
                code=code,
                name=data.get('name'),
                fantasy_name=data.get('fantasyName'),
                measure_unit=data.get('measureUnitCode')
            )
            db.session.add(product)
            db.session.flush()
        
        self.cache['products'][key] = product
        return product
    
    def get_or_create_customer_vendor(self, company, code, name=None, cnpj=None):
        key = (company.id, code)
        if key in self.cache['customer_vendors']:
            return self.cache['customer_vendors'][key]
        
        cv = CustomerVendor.query.filter_by(company_id=company.id, code=code).first()
        if not cv:
            cv = CustomerVendor(company_id=company.id, code=code, name=name, cnpj=cnpj)
            db.session.add(cv)
            db.session.flush()
        
        self.cache['customer_vendors'][key] = cv
        return cv
    
    def get_or_create_budgetary_nature(self, company, code, description=None):
        # Cache logic omitted for brevity, but could be added
        bn = BudgetaryNature.query.filter_by(company_id=company.id, code=code).first()
        if not bn:
            bn = BudgetaryNature(company_id=company.id, code=code, description=description)
            db.session.add(bn)
            db.session.flush()
        return bn

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
    
    def import_movement(self, data, company, branch):
        # Cliente/Fornecedor
        cv = None
        if data.get('customerVendorCode'):
            cv = self.get_or_create_customer_vendor(
                company, data['customerVendorCode'],
                data.get('customerVendorName'), data.get('customerVendorCNPJ')
            )
        
        # Movimento
        movement = FinancialMovement(
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
        
        db.session.add(movement)
        db.session.flush()
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
            
            # Import Budgetary Nature if present
            bn_code = item_data.get('bugdetNatureCode') or item_data.get('budgetNatureCode')
            if bn_code:
                self.get_or_create_budgetary_nature(company, bn_code, item_data.get('budgetNatureDescription'))

            item = MovementItem(
                movement_id=movement.id,
                product_id=product.id if product else None,
                cost_center_id=cc.id if cc else None,
                sequential_number=item_data.get('sequentialNumber'),
                quantity=item_data.get('quantity', 0.0),
                unit_price=item_data.get('unitPrice', 0.0),
                total_value=item_data.get('totalValue', 0.0),
                original_data=json.dumps(item_data) # Save original JSON for fidelity
            )
            db.session.add(item)
            self.stats['items'] += 1
        
        # Rateios
        for app_data in data.get('costCenterApportionments', []):
            cc = self.get_or_create_cost_center(
                company,
                app_data['costCenterCode'],
                app_data.get('costCenterName', '')
            )
            
            app = CostCenterApportionment(
                movement_id=movement.id,
                cost_center_id=cc.id,
                value=app_data.get('value', 0.0) or app_data.get('amount', 0.0),
            )
            db.session.add(app)
            self.stats['apportionments'] += 1
    
    def import_movements(self, start_date, end_date, company_code, branch_code, page_size=50, max_pages=1000):
        TZBR = tz.gettz("America/Sao_Paulo")
        dt_ini = datetime.strptime(start_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, tzinfo=TZBR)
        dt_fim = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=TZBR)
        
        print(f"\n{'='*72}")
        print(f"🚀 Importando da API TOTVS (Sistema Principal)")
        print(f"{'='*72}")
        print(f"Período: {dt_ini.date()} → {dt_fim.date()}")
        print(f"Empresa: {company_code} | Filial: {branch_code}")
        
        company = self.get_or_create_company(company_code)
        branch = self.get_or_create_branch(company, branch_code)
        
        odata_filter = f"companyId eq {company_code} and branchId eq {branch_code} and date ge {_date_iso(dt_ini)} and date le {_date_iso(dt_fim)}"
        
        print(f"\n📡 Buscando movimentos...")
        
        page = 1
        while page <= max_pages:
            print(f"\n  📄 Página {page}...")
            movements_data, status = self.get_movements_page(page, page_size, odata_filter)
            
            if status >= 400 or not movements_data:
                print(f"  ✅ Fim (status={status})")
                break
            
            print(f"  ✅ {len(movements_data)} movimentos")
            
            for mov_data in movements_data:
                try:
                    self.import_movement(mov_data, company, branch)
                    if self.stats['movements'] % 10 == 0:
                        db.session.commit()
                        print(f"  💾 {self.stats['movements']} importados...")
                except Exception as e:
                    print(f"  ⚠️ Erro: {e}")
                    db.session.rollback()
            
            db.session.commit()
            
            if len(movements_data) < page_size:
                break
            page += 1
        
        print(f"\n{'='*72}")
        print(f"✅ Concluído!")
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
    
    app = create_app()
    with app.app_context():
        print("\n" + "="*72)
        print("🔧 IMPORTADOR MOVEMENTS (MIGRADO)")
        print("="*72)
        
        print("\n📦 Criando tabelas (se necessário)...")
        db.create_all()
        print("✅ Tabelas verificadas!")
        
        importer = Importer()
        
        try:
            importer.import_movements(
                args.inicio, args.fim, args.empresa, args.filial,
                args.page_size, args.max_pages
            )
            
        except KeyboardInterrupt:
            print("\n⚠️ Interrompido")
            sys.exit(130)
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(2)

if __name__ == "__main__":
    main()
