# -*- coding: utf-8 -*-
"""
Importador de dados da API TOTVS para o banco de dados normalizado.
Baseado no Teste_1.py, mas ao invés de gerar Excel, popula o banco diretamente.
"""
import re
import sys
import os
import json
import time
import argparse
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import local, Lock

import requests
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dateutil import tz, parser as dtparser

# Importações do Flask/SQLAlchemy
from app import create_app, db
from models_new import (
    Company, Branch, CostCenter, Product, CustomerVendor,
    FinancialMovement, MovementItem, MovementPayment, MovementTax,
    CostCenterApportionment, DepartmentApportionment
)

# ==============================
# CONFIG DE CONEXÃO
# ==============================
HOST = "http://192.168.18.9:8051"
USER = "INTEGRA_INOVAI"
PWD = "INOVAI.LAB"
auth = HTTPBasicAuth(USER, PWD)

MOV_ENDPOINT = "/api/mov/v1/movements"

# ==============================
# AJUSTES DE REDE / TOLERÂNCIA
# ==============================
MAX_PAGES_PER_BRANCH = 1_000_000
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 45
ADAPTER_RETRIES = 3
MANUAL_RETRIES = 2
BACKOFF_BASE = 0.5
DEBUG_VERBOSE = True

DATE_FIELD_HINTS = [
    "date", "issueDate", "emissionDate", "movementDate", "creationDate", "createdDate",
    "entryDate", "exitDate", "lastEditTime", "registrationDate",
]
COMPANY_KEYS = ["companyId", "CompanyId", "companyCode", "CompanyCode"]
BRANCH_KEYS = ["branchId", "BranchId", "branchCode", "BranchCode"]

# ==============================
# HTTP por thread (keep-alive + gzip)
# ==============================
_thread_local = local()


def _build_session() -> requests.Session:
    retry = Retry(
        total=ADAPTER_RETRIES, connect=ADAPTER_RETRIES, read=ADAPTER_RETRIES,
        backoff_factor=0.4, status_forcelist=[502, 503, 504],
        allowed_methods=["GET", "HEAD"], raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=64, pool_maxsize=256)
    s = requests.Session()
    s.auth = auth
    s.headers.update({
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
    })
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


def _sess() -> requests.Session:
    s = getattr(_thread_local, "session", None)
    if s is None:
        s = _build_session()
        _thread_local.session = s
    return s


def _safe_request(method: str, url: str, *, params=None, timeout=None):
    timeout = timeout or (CONNECT_TIMEOUT, READ_TIMEOUT)
    last_exc = None
    for attempt in range(1, MANUAL_RETRIES + 1):
        try:
            r = _sess().request(method, url, params=params, timeout=timeout)
            return r, None
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            last_exc = e
            sleep_s = BACKOFF_BASE * (2 ** (attempt - 1))
            print(f"      ⚠️ {type(e).__name__} {attempt}/{MANUAL_RETRIES}. Backoff {sleep_s:.1f}s…")
            time.sleep(sleep_s)
        except Exception as e:
            print(f"      ❌ Exception inesperada: {type(e).__name__}: {e}")
            return None, e
    return None, last_exc


# ==============================
# UTILS
# ==============================
def _norm_code(x: str) -> str:
    s = str(x).strip()
    return str(int(s)) if s.isdigit() else s


def _detect_field_present(obj: Dict[str, Any], candidates: List[str]) -> Optional[str]:
    lower_map = {k.lower(): k for k in obj.keys()}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def _build_company_branch_filter(company_field: Optional[str], branch_field: Optional[str],
                                  comp_code: str, branch_code: str) -> Optional[str]:
    parts = []
    if company_field:
        val = _norm_code(comp_code)
        parts.append(f"{company_field} eq {val if val.isdigit() else repr(val)}")
    if branch_field and str(branch_code).strip() != "":
        bc = str(branch_code).strip()
        parts.append(f"{branch_field} eq {bc if bc.isdigit() else repr(bc)}")
    return " and ".join(parts) if parts else None


def _date_iso(dt: datetime) -> str:
    return dt.isoformat()


