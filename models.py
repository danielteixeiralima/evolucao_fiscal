from app import db
from flask_login import UserMixin
from datetime import datetime
import json
from sqlalchemy.orm import relationship

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'

class UploadHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.String(36), unique=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_rows = db.Column(db.Integer, default=0)
    success_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)
    errors = db.Column(db.Text)
    status = db.Column(db.String(20), default='processing')
    
    # Relationship
    uploader = db.relationship('User', backref='uploads')
    
    def __repr__(self):
        return f'<UploadHistory {self.filename}>'

# -----------------------------------------------------------------------------
# V2 MODELS (Normalized) - Adapted for Flask-SQLAlchemy
# -----------------------------------------------------------------------------

class Company(db.Model):
    """Empresa"""
    __tablename__ = 'company'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    branches = db.relationship('Branch', back_populates='company')
    cost_centers = db.relationship('CostCenter', back_populates='company')
    movements = db.relationship('FinancialMovement', back_populates='company')
    
    def __repr__(self):
        return f'<Company {self.code} - {self.name}>'


class Branch(db.Model):
    """Filial"""
    __tablename__ = 'branch'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False, index=True)
    name = db.Column(db.String(255))
    
    __table_args__ = (
        db.UniqueConstraint('company_id', 'code', name='uq_branch_company_code'),
    )
    
    company = db.relationship('Company', back_populates='branches')
    movements = db.relationship('FinancialMovement', back_populates='branch')


class CostCenter(db.Model):
    """Centro de Custo"""
    __tablename__ = 'cost_center'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('company_id', 'code', name='uq_cc_company_code'),
    )
    
    company = db.relationship('Company', back_populates='cost_centers')
    apportionments = db.relationship('CostCenterApportionment', back_populates='cost_center')
    items = db.relationship('MovementItem', back_populates='cost_center')


class Product(db.Model):
    """Produto"""
    __tablename__ = 'product'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False, index=True)
    name = db.Column(db.String(255))
    fantasy_name = db.Column(db.String(255))
    measure_unit = db.Column(db.String(20))
    
    __table_args__ = (
        db.UniqueConstraint('company_id', 'code', name='uq_product_company_code'),
    )
    
    items = db.relationship('MovementItem', back_populates='product')


class CustomerVendor(db.Model):
    """Cliente/Fornecedor"""
    __tablename__ = 'customer_vendor'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False, index=True)
    name = db.Column(db.String(255))
    cnpj = db.Column(db.String(30))
    
    __table_args__ = (
        db.UniqueConstraint('company_id', 'code', name='uq_cv_company_code'),
    )
    
    movements = db.relationship('FinancialMovement', back_populates='customer_vendor')


class FinancialMovement(db.Model):
    """Movimento Financeiro"""
    __tablename__ = 'financial_movement'
    
    id = db.Column(db.Integer, primary_key=True)
    internal_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    movement_id = db.Column(db.Integer)
    
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False, index=True)
    customer_vendor_id = db.Column(db.Integer, db.ForeignKey('customer_vendor.id'))
    
    number = db.Column(db.Integer)
    series = db.Column(db.String(10))
    movement_type_code = db.Column(db.String(50))
    type = db.Column(db.String(10))
    status = db.Column(db.String(10))
    date = db.Column(db.DateTime)
    
    gross_value = db.Column(db.Float, default=0.0)
    net_value = db.Column(db.Float, default=0.0)
    
    warehouse_code = db.Column(db.String(50))
    observation = db.Column(db.Text)
    
    # Upload tracking
    upload_batch_id = db.Column(db.String(36))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    company = db.relationship('Company', back_populates='movements')
    branch = db.relationship('Branch', back_populates='movements')
    customer_vendor = db.relationship('CustomerVendor', back_populates='movements')
    items = db.relationship('MovementItem', back_populates='movement', cascade='all, delete-orphan')
    cost_center_apportionments = db.relationship('CostCenterApportionment', back_populates='movement', cascade='all, delete-orphan')
    
    def get_json_field(self, field_name):
        """Helper for compatibility with old templates, though logic should move to Adapter"""
        return None 


class MovementItem(db.Model):
    """Item do Movimento"""
    __tablename__ = 'movement_item'
    
    id = db.Column(db.Integer, primary_key=True)
    movement_id = db.Column(db.Integer, db.ForeignKey('financial_movement.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_center.id'))
    
    sequential_number = db.Column(db.Integer)
    quantity = db.Column(db.Float, default=0.0)
    unit_price = db.Column(db.Float, default=0.0)
    total_value = db.Column(db.Float, default=0.0)
    
    # Campo para armazenar o JSON original completo do item (para fidelidade visual)
    original_data = db.Column(db.Text)
    
    movement = db.relationship('FinancialMovement', back_populates='items')
    product = db.relationship('Product', back_populates='items')
    cost_center = db.relationship('CostCenter', back_populates='items')


class CostCenterApportionment(db.Model):
    """Rateio de Centro de Custo"""
    __tablename__ = 'cost_center_apportionment'
    
    id = db.Column(db.Integer, primary_key=True)
    movement_id = db.Column(db.Integer, db.ForeignKey('financial_movement.id'), nullable=False, index=True)
    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_center.id'), nullable=False, index=True)
    value = db.Column(db.Float, default=0.0)
    
    movement = db.relationship('FinancialMovement', back_populates='cost_center_apportionments')
    cost_center = db.relationship('CostCenter', back_populates='apportionments')


class BudgetaryNature(db.Model):
    """Natureza Orçamentária"""
    __tablename__ = 'budgetary_nature'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.String(255))
    
    __table_args__ = (
        db.UniqueConstraint('company_id', 'code', name='uq_bn_company_code'),
    )