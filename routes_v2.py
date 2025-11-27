# -*- coding: utf-8 -*-
"""
Rotas para o sistema V2 (dados normalizados).
"""
from flask import Blueprint, render_template, abort
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_v2_pure import (
    Base_V2, Company_V2, Branch_V2, CostCenter_V2, Product_V2,
    CustomerVendor_V2, FinancialMovement_V2, MovementItem_V2,
    CostCenterApportionment_V2, BudgetaryNature_V2
)
from sqlalchemy.orm import object_session

# Configuração do banco V2
DATABASE_V2_PATH = 'instance/financial_data_v2.db'
engine_v2 = create_engine(f'sqlite:///{DATABASE_V2_PATH}', echo=False)
Session_v2 = sessionmaker(bind=engine_v2)

# Blueprint para rotas V2
bp_v2 = Blueprint('movements_v2', __name__, url_prefix='/movements_v2')


@bp_v2.route('/')
def list_movements():
    """Lista todos os movimentos V2"""
    session = Session_v2()
    try:
        movements = session.query(FinancialMovement_V2)\
            .order_by(FinancialMovement_V2.date.desc())\
            .limit(100)\
            .all()
        
        return render_template('movements_v2/list.html', movements=movements)
    finally:
        session.close()


@bp_v2.route('/<int:movement_id>')
def detail(movement_id):
    """Detalhes de um movimento V2 - compatível com template original"""
    session = Session_v2()
    try:
        movement = session.query(FinancialMovement_V2)\
            .filter_by(id=movement_id)\
            .first()
        
        if not movement:
            abort(404)
        
        # Adapta o movimento V2 para ter os mesmos métodos que o original
        class MovementAdapter:
            def __init__(self, mov):
                self._mov = mov
                
            def __getattr__(self, name):
                # Delega atributos não encontrados para o movimento original
                return getattr(self._mov, name)
            
            def get_json_field(self, field_name):
                """Simula o get_json_field do sistema antigo"""
                if field_name == 'cost_center_apportionments':
                    return [
                        {
                            'costCenterCode': app.cost_center.code,
                            'costCenterName': app.cost_center.name,
                            'value': app.value,
                            'amount': app.value,
                            'totalValue': app.value,
                        }
                        for app in self._mov.cost_center_apportionments
                    ]
                elif field_name == 'movement_items':
                    # Retorna lista de itens usando o JSON original para fidelidade total
                    items = []
                    for item in self._mov.items:
                        if item.original_data:
                            try:
                                import json
                                item_dict = json.loads(item.original_data)
                                
                                # Fix Definitivo: O template mapeia 'costCenterCode' para 'Centro de Custo'.
                                # O usuário quer que 'Centro de Custo' mostre o NOME.
                                # Então vamos sobrescrever 'costCenterCode' com o nome e remover 'costCenter' para não duplicar.
                                
                                cost_center_name = None
                                if item.cost_center:
                                    cost_center_name = item.cost_center.name
                                elif self._mov.cost_center_apportionments:
                                    # Fallback: Tenta pegar do rateio
                                    for app in self._mov.cost_center_apportionments:
                                        if app.cost_center:
                                            cost_center_name = app.cost_center.name
                                            break
                                
                                if cost_center_name:
                                    item_dict['costCenterCode'] = cost_center_name
                                    # Remove campo duplicado se existir
                                    if 'costCenter' in item_dict:
                                        del item_dict['costCenter']
                                
                                # Fix: Natureza Orçamentária (bugdetNatureCode)
                                # O template espera 'bugdetNatureCode' (com erro de digitação mesmo)
                                bn_code = item_dict.get('bugdetNatureCode') or item_dict.get('budgetNatureCode')
                                if bn_code:
                                    session = object_session(self._mov)
                                    if session:
                                        bn = session.query(BudgetaryNature_V2).filter_by(
                                            company_id=self._mov.company_id,
                                            code=bn_code
                                        ).first()
                                        if bn and bn.description:
                                            item_dict['bugdetNatureCode'] = bn.description

                                items.append(item_dict)
                            except:
                                # Fallback se falhar o parse
                                items.append({
                                    'sequentialNumber': item.sequential_number,
                                    'productCode': item.product.code if item.product else None,
                                    'name': item.product.name if item.product else None,
                                    'quantity': item.quantity or 0,
                                    'unitPrice': item.unit_price or 0,
                                    'totalValue': item.total_value or 0,
                                })
                        else:
                            # Fallback para itens sem JSON original (ex: importados via API nova)
                            items.append({
                                'sequentialNumber': item.sequential_number,
                                'productCode': item.product.code if item.product else None,
                                'name': item.product.name if item.product else None,
                                'quantity': item.quantity or 0,
                                'unitPrice': item.unit_price or 0,
                                'totalValue': item.total_value or 0,
                                'grossValue': getattr(item, 'gross_value', item.total_value or 0),
                                'netValue': getattr(item, 'net_value', item.total_value or 0),
                                'costCenter': {
                                    'costCenterCode': item.cost_center.code if item.cost_center else None,
                                    'costCenterName': item.cost_center.name if item.cost_center else None,
                                } if item.cost_center else {}
                            })
                    return items
                elif field_name == 'taxes':
                    return []  # Por enquanto vazio
                else:
                    return []
            
            # --- Propriedades de Compatibilidade ---
            
            @property
            def company_id(self):
                return self._mov.company.code if self._mov.company else None
            
            @property
            def branch_id(self):
                return self._mov.branch.code if self._mov.branch else None
            
            @property
            def filial_nome(self):
                return self._mov.branch.name if self._mov.branch else None
                
            @property
            def customer_vendor_code(self):
                return self._mov.customer_vendor.code if self._mov.customer_vendor else None
                
            @property
            def aux_customer_vendor_code(self):
                return self.customer_vendor_code
                
            @property
            def customer_vendor_name(self):
                return self._mov.customer_vendor.name if self._mov.customer_vendor else None
            
            @property
            def register_date(self):
                return self._mov.date
                
            @property
            def entry_date(self):
                return self._mov.date  # Fallback
                
            @property
            def last_edit_time(self):
                return self._mov.date  # Fallback
            
            @property
            def enriched_items(self):
                """Retorna itens formatados para a tabela principal"""
                items = []
                for item in self._mov.items:
                    items.append({
                        'sequentialNumber': item.sequential_number,
                        'productCode': item.product.code if item.product else None,
                        'productFantasyName': item.product.name if item.product else None, # Usando nome como fantasia por enquanto
                        'description': item.product.name if item.product else None,
                        'quantity': item.quantity,
                        'unitPrice': item.unit_price,
                        'measureUnitCode': item.product.measure_unit if item.product else None,
                        'totalValue': item.total_value,
                        'registerDate': self._mov.date.isoformat() if self._mov.date else None
                    })
                return items

            # --- Campos Faltantes (Defaults) ---
            @property
            def payment_term_code(self): return '-'
            @property
            def salesman1_code(self): return '-'
            @property
            def net_value_currency_code(self): return 'R$'
            @property
            def discount_percentage_value(self): return 0.0
            @property
            def expense_value(self): return 0.0
            @property
            def freight_value(self): return 0.0
            @property
            def insurance_value(self): return 0.0
            @property
            def destiny_warehouse_code(self): return '-'
            @property
            def user_code(self): return '-'
        
        # Cria o adapter
        adapted_movement = MovementAdapter(movement)
        
        return render_template('movements/detail.html', movement=adapted_movement)
    finally:
        session.close()


@bp_v2.route('/stats')
def stats():
    """Estatísticas do banco V2"""
    session = Session_v2()
    try:
        stats_data = {
            'companies': session.query(Company_V2).count(),
            'branches': session.query(Branch_V2).count(),
            'cost_centers': session.query(CostCenter_V2).count(),
            'products': session.query(Product_V2).count(),
            'customer_vendors': session.query(CustomerVendor_V2).count(),
            'movements': session.query(FinancialMovement_V2).count(),
            'items': session.query(MovementItem_V2).count(),
            'apportionments': session.query(CostCenterApportionment_V2).count(),
        }
        
        return render_template('movements_v2/stats.html', stats=stats_data)
    finally:
        session.close()