# ==============================
# CACHE DE ENTIDADES
# ==============================
class EntityCache:
    """Cache para evitar duplicação de empresas, filiais, centros de custo, etc."""
    
    def __init__(self):
        self.companies = {}  # code -> Company
        self.branches = {}  # (company_id, code) -> Branch
        self.cost_centers = {}  # (company_id, code) -> CostCenter
        self.products = {}  # (company_id, code) -> Product
        self.customer_vendors = {}  # (company_id, code) -> CustomerVendor
        self.lock = Lock()
    
    def get_or_create_company(self, code: str, name: str = None) -> Company:
        """Obtém ou cria uma empresa"""
        code = _norm_code(code)
        
        with self.lock:
            if code in self.companies:
                return self.companies[code]
            
            # Busca no banco
            company = Company.query.filter_by(code=code).first()
            if not company:
                company = Company(code=code, name=name or f"Empresa {code}")
                db.session.add(company)
                db.session.flush()  # Para obter o ID
                print(f"  ✅ Empresa criada: {company.code} - {company.name}")
            
            self.companies[code] = company
            return company
    
    def get_or_create_branch(self, company: Company, code: str, name: str = None) -> Branch:
        """Obtém ou cria uma filial"""
        code = str(code).strip()
        key = (company.id, code)
        
        with self.lock:
            if key in self.branches:
                return self.branches[key]
            
            # Busca no banco
            branch = Branch.query.filter_by(company_id=company.id, code=code).first()
            if not branch:
                branch = Branch(company_id=company.id, code=code, name=name or f"Filial {code}")
                db.session.add(branch)
                db.session.flush()
                print(f"  ✅ Filial criada: {branch.code} - {branch.name}")
            
            self.branches[key] = branch
            return branch
    
    def get_or_create_cost_center(self, company: Company, code: str, name: str) -> CostCenter:
        """Obtém ou cria um centro de custo"""
        code = str(code).strip()
        key = (company.id, code)
        
        with self.lock:
            if key in self.cost_centers:
                cc = self.cost_centers[key]
                # Atualiza o nome se mudou
                if cc.name != name and name:
                    cc.name = name
                    cc.updated_at = datetime.utcnow()
                return cc
            
            # Busca no banco
            cc = CostCenter.query.filter_by(company_id=company.id, code=code).first()
            if not cc:
                cc = CostCenter(company_id=company.id, code=code, name=name or f"CC {code}")
                db.session.add(cc)
                db.session.flush()
                print(f"  ✅ Centro de Custo criado: {cc.code} - {cc.name}")
            elif cc.name != name and name:
                # Atualiza o nome se mudou
                cc.name = name
                cc.updated_at = datetime.utcnow()
            
            self.cost_centers[key] = cc
            return cc
    
    def get_or_create_product(self, company: Company, code: str, product_data: dict) -> Product:
        """Obtém ou cria um produto"""
        code = str(code).strip()
        key = (company.id, code)
        
        with self.lock:
            if key in self.products:
                return self.products[key]
            
            # Busca no banco
            product = Product.query.filter_by(company_id=company.id, code=code).first()
            if not product:
                product = Product(
                    company_id=company.id,
                    code=code,
                    product_id=product_data.get('productId'),
                    name=product_data.get('name'),
                    fantasy_name=product_data.get('fantasyName'),
                    description=product_data.get('description'),
                    measure_unit=product_data.get('measureUnitCode')
                )
                db.session.add(product)
                db.session.flush()
            
            self.products[key] = product
            return product
    
    def get_or_create_customer_vendor(self, company: Company, code: str, name: str = None,
                                      short_name: str = None, cnpj: str = None) -> CustomerVendor:
        """Obtém ou cria um cliente/fornecedor"""
        code = str(code).strip()
        key = (company.id, code)
        
        with self.lock:
            if key in self.customer_vendors:
                return self.customer_vendors[key]
            
            # Busca no banco
            cv = CustomerVendor.query.filter_by(company_id=company.id, code=code).first()
            if not cv:
                cv = CustomerVendor(
                    company_id=company.id,
                    code=code,
                    name=name,
                    short_name=short_name,
                    cnpj=cnpj
                )
                db.session.add(cv)
                db.session.flush()
            
            self.customer_vendors[key] = cv
            return cv


