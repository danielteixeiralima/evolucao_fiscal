# -*- coding: utf-8 -*-
"""
Modelos V2 - Completamente isolados do Flask-SQLAlchemy.
Usa SQLAlchemy puro para evitar conflitos de registry.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index, UniqueConstraint, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

# Base SEPARADA do Flask-SQLAlchemy
Base_V2 = declarative_base()


class Company_V2(Base_V2):
    """Empresa"""
    __tablename__ = 'company_v2'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    branches = relationship('Branch_V2', back_populates='company')
    cost_centers = relationship('CostCenter_V2', back_populates='company')
    movements = relationship('FinancialMovement_V2', back_populates='company')
    
    def __repr__(self):
        return f'<Company {self.code} - {self.name}>'


class Branch_V2(Base_V2):
    """Filial"""
    __tablename__ = 'branch_v2'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('company_v2.id'), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(255))
    
    __table_args__ = (
        UniqueConstraint('company_id', 'code', name='uq_branch_company_code'),
    )
    
    company = relationship('Company_V2', back_populates='branches')
    movements = relationship('FinancialMovement_V2', back_populates='branch')


class CostCenter_V2(Base_V2):
    """Centro de Custo"""
    __tablename__ = 'cost_center_v2'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('company_v2.id'), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('company_id', 'code', name='uq_cc_company_code'),
    )
    
    company = relationship('Company_V2', back_populates='cost_centers')
    apportionments = relationship('CostCenterApportionment_V2', back_populates='cost_center')
    items = relationship('MovementItem_V2', back_populates='cost_center')


class Product_V2(Base_V2):
    """Produto"""
    __tablename__ = 'product_v2'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('company_v2.id'), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(255))
    fantasy_name = Column(String(255))
    measure_unit = Column(String(20))
    
    __table_args__ = (
        UniqueConstraint('company_id', 'code', name='uq_product_company_code'),
    )
    
    items = relationship('MovementItem_V2', back_populates='product')


class CustomerVendor_V2(Base_V2):
    """Cliente/Fornecedor"""
    __tablename__ = 'customer_vendor_v2'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('company_v2.id'), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(255))
    cnpj = Column(String(30))
    
    __table_args__ = (
        UniqueConstraint('company_id', 'code', name='uq_cv_company_code'),
    )
    
    movements = relationship('FinancialMovement_V2', back_populates='customer_vendor')


class FinancialMovement_V2(Base_V2):
    """Movimento Financeiro"""
    __tablename__ = 'financial_movement_v2'
    
    id = Column(Integer, primary_key=True)
    internal_id = Column(String(50), unique=True, nullable=False, index=True)
    movement_id = Column(Integer)
    
    company_id = Column(Integer, ForeignKey('company_v2.id'), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey('branch_v2.id'), nullable=False, index=True)
    customer_vendor_id = Column(Integer, ForeignKey('customer_vendor_v2.id'))
    
    number = Column(Integer)
    series = Column(String(10))
    movement_type_code = Column(String(50))
    type = Column(String(10))
    status = Column(String(10))
    date = Column(DateTime)
    
    gross_value = Column(Float, default=0.0)
    net_value = Column(Float, default=0.0)
    
    warehouse_code = Column(String(50))
    observation = Column(Text)
    
    company = relationship('Company_V2', back_populates='movements')
    branch = relationship('Branch_V2', back_populates='movements')
    customer_vendor = relationship('CustomerVendor_V2', back_populates='movements')
    items = relationship('MovementItem_V2', back_populates='movement', cascade='all, delete-orphan')
    cost_center_apportionments = relationship('CostCenterApportionment_V2', back_populates='movement', cascade='all, delete-orphan')


class MovementItem_V2(Base_V2):
    """Item do Movimento"""
    __tablename__ = 'movement_item_v2'
    
    id = Column(Integer, primary_key=True)
    movement_id = Column(Integer, ForeignKey('financial_movement_v2.id'), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey('product_v2.id'))
    cost_center_id = Column(Integer, ForeignKey('cost_center_v2.id'))
    
    sequential_number = Column(Integer)
    quantity = Column(Float, default=0.0)
    unit_price = Column(Float, default=0.0)
    total_value = Column(Float, default=0.0)
    
    # Campo para armazenar o JSON original completo do item (para fidelidade visual)
    original_data = Column(Text)
    
    movement = relationship('FinancialMovement_V2', back_populates='items')
    product = relationship('Product_V2', back_populates='items')
    cost_center = relationship('CostCenter_V2', back_populates='items')


class CostCenterApportionment_V2(Base_V2):
    """Rateio de Centro de Custo"""
    __tablename__ = 'cost_center_apportionment_v2'
    
    id = Column(Integer, primary_key=True)
    movement_id = Column(Integer, ForeignKey('financial_movement_v2.id'), nullable=False, index=True)
    cost_center_id = Column(Integer, ForeignKey('cost_center_v2.id'), nullable=False, index=True)
    value = Column(Float, default=0.0)
    
    movement = relationship('FinancialMovement_V2', back_populates='cost_center_apportionments')
    cost_center = relationship('CostCenter_V2', back_populates='apportionments')


class BudgetaryNature_V2(Base_V2):
    """Natureza Orçamentária"""
    __tablename__ = 'budgetary_nature_v2'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('company_v2.id'), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    description = Column(String(255))
    
    __table_args__ = (
        UniqueConstraint('company_id', 'code', name='uq_bn_company_code'),
    )
