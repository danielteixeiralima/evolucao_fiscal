from app import db
from flask_login import UserMixin
from datetime import datetime
import json

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'

class FinancialMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Core identification fields - all 117 fields from Excel (added 4 new company/branch info fields)
    internal_id = db.Column(db.String(50), nullable=True)
    company_id = db.Column(db.Integer, nullable=True)
    movement_id = db.Column(db.Integer, nullable=True)
    branch_id = db.Column(db.Integer, nullable=True)
    
    # Company and Branch information (new fields)
    empresa_code = db.Column(db.String(50), nullable=True)
    empresa_nome = db.Column(db.String(255), nullable=True)
    filial_code = db.Column(db.String(50), nullable=True)
    filial_nome = db.Column(db.String(255), nullable=True)
    warehouse_code = db.Column(db.String(50), nullable=True)
    destiny_warehouse_code = db.Column(db.String(50), nullable=True)
    number = db.Column(db.Integer, nullable=True)
    series = db.Column(db.String(10), nullable=True)
    movement_type_code = db.Column(db.String(50), nullable=True)
    type = db.Column(db.String(10), nullable=True)
    status = db.Column(db.String(10), nullable=True)
    printed = db.Column(db.Boolean, nullable=True)
    document_printed = db.Column(db.Boolean, nullable=True)
    bill_printed = db.Column(db.Boolean, nullable=True)
    register_date = db.Column(db.DateTime, nullable=True)
    exit_date = db.Column(db.DateTime, nullable=True)
    commercial_representative_charge = db.Column(db.Float, nullable=True)
    gross_value = db.Column(db.Float, nullable=True)
    net_value = db.Column(db.Float, nullable=True)
    informed_net_value = db.Column(db.Float, nullable=True)
    other_values = db.Column(db.Float, nullable=True)
    discount_percentage = db.Column(db.Float, nullable=True)
    expense_percentage = db.Column(db.Float, nullable=True)
    expense_value = db.Column(db.Float, nullable=True)
    extra_percentage1 = db.Column(db.Float, nullable=True)
    extra_value1 = db.Column(db.Float, nullable=True)
    extra_percentage2 = db.Column(db.Float, nullable=True)
    extra_value2 = db.Column(db.Float, nullable=True)
    transported_product_net_weight = db.Column(db.Float, nullable=True)
    transported_product_gross_weight = db.Column(db.Float, nullable=True)
    classification_table5_code = db.Column(db.String(50), nullable=True)
    financial_optional_table2_code = db.Column(db.String(50), nullable=True)
    net_value_currency_code = db.Column(db.String(10), nullable=True)
    date = db.Column(db.DateTime, nullable=True)
    has_generated_bill = db.Column(db.Boolean, nullable=True)
    aux_customer_vendor_code = db.Column(db.String(50), nullable=True)
    aux_customer_vendor_company_id = db.Column(db.Integer, nullable=True)
    cost_center_code = db.Column(db.String(50), nullable=True)
    salesman1_code = db.Column(db.String(50), nullable=True)
    charge_percentage = db.Column(db.Float, nullable=True)
    salesman2_charge_percentage = db.Column(db.Float, nullable=True)
    salesman3_charge_percentage = db.Column(db.Float, nullable=True)
    salesman4_charge_percentage = db.Column(db.Float, nullable=True)
    user_code = db.Column(db.String(50), nullable=True)
    destiny_branch_id = db.Column(db.Integer, nullable=True)
    lot_generated = db.Column(db.Boolean, nullable=True)
    accounting_export_status = db.Column(db.String(50), nullable=True)
    delivery_date = db.Column(db.DateTime, nullable=True)
    has_generated_work_account = db.Column(db.Boolean, nullable=True)
    work_account_generated = db.Column(db.String(50), nullable=True)
    last_edit_time = db.Column(db.DateTime, nullable=True)
    indicate_object_use = db.Column(db.String(50), nullable=True)
    bonum_integrated = db.Column(db.Boolean, nullable=True)
    processed_flag = db.Column(db.Boolean, nullable=True)
    icms_deduction_value = db.Column(db.Float, nullable=True)
    creation_user = db.Column(db.String(50), nullable=True)
    creation_date = db.Column(db.DateTime, nullable=True)
    email_status = db.Column(db.String(50), nullable=True)
    internal_gross_value = db.Column(db.Float, nullable=True)
    other_company_inss_base_value = db.Column(db.Float, nullable=True)
    conditional_discount_value = db.Column(db.Float, nullable=True)
    conditional_expense_value = db.Column(db.Float, nullable=True)
    affect_stock_order = db.Column(db.String(50), nullable=True)
    commercial_automation_exported = db.Column(db.Integer, nullable=True)
    aplication_integration = db.Column(db.String(10), nullable=True)
    entry_date = db.Column(db.DateTime, nullable=True)
    extemporaneous = db.Column(db.Integer, nullable=True)
    merchandise_value = db.Column(db.Float, nullable=True)
    uses_financial_value_apportionment = db.Column(db.Boolean, nullable=True)
    conclusion_flag = db.Column(db.Integer, nullable=True)
    paradigma_status = db.Column(db.String(10), nullable=True)
    paradigma_auto_integrated = db.Column(db.Boolean, nullable=True)
    original_gross_value = db.Column(db.Float, nullable=True)
    original_net_value = db.Column(db.Float, nullable=True)
    original_other_values = db.Column(db.Float, nullable=True)
    operation_id = db.Column(db.Integer, nullable=True)
    scp_branch_id = db.Column(db.Integer, nullable=True)
    
    # JSON fields - properly formatted as Text columns
    movement_items = db.Column(db.Text, nullable=True)
    payments = db.Column(db.Text, nullable=True)
    cost_center_apportionments = db.Column(db.Text, nullable=True)
    department_apportionments = db.Column(db.Text, nullable=True)
    taxes = db.Column(db.Text, nullable=True)
    fiscal = db.Column(db.Text, nullable=True)
    norm = db.Column(db.Text, nullable=True)
    cargo_component = db.Column(db.Text, nullable=True)
    third_party_nf = db.Column(db.Text, nullable=True)
    safety_device = db.Column(db.Text, nullable=True)
    nfe = db.Column(db.Text, nullable=True)
    input_ctrc = db.Column(db.Text, nullable=True)
    output_ctrc = db.Column(db.Text, nullable=True)
    ctrc = db.Column(db.Text, nullable=True)
    transport_data = db.Column(db.Text, nullable=True)
    document_authorization = db.Column(db.Text, nullable=True)
    judicial_process = db.Column(db.Text, nullable=True)
    service_order = db.Column(db.Text, nullable=True)
    related_movement = db.Column(db.Text, nullable=True)
    export_related_movement = db.Column(db.Text, nullable=True)
    linked_movement = db.Column(db.Text, nullable=True)
    c_te = db.Column(db.Text, nullable=True)
    eai_integration = db.Column(db.Text, nullable=True)
    electronic_invoice_free_fields = db.Column(db.Text, nullable=True)
    
    # Remaining fields
    customer_vendor_code = db.Column(db.String(50), nullable=True)
    payment_term_code = db.Column(db.String(50), nullable=True)
    observation = db.Column(db.Text, nullable=True)
    financial_optional_table1_code = db.Column(db.String(50), nullable=True)
    financial_entry_movement_id = db.Column(db.String(50), nullable=True)
    generated_entry_number = db.Column(db.String(50), nullable=True)
    open_entry_number = db.Column(db.String(50), nullable=True)
    cash_account_code = db.Column(db.String(50), nullable=True)
    customer_vendor_company_id = db.Column(db.Integer, nullable=True)
    fluxus_grouped_flag = db.Column(db.Boolean, nullable=True)
    cash_account_company_id = db.Column(db.Integer, nullable=True)
    long_history = db.Column(db.Text, nullable=True)
    
    # Upload tracking
    upload_batch_id = db.Column(db.String(36))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_json_field(self, field_name):
        """Get a JSON field as a Python object"""
        field_value = getattr(self, field_name, None)
        if field_value:
            try:
                return json.loads(field_value) if isinstance(field_value, str) else field_value
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def set_json_field(self, field_name, value):
        """Set a JSON field from a Python object"""
        if value:
            json_value = json.dumps(value) if not isinstance(value, str) else value
            setattr(self, field_name, json_value)
        else:
            setattr(self, field_name, None)
    
    def __repr__(self):
        return f'<FinancialMovement {self.internal_id}>'

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