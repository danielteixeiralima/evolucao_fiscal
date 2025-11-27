# -*- coding: utf-8 -*-
"""
Novos modelos normalizados para o sistema de movimentos fiscais.
Esta estrutura substitui os campos JSON por relacionamentos adequados.
"""
from app import db
from flask_login import UserMixin
from datetime import datetime
import json


# ============================================================================
# MODELOS DE ENTIDADES BÁSICAS (Catálogos)
# ============================================================================

class Company(db.Model):
    """Empresa - Catálogo de empresas"""
    __tablename__ = 'company_v2'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    branches = db.relationship('Branch', backref='company', lazy='dynamic')
    cost_centers = db.relationship('CostCenter', backref='company', lazy='dynamic')
    movements = db.relationship('FinancialMovement', backref='company', lazy='dynamic')
    
    def __repr__(self):
        return f'<Company {self.code} - {self.name}>'


class Branch(db.Model):
    """Filial - Catálogo de filiais por empresa"""
    __tablename__ = 'branch_v2'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_v2.id'), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False, index=True)
    name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Índice composto para garantir unicidade por empresa
    __table_args__ = (
        db.UniqueConstraint('company_id', 'code', name='uq_branch_company_code'),
        db.Index('idx_branch_company_code', 'company_id', 'code'),
    )
    
    # Relacionamentos
    movements = db.relationship('FinancialMovement', backref='branch', lazy='dynamic')
    
    def __repr__(self):
        return f'<Branch {self.code} - {self.name}>'


class CostCenter(db.Model):
    """Centro de Custo - Catálogo de centros de custo"""
    __tablename__ = 'cost_center_v2'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_v2.id'), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)  # ← NOME SEMPRE DISPONÍVEL!
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Índice composto para garantir unicidade por empresa
    __table_args__ = (
        db.UniqueConstraint('company_id', 'code', name='uq_cost_center_company_code'),
        db.Index('idx_cost_center_company_code', 'company_id', 'code'),
    )
    
    # Relacionamentos
    apportionments = db.relationship('CostCenterApportionment', backref='cost_center', lazy='dynamic')
    movement_items = db.relationship('MovementItem', backref='cost_center', lazy='dynamic')
    
    def __repr__(self):
        return f'<CostCenter {self.code} - {self.name}>'


class Product(db.Model):
    """Produto - Catálogo de produtos"""
    __tablename__ = 'product_v2'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_v2.id'), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False, index=True)
    product_id = db.Column(db.String(50), index=True)  # ID do produto na API
    name = db.Column(db.String(255))
    fantasy_name = db.Column(db.String(255))
    description = db.Column(db.Text)
    measure_unit = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Índice composto
    __table_args__ = (
        db.UniqueConstraint('company_id', 'code', name='uq_product_company_code'),
        db.Index('idx_product_company_code', 'company_id', 'code'),
    )
    
    # Relacionamentos
    movement_items = db.relationship('MovementItem', backref='product', lazy='dynamic')
    
    def __repr__(self):
        return f'<Product {self.code} - {self.name or self.fantasy_name}>'