# ==============================
# IMPORTADOR PRINCIPAL
# ==============================
class TOTVSAPIImporter:
    """Importa dados da API TOTVS e popula o banco normalizado"""
    
    def __init__(self):
        self.cache = EntityCache()
        self.stats = {
            'movements': 0,
            'items': 0,
            'payments': 0,
            'taxes': 0,
            'apportionments': 0,
        }
    
    def _get_movements_page(self, page: int, page_size: int, odata_filter: Optional[str]):
        """Busca uma página de movimentos da API"""
        url = f"{HOST}{MOV_ENDPOINT}"
        params = {
            "page": max(1, page),
            "pageSize": max(1, page_size)
        }
        
        if odata_filter:
            params["$filter"] = odata_filter
        
        r, exc = _safe_request("GET", url, params=params)
        if not r or r.status_code >= 400:
            return [], r.status_code if r else -1
        
        try:
            j = r.json()
            if isinstance(j, dict):
                items = j.get("items") or j.get("Items") or []
            elif isinstance(j, list):
                items = j
            else:
                items = []
            return items, r.status_code
        except Exception:
            return [], r.status_code
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Converte string ISO para datetime"""
        if not value or value == "":
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return dtparser.isoparse(value)
            except Exception:
                return None
        return None
    
    def _import_movement(self, mov_data: dict, company: Company, branch: Branch) -> FinancialMovement:
        """Importa um movimento e seus relacionados"""
        
        # Cliente/Fornecedor
        customer_vendor = None
        cv_code = mov_data.get('customerVendorCode')
        if cv_code:
            customer_vendor = self.cache.get_or_create_customer_vendor(
                company,
                cv_code,
                name=mov_data.get('customerVendorName'),
                cnpj=mov_data.get('customerVendorCNPJ')
            )
        
        # Cria o movimento principal
        movement = FinancialMovement(
            internal_id=mov_data.get('internalId'),
            movement_id=mov_data.get('movementId'),
            company_id=company.id,
            branch_id=branch.id,
            customer_vendor_id=customer_vendor.id if customer_vendor else None,
            
            # Documento
            number=mov_data.get('number'),
            series=mov_data.get('series'),
            movement_type_code=mov_data.get('movementTypeCode'),
            type=mov_data.get('type'),
            status=mov_data.get('status'),
            date=self._parse_datetime(mov_data.get('date')),
            
            # Valores
            gross_value=mov_data.get('grossValue', 0.0),
            net_value=mov_data.get('netValue', 0.0),
            informed_net_value=mov_data.get('informedNetValue', 0.0),
            other_values=mov_data.get('otherValues', 0.0),
            merchandise_value=mov_data.get('merchandiseValue', 0.0),
            
            # Descontos e despesas
            discount_percentage=mov_data.get('discountPercentage', 0.0),
            expense_percentage=mov_data.get('expensePercentage', 0.0),
            expense_value=mov_data.get('expenseValue', 0.0),
            
            # Datas
            register_date=self._parse_datetime(mov_data.get('registerDate')),
            entry_date=self._parse_datetime(mov_data.get('entryDate')),
            exit_date=self._parse_datetime(mov_data.get('exitDate')),
            delivery_date=self._parse_datetime(mov_data.get('deliveryDate')),
            creation_date=self._parse_datetime(mov_data.get('creationDate')),
            last_edit_time=self._parse_datetime(mov_data.get('lastEditTime')),
            
            # Armazém
            warehouse_code=mov_data.get('warehouseCode'),
            destiny_warehouse_code=mov_data.get('destinyWarehouseCode'),
            
            # Outros
            observation=mov_data.get('observation'),
            user_code=mov_data.get('userCode'),
            creation_user=mov_data.get('creationUser'),
        )
        
        db.session.add(movement)
        db.session.flush()  # Para obter o ID
        self.stats['movements'] += 1
        
        # Importa itens
        items_data = mov_data.get('movementItems', [])
        for item_data in items_data:
            self._import_movement_item(movement, company, item_data)
        
        # Importa rateios de centro de custo
        apportionments_data = mov_data.get('costCenterApportionments', [])
        for app_data in apportionments_data:
            self._import_cost_center_apportionment(movement, company, app_data)
        
        # Importa pagamentos
        payments_data = mov_data.get('payments', [])
        for pay_data in payments_data:
            self._import_payment(movement, pay_data)
        
        # Importa impostos
        taxes_data = mov_data.get('taxes', [])
        for tax_data in taxes_data:
            self._import_tax(movement, None, tax_data)
        
        return movement
    
    def _import_movement_item(self, movement: FinancialMovement, company: Company, item_data: dict):
        """Importa um item do movimento"""
        
        # Produto
        product = None
        product_code = item_data.get('productCode')
        if product_code:
            product = self.cache.get_or_create_product(company, product_code, item_data)
        
        # Centro de custo do item
        cost_center = None
        cc_data = item_data.get('costCenter', {})
        if cc_data and cc_data.get('costCenterCode'):
            cost_center = self.cache.get_or_create_cost_center(
                company,
                cc_data.get('costCenterCode'),
                cc_data.get('costCenterName', f"CC {cc_data.get('costCenterCode')}")
            )
        
        item = MovementItem(
            movement_id=movement.id,
            product_id=product.id if product else None,
            cost_center_id=cost_center.id if cost_center else None,
            
            sequential_id=item_data.get('sequentialId'),
            sequential_number=item_data.get('sequentialNumber'),
            
            quantity=item_data.get('quantity', 0.0),
            unit_price=item_data.get('unitPrice', 0.0),
            total_value=item_data.get('totalValue', 0.0),
            gross_value=item_data.get('grossValue', 0.0),
            net_value=item_data.get('netValue', 0.0),
            
            measure_unit_code=item_data.get('measureUnitCode'),
            register_date=self._parse_datetime(item_data.get('registerDate')),
        )
        
        db.session.add(item)
        self.stats['items'] += 1
        
        # Impostos do item
        item_taxes = item_data.get('taxes', [])
        for tax_data in item_taxes:
            self._import_tax(movement, item, tax_data)
    
    def _import_cost_center_apportionment(self, movement: FinancialMovement, company: Company, app_data: dict):
        """Importa um rateio de centro de custo"""
        
        cost_center = self.cache.get_or_create_cost_center(
            company,
            app_data.get('costCenterCode'),
            app_data.get('costCenterName', f"CC {app_data.get('costCenterCode')}")
        )
        
        apportionment = CostCenterApportionment(
            movement_id=movement.id,
            cost_center_id=cost_center.id,
            value=app_data.get('value', 0.0) or app_data.get('amount', 0.0) or app_data.get('totalValue', 0.0),
            percentage=app_data.get('percentage', 0.0)
        )
        
        db.session.add(apportionment)
        self.stats['apportionments'] += 1
    
    def _import_payment(self, movement: FinancialMovement, pay_data: dict):
        """Importa um pagamento"""
        
        payment = MovementPayment(
            movement_id=movement.id,
            sequential_number=pay_data.get('paymentSequentialId') or pay_data.get('sequentialNumber'),
            due_date=self._parse_datetime(pay_data.get('dueDate')),
            value=pay_data.get('value', 0.0),
            payment_term_code=pay_data.get('paymentTermCode'),
            installment_number=pay_data.get('installmentNumber'),
            payment_type=pay_data.get('paymentType'),
        )
        
        db.session.add(payment)
        self.stats['payments'] += 1
    
    def _import_tax(self, movement: FinancialMovement, item: MovementItem, tax_data: dict):
        """Importa um imposto"""
        
        tax = MovementTax(
            movement_id=movement.id,
            movement_item_id=item.id if item else None,
            tax_id=tax_data.get('taxId'),
            calculation_basis=tax_data.get('calculationBasis', 0.0),
            aliquot=tax_data.get('aliquot', 0.0),
            value=tax_data.get('value', 0.0),
            edited=tax_data.get('edited', False)
        )
        
        db.session.add(tax)
        self.stats['taxes'] += 1
    
    def import_movements(self, start_date: str, end_date: str, company_code: str, branch_code: str,
                        page_size: int = 50, max_pages: int = 1000):
        """Importa movimentos da API para o banco"""
        
        TZBR = tz.gettz("America/Sao_Paulo")
        dt_ini = datetime.strptime(start_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, tzinfo=TZBR)
        dt_fim = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=TZBR)
        
        print(f"\n{'='*72}")
        print(f"🚀 Importando movimentos da API TOTVS")
        print(f"{'='*72}")
        print(f"Período: {dt_ini.date()} até {dt_fim.date()}")
        print(f"Empresa: {company_code} | Filial: {branch_code}")
        print(f"Endpoint: {HOST}{MOV_ENDPOINT}")
        
        # Obtém ou cria empresa e filial
        company = self.cache.get_or_create_company(company_code)
        branch = self.cache.get_or_create_branch(company, branch_code)
        
        # Monta filtro OData
        date_filter = f"date ge {_date_iso(dt_ini)} and date le {_date_iso(dt_fim)}"
        company_filter = f"companyId eq {company_code}"
        branch_filter = f"branchId eq {branch_code}"
        odata_filter = f"{company_filter} and {branch_filter} and {date_filter}"
        
        print(f"\n📡 Buscando movimentos...")
        print(f"Filtro: {odata_filter}")
        
        page = 1
        total_imported = 0
        
        while page <= max_pages:
            print(f"\n  📄 Página {page}...")
            
            movements_data, status = self._get_movements_page(page, page_size, odata_filter)
            
            if status >= 400 or status == -1:
                print(f"  ❌ Erro HTTP {status} - encerrando importação")
                break
            
            if not movements_data:
                print(f"  ✅ Página vazia - fim dos dados")
                break
            
            print(f"  ✅ {len(movements_data)} movimentos encontrados")
            
            # Importa cada movimento
            for mov_data in movements_data:
                try:
                    self._import_movement(mov_data, company, branch)
                    total_imported += 1
                    
                    # Commit a cada 10 movimentos para evitar transações muito grandes
                    if total_imported % 10 == 0:
                        db.session.commit()
                        print(f"  💾 {total_imported} movimentos importados...")
                
                except Exception as e:
                    print(f"  ⚠️ Erro ao importar movimento {mov_data.get('internalId')}: {e}")
                    db.session.rollback()
            
            # Commit final da página
            db.session.commit()
            
            # Se retornou menos que o page_size, é a última página
            if len(movements_data) < page_size:
                print(f"  ✅ Última página (retornou {len(movements_data)} < {page_size})")
                break
            
            page += 1
        
        print(f"\n{'='*72}")
        print(f"✅ Importação concluída!")
        print(f"{'='*72}")
        print(f"📊 Estatísticas:")
        print(f"  • Movimentos: {self.stats['movements']}")
        print(f"  • Itens: {self.stats['items']}")
        print(f"  • Rateios CC: {self.stats['apportionments']}")
        print(f"  • Pagamentos: {self.stats['payments']}")
        print(f"  • Impostos: {self.stats['taxes']}")
        print(f"{'='*72}\n")


# ==============================
# CLI
# ==============================
def parse_args():
    ap = argparse.ArgumentParser(description="Importa movimentos da API TOTVS para o banco normalizado.")
    ap.add_argument("--inicio", required=True, help="Data inicial (YYYY-MM-DD).")
    ap.add_argument("--fim", required=True, help="Data final (YYYY-MM-DD).")
    ap.add_argument("--empresa", required=True, help="Código da empresa, ex.: 4")
    ap.add_argument("--filial", required=True, help="Código da filial, ex.: 17")
    ap.add_argument("--page-size", type=int, default=50, help="Itens por página (padrão: 50).")
    ap.add_argument("--max-pages", type=int, default=1000, help="Número máximo de páginas (padrão: 1000).")
    return ap.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    # Cria o app Flask para ter acesso ao contexto do banco
    app = create_app()
    
    with app.app_context():
        # Cria as tabelas se não existirem
        db.create_all()
        
        # Executa a importação
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
        except KeyboardInterrupt:
            print("\n⚠️ Importação interrompida pelo usuário.")
            sys.exit(130)
        except Exception as e:
            print(f"\n❌ ERRO fatal: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(2)