class CustomerVendor(db.Model):
    """Cliente/Fornecedor - Catálogo de parceiros comerciais"""
    __tablename__ = 'customer_vendor_v2'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_v2.id'), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False, index=True)
    name = db.Column(db.String(255))
    short_name = db.Column(db.String(255))
    cnpj = db.Column(db.String(30), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Índice composto
    __table_args__ = (
        db.UniqueConstraint('company_id', 'code', name='uq_customer_vendor_company_code'),
        db.Index('idx_customer_vendor_company_code', 'company_id', 'code'),
        db.Index('idx_customer_vendor_cnpj', 'cnpj'),
    )
    
    # Relacionamentos
    movements = db.relationship('FinancialMovement', backref='customer_vendor', lazy='dynamic')
    
    def __repr__(self):
        return f'<CustomerVendor {self.code} - {self.name or self.short_name}>'


# ============================================================================
# MODELO PRINCIPAL: MOVIMENTO FINANCEIRO
# ============================================================================

class FinancialMovement(db.Model):
    """Movimento Financeiro - Documento fiscal principal"""
    __tablename__ = 'financial_movement_v2'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # ========== IDENTIFICAÇÃO ==========
    internal_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    movement_id = db.Column(db.Integer, index=True)
    
    # ========== RELACIONAMENTOS COM CATÁLOGOS ==========
    company_id = db.Column(db.Integer, db.ForeignKey('company_v2.id'), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch_v2.id'), nullable=False, index=True)
    customer_vendor_id = db.Column(db.Integer, db.ForeignKey('customer_vendor_v2.id'), index=True)
    
    # ========== DADOS DO DOCUMENTO ==========
    number = db.Column(db.Integer)
    series = db.Column(db.String(10))
    movement_type_code = db.Column(db.String(50), index=True)
    type = db.Column(db.String(10))
    status = db.Column(db.String(10), index=True)
    date = db.Column(db.DateTime, index=True)
    
    # ========== VALORES FINANCEIROS ==========
    gross_value = db.Column(db.Float, default=0.0)
    net_value = db.Column(db.Float, default=0.0, index=True)
    informed_net_value = db.Column(db.Float, default=0.0)
    other_values = db.Column(db.Float, default=0.0)
    merchandise_value = db.Column(db.Float, default=0.0)
    internal_gross_value = db.Column(db.Float, default=0.0)
    original_gross_value = db.Column(db.Float, default=0.0)
    original_net_value = db.Column(db.Float, default=0.0)
    original_other_values = db.Column(db.Float, default=0.0)
    
    # ========== DESCONTOS E DESPESAS ==========
    discount_percentage = db.Column(db.Float, default=0.0)
    discount_percentage_value = db.Column(db.Float, default=0.0)
    expense_percentage = db.Column(db.Float, default=0.0)
    expense_value = db.Column(db.Float, default=0.0)
    conditional_discount_value = db.Column(db.Float, default=0.0)
    conditional_expense_value = db.Column(db.Float, default=0.0)
    
    # ========== EXTRAS E ENCARGOS ==========
    extra_percentage1 = db.Column(db.Float, default=0.0)
    extra_value1 = db.Column(db.Float, default=0.0)
    extra_percentage2 = db.Column(db.Float, default=0.0)
    extra_value2 = db.Column(db.Float, default=0.0)
    charge_percentage = db.Column(db.Float, default=0.0)
    commercial_representative_charge = db.Column(db.Float, default=0.0)
    
    # ========== FRETE E SEGURO ==========
    freight_value = db.Column(db.Float, default=0.0)
    insurance_value = db.Column(db.Float, default=0.0)
    transported_product_net_weight = db.Column(db.Float, default=0.0)
    transported_product_gross_weight = db.Column(db.Float, default=0.0)
    
    # ========== IMPOSTOS ==========
    icms_deduction_value = db.Column(db.Float, default=0.0)
    other_company_inss_base_value = db.Column(db.Float, default=0.0)
    
    # ========== DATAS ==========
    register_date = db.Column(db.DateTime, index=True)
    entry_date = db.Column(db.DateTime)
    exit_date = db.Column(db.DateTime)
    delivery_date = db.Column(db.DateTime)
    creation_date = db.Column(db.DateTime)
    last_edit_time = db.Column(db.DateTime)
    
    # ========== ARMAZÉM E OPERAÇÕES ==========
    warehouse_code = db.Column(db.String(50))
    destiny_warehouse_code = db.Column(db.String(50))
    destiny_branch_id_value = db.Column(db.Integer)
    operation_id = db.Column(db.Integer)
    
    # ========== VENDEDORES ==========
    salesman1_code = db.Column(db.String(50))
    salesman2_charge_percentage = db.Column(db.Float, default=0.0)
    salesman3_charge_percentage = db.Column(db.Float, default=0.0)
    salesman4_charge_percentage = db.Column(db.Float, default=0.0)
    
    # ========== CÓDIGOS E TABELAS ==========
    classification_table5_code = db.Column(db.String(50))
    financial_optional_table1_code = db.Column(db.String(50))
    financial_optional_table2_code = db.Column(db.String(50))
    payment_term_code = db.Column(db.String(50))
    cash_account_code = db.Column(db.String(50))
    cash_account_company_id = db.Column(db.Integer)
    
    # ========== MOEDA ==========
    net_value_currency_code = db.Column(db.String(10))
    
    # ========== FLAGS E STATUS ==========
    printed = db.Column(db.Boolean, default=False)
    document_printed = db.Column(db.Boolean, default=False)
    bill_printed = db.Column(db.Boolean, default=False)
    has_generated_bill = db.Column(db.Boolean, default=False)
    lot_generated = db.Column(db.Boolean, default=False)
    has_generated_work_account = db.Column(db.Boolean, default=False)
    bonum_integrated = db.Column(db.Boolean, default=False)
    processed_flag = db.Column(db.Boolean, default=False)
    paradigma_auto_integrated = db.Column(db.Boolean, default=False)
    fluxus_grouped_flag = db.Column(db.Boolean, default=False)
    uses_financial_value_apportionment = db.Column(db.Boolean, default=False)
    extemporaneous = db.Column(db.Integer, default=0)
    conclusion_flag = db.Column(db.Integer, default=0)
    commercial_automation_exported = db.Column(db.Integer, default=0)
    
    # ========== OUTROS ==========
    user_code = db.Column(db.String(50))
    creation_user = db.Column(db.String(50))
    accounting_export_status = db.Column(db.String(50))
    work_account_generated = db.Column(db.String(50))
    indicate_object_use = db.Column(db.String(50))
    email_status = db.Column(db.String(50))
    affect_stock_order = db.Column(db.String(50))
    aplication_integration = db.Column(db.String(10))
    paradigma_status = db.Column(db.String(10))
    scp_branch_id = db.Column(db.Integer)
    
    # ========== TEXTOS LONGOS ==========
    observation = db.Column(db.Text)
    long_history = db.Column(db.Text)
    
    # ========== CAMPOS FINANCEIROS ADICIONAIS ==========
    financial_entry_movement_id = db.Column(db.String(50))
    generated_entry_number = db.Column(db.String(50))
    open_entry_number = db.Column(db.String(50))
    
    # ========== TRACKING DE UPLOAD ==========
    upload_batch_id = db.Column(db.String(36), index=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ========== RELACIONAMENTOS ==========
    items = db.relationship('MovementItem', backref='movement', lazy='dynamic', cascade='all, delete-orphan')
    payments = db.relationship('MovementPayment', backref='movement', lazy='dynamic', cascade='all, delete-orphan')
    taxes = db.relationship('MovementTax', backref='movement', lazy='dynamic', cascade='all, delete-orphan')
    cost_center_apportionments = db.relationship('CostCenterApportionment', backref='movement', lazy='dynamic', cascade='all, delete-orphan')
    department_apportionments = db.relationship('DepartmentApportionment', backref='movement', lazy='dynamic', cascade='all, delete-orphan')
    
    # Índices compostos para performance
    __table_args__ = (
        db.Index('idx_movement_company_branch', 'company_id', 'branch_id'),
        db.Index('idx_movement_date_company', 'date', 'company_id'),
        db.Index('idx_movement_status_date', 'status', 'date'),
    )
    
    def __repr__(self):
        return f'<FinancialMovement {self.internal_id}>'


# ============================================================================
# MODELOS RELACIONADOS AO MOVIMENTO
# ============================================================================

class MovementItem(db.Model):
    """Item do Movimento - Produtos/serviços do documento fiscal"""
    __tablename__ = 'movement_item_v2'
    
    id = db.Column(db.Integer, primary_key=True)
    movement_id = db.Column(db.Integer, db.ForeignKey('financial_movement_v2.id'), nullable=False, index=True)
    
    # Relacionamentos
    product_id = db.Column(db.Integer, db.ForeignKey('product_v2.id'), index=True)
    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_center_v2.id'), index=True)
    
    # Identificação do item
    sequential_id = db.Column(db.Integer)
    sequential_number = db.Column(db.Integer)
    
    # Quantidades
    quantity = db.Column(db.Float, default=0.0)
    original_quantity = db.Column(db.Float, default=0.0)
    receivable_quantity = db.Column(db.Float, default=0.0)
    completed_quantity = db.Column(db.Float, default=0.0)
    
    # Valores
    unit_price = db.Column(db.Float, default=0.0)
    table_price = db.Column(db.Float, default=0.0)
    unit_value = db.Column(db.Float, default=0.0)
    financial_value = db.Column(db.Float, default=0.0)
    gross_value = db.Column(db.Float, default=0.0)
    net_value = db.Column(db.Float, default=0.0)
    total_value = db.Column(db.Float, default=0.0)
    discount_value = db.Column(db.Float, default=0.0)
    completed_value = db.Column(db.Float, default=0.0)
    
    # Datas
    register_date = db.Column(db.DateTime)
    delivery_date = db.Column(db.DateTime)
    
    # Códigos e classificações
    measure_unit_code = db.Column(db.String(20))
    classification_table5_code = db.Column(db.String(50))
    financial_optional_table2_code = db.Column(db.String(50))
    
    # Flags
    stock_effect_flag = db.Column(db.String(10))
    flag = db.Column(db.String(50))
    block_object = db.Column(db.String(50))
    
    # Outros
    partial_billing_received_value = db.Column(db.Float, default=0.0)
    ordination_tax_aliquot = db.Column(db.Float, default=0.0)
    
    # Índices
    __table_args__ = (
        db.Index('idx_item_movement_product', 'movement_id', 'product_id'),
        db.Index('idx_item_cost_center', 'cost_center_id'),
    )
    
    def __repr__(self):
        return f'<MovementItem {self.sequential_number} - Movement {self.movement_id}>'


class MovementPayment(db.Model):
    """Pagamento do Movimento - Parcelas e formas de pagamento"""
    __tablename__ = 'movement_payment_v2'
    
    id = db.Column(db.Integer, primary_key=True)
    movement_id = db.Column(db.Integer, db.ForeignKey('financial_movement_v2.id'), nullable=False, index=True)
    
    # Dados do pagamento
    sequential_number = db.Column(db.Integer)
    due_date = db.Column(db.DateTime)
    value = db.Column(db.Float, default=0.0)
    payment_term_code = db.Column(db.String(50))
    installment_number = db.Column(db.Integer)
    
    # Outros campos do pagamento (adicionar conforme necessário)
    payment_type = db.Column(db.String(50))
    bank_code = db.Column(db.String(20))
    
    def __repr__(self):
        return f'<MovementPayment {self.sequential_number} - R$ {self.value}>'


class MovementTax(db.Model):
    """Imposto do Movimento - Impostos aplicados ao documento"""
    __tablename__ = 'movement_tax_v2'
    
    id = db.Column(db.Integer, primary_key=True)
    movement_id = db.Column(db.Integer, db.ForeignKey('financial_movement_v2.id'), nullable=False, index=True)
    movement_item_id = db.Column(db.Integer, db.ForeignKey('movement_item_v2.id'), index=True)
    
    # Dados do imposto
    tax_id = db.Column(db.String(50), index=True)
    calculation_basis = db.Column(db.Float, default=0.0)
    calculated_calculation_basis = db.Column(db.Float, default=0.0)
    full_base = db.Column(db.Float, default=0.0)
    aliquot = db.Column(db.Float, default=0.0)
    value = db.Column(db.Float, default=0.0)
    
    # Flags
    edited = db.Column(db.Boolean, default=False)
    
    # Índices
    __table_args__ = (
        db.Index('idx_tax_movement_type', 'movement_id', 'tax_id'),
    )
    
    def __repr__(self):
        return f'<MovementTax {self.tax_id} - R$ {self.value}>'


class CostCenterApportionment(db.Model):
    """Rateio de Centro de Custo - Distribuição de valores por centro de custo"""
    __tablename__ = 'cost_center_apportionment_v2'
    
    id = db.Column(db.Integer, primary_key=True)
    movement_id = db.Column(db.Integer, db.ForeignKey('financial_movement_v2.id'), nullable=False, index=True)
    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_center_v2.id'), nullable=False, index=True)
    
    # Valor do rateio
    value = db.Column(db.Float, default=0.0)
    percentage = db.Column(db.Float, default=0.0)
    
    # Índices
    __table_args__ = (
        db.Index('idx_apportionment_movement_cc', 'movement_id', 'cost_center_id'),
    )
    
    def __repr__(self):
        return f'<CostCenterApportionment CC:{self.cost_center_id} - R$ {self.value}>'


class DepartmentApportionment(db.Model):
    """Rateio de Departamento - Distribuição de valores por departamento"""
    __tablename__ = 'department_apportionment_v2'
    
    id = db.Column(db.Integer, primary_key=True)
    movement_id = db.Column(db.Integer, db.ForeignKey('financial_movement_v2.id'), nullable=False, index=True)
    
    # Dados do departamento (simplificado - expandir conforme necessário)
    department_code = db.Column(db.String(50))
    department_name = db.Column(db.String(255))
    value = db.Column(db.Float, default=0.0)
    percentage = db.Column(db.Float, default=0.0)
    
    def __repr__(self):
        return f'<DepartmentApportionment {self.department_code} - R$ {self.value}>'

