import os
import uuid
import json
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_, desc
from app import db, login_manager
from models import (
    User, UploadHistory, 
    Company, Branch, CostCenter, Product, CustomerVendor, 
    FinancialMovement, MovementItem, CostCenterApportionment, BudgetaryNature
)
from forms import LoginForm, UserForm, EditUserForm, FileUploadForm
# from file_processor import FinancialDataProcessor # Temporarily disabled until updated
import logging

logger = logging.getLogger(__name__)

# TOTVS API Configuration
TOTVS_API_BASE = "http://192.168.18.9:8051/api/mov/v1"
TOTVS_API_USER = "INTEGRA_INOVAI"
TOTVS_API_PWD = "INOVAI.LAB"
totvs_auth = HTTPBasicAuth(TOTVS_API_USER, TOTVS_API_PWD)

def fetch_budgetary_nature_description(code):
    """Fetch budgetary nature description from TOTVS API"""
    if not code:
        return None
    
    try:
        url = f"{TOTVS_API_BASE}/FinancialBudgetaryNatures"
        filter_param = f"code eq '{code}'"
        params = {"$filter": filter_param}
        
        response = requests.get(url, params=params, auth=totvs_auth, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, dict) and 'items' in data and len(data['items']) > 0:
                description = data['items'][0].get('description')
                return description
            elif isinstance(data, list) and len(data) > 0:
                description = data[0].get('description')
                return description
        
        logger.warning(f"Failed to fetch budgetary nature for code {code}: {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error fetching budgetary nature for code {code}: {str(e)}")
        return None

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Blueprint definitions
main_bp = Blueprint('main', __name__)
admin_bp = Blueprint('admin', __name__)
auth_bp = Blueprint('auth', __name__)

def admin_required(f):
    """Decorator to require admin access"""
    from functools import wraps
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You need administrator privileges to access this page.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# Main routes
@main_bp.route('/')
def index():
    """Homepage - show recent movements"""
    recent_movements = FinancialMovement.query.order_by(desc(FinancialMovement.date)).limit(10).all()
    return render_template('index.html', movements=recent_movements)

@main_bp.route('/movements')
@login_required
def movements():
    """List all movements with search, filters and pagination (V2 Logic)"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    company_filter = request.args.get('company', '', type=str)
    branch_filter = request.args.get('branch', '', type=str)
    status_filter = request.args.get('status', '', type=str)
    per_page = 25
    start_date = request.args.get('start_date', '', type=str)
    end_date = request.args.get('end_date', '', type=str)
    
    query = FinancialMovement.query.join(Company, FinancialMovement.company_id == Company.id).join(Branch, FinancialMovement.branch_id == Branch.id).outerjoin(CustomerVendor, FinancialMovement.customer_vendor_id == CustomerVendor.id)
    
    # Apply date filter
    if start_date:
        try:
            sd = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(FinancialMovement.date >= sd)
        except ValueError:
            pass
            
    if end_date:
        try:
            ed = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(FinancialMovement.date <= ed)
        except ValueError:
            pass
    
    # Apply search filter
    if search:
        s = search.strip()
        text_conds = [
            FinancialMovement.internal_id.ilike(f"%{s}%"),
            FinancialMovement.observation.ilike(f"%{s}%"),
            FinancialMovement.movement_type_code.ilike(f"%{s}%"),
            Company.name.ilike(f"%{s}%"),
            Branch.name.ilike(f"%{s}%"),
            CustomerVendor.name.ilike(f"%{s}%"),
            CustomerVendor.code.ilike(f"%{s}%"),
            CustomerVendor.cnpj.ilike(f"%{s}%"),
        ]
        if s.isdigit():
            text_conds.append(FinancialMovement.number == int(s))
            
        query = query.filter(or_(*text_conds))
    
    # Apply company filter
    if company_filter:
        query = query.filter(Company.name.contains(company_filter))
    
    # Apply branch filter  
    if branch_filter:
        query = query.filter(Branch.name.contains(branch_filter))
    
    # Apply status filter
    if status_filter:
        query = query.filter(FinancialMovement.status == status_filter)
    
    movements = query.order_by(desc(FinancialMovement.date)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get unique values for filter dropdowns
    companies = db.session.query(Company.name).distinct().order_by(Company.name).all()
    companies = [c[0] for c in companies if c[0]]
    
    branches = db.session.query(Branch.name).distinct().order_by(Branch.name).all()
    branches = [b[0] for b in branches if b[0]]
    
    statuses = db.session.query(FinancialMovement.status).distinct().filter(
        FinancialMovement.status.isnot(None)
    ).order_by(FinancialMovement.status).all()
    statuses = [s[0] for s in statuses if s[0]]
    
    return render_template('movements/list.html', 
                         movements=movements, 
                         search=search,
                         company_filter=company_filter,
                         branch_filter=branch_filter,
                         status_filter=status_filter,
                         companies=companies,
                         branches=branches,
                         statuses=statuses,
                         start_date=start_date,
                         end_date=end_date)

class MovementAdapter:
    """Adapts V2 FinancialMovement to be compatible with V1 templates"""
    def __init__(self, mov):
        self._mov = mov
        
    def __getattr__(self, name):
        return getattr(self._mov, name)
    
    def get_json_field(self, field_name):
        """Simulates get_json_field from old system"""
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
            items = []
            for item in self._mov.items:
                if item.original_data:
                    try:
                        item_dict = json.loads(item.original_data)
                        
                        # Fix: Ensure costCenterCode is the name if possible (as per user request)
                        cost_center_name = None
                        if item.cost_center:
                            cost_center_name = item.cost_center.name
                        elif self._mov.cost_center_apportionments:
                            for app in self._mov.cost_center_apportionments:
                                if app.cost_center:
                                    cost_center_name = app.cost_center.name
                                    break
                        
                        if cost_center_name:
                            item_dict['costCenterCode'] = cost_center_name
                            if 'costCenter' in item_dict:
                                del item_dict['costCenter']
                        
                        # Fix: Budgetary Nature - Fetch from API
                        bn_code = item_dict.get('bugdetNatureCode') or item_dict.get('budgetNatureCode')
                        if bn_code:
                            logger.debug(f"Fetching budgetary nature for code: {bn_code}")
                            # Try API first
                            bn_description = fetch_budgetary_nature_description(bn_code)
                            if bn_description:
                                logger.debug(f"API returned description: {bn_description}")
                                # Update both possible field names
                                item_dict['bugdetNatureCode'] = bn_description
                                item_dict['budgetNatureCode'] = bn_description
                            else:
                                logger.warning(f"API failed for code {bn_code}, trying database")
                                # Fallback to database
                                bn = BudgetaryNature.query.filter_by(
                                    company_id=self._mov.company_id,
                                    code=bn_code
                                ).first()
                                if bn and bn.description:
                                    logger.debug(f"Database returned description: {bn.description}")
                                    item_dict['bugdetNatureCode'] = bn.description
                                    item_dict['budgetNatureCode'] = bn.description
                                else:
                                    logger.warning(f"No description found for budgetary nature code: {bn_code}")

                        items.append(item_dict)
                    except Exception as e:
                        logger.error(f"Error processing movement item: {str(e)}")
                        items.append(self._fallback_item(item))
                else:
                    items.append(self._fallback_item(item))
            return items
        elif field_name == 'taxes':
            return []
        else:
            return []

    def _fallback_item(self, item):
        return {
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
        }
    
    # Compatibility Properties
    @property
    def company_id(self): return self._mov.company.code if self._mov.company else None
    
    @property
    def branch_id(self): return self._mov.branch.code if self._mov.branch else None
    
    @property
    def filial_nome(self): return self._mov.branch.name if self._mov.branch else None
        
    @property
    def customer_vendor_code(self): return self._mov.customer_vendor.code if self._mov.customer_vendor else None
        
    @property
    def aux_customer_vendor_code(self): return self.customer_vendor_code
        
    @property
    def customer_vendor_name(self): return self._mov.customer_vendor.name if self._mov.customer_vendor else None
    
    @property
    def register_date(self): return self._mov.date
        
    @property
    def entry_date(self): return self._mov.date
        
    @property
    def last_edit_time(self): return self._mov.date
    
    @property
    def enriched_items(self):
        items = []
        for item in self._mov.items:
            items.append({
                'sequentialNumber': item.sequential_number,
                'productCode': item.product.code if item.product else None,
                'productFantasyName': item.product.name if item.product else None,
                'description': item.product.name if item.product else None,
                'quantity': item.quantity,
                'unitPrice': item.unit_price,
                'measureUnitCode': item.product.measure_unit if item.product else None,
                'totalValue': item.total_value,
                'registerDate': self._mov.date.isoformat() if self._mov.date else None
            })
        return items

    # Defaults
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


@main_bp.route('/movements/<int:id>')
@login_required
def movement_detail(id):
    """Show detailed view of a specific movement"""
    movement = FinancialMovement.query.get_or_404(id)
    adapted_movement = MovementAdapter(movement)
    return render_template('movements/detail.html', movement=adapted_movement)

@main_bp.route('/movements/<int:id>/delete', methods=['POST'])
@login_required
def delete_movement(id):
    """Delete a specific movement"""
    movement = FinancialMovement.query.get_or_404(id)
    try:
        movement_name = movement.internal_id or f"#{movement.id}"
        db.session.delete(movement)
        db.session.commit()
        flash(f'Movement {movement_name} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting movement: {str(e)}', 'error')
        logger.error(f"Error deleting movement {id}: {str(e)}")
    
    return redirect(url_for('main.movements'))

@main_bp.route('/movements/delete-all', methods=['GET', 'POST'])
@login_required
def delete_all_movements():
    """Delete all movements from database"""
    if request.method == 'POST':
        confirmation = request.form.get('confirmation', '').strip().lower()
        
        if confirmation == 'delete all movements':
            try:
                movement_count = FinancialMovement.query.count()
                # Also delete related data? Cascade should handle it if models are set up right.
                # But explicit delete is safer if not.
                db.session.query(FinancialMovement).delete()
                # db.session.query(UploadHistory).delete() # Keep upload history? Maybe.
                db.session.commit()
                
                flash(f'All movements deleted successfully! {movement_count} records removed.', 'success')
                return redirect(url_for('main.movements'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error deleting data: {str(e)}', 'error')
                logger.error(f"Error deleting all movements: {str(e)}")
                
        else:
            flash('Invalid confirmation text. Type exactly "delete all movements" to confirm.', 'warning')
    
    movement_count = FinancialMovement.query.count()
    upload_count = UploadHistory.query.count()
    
    return render_template('movements/delete_all.html', 
                          movement_count=movement_count, 
                          upload_count=upload_count)

@main_bp.route('/api/movements/<int:id>/json/<field>')
@login_required
def get_movement_json_field(id, field):
    """API endpoint - Adapted"""
    movement = FinancialMovement.query.get_or_404(id)
    adapter = MovementAdapter(movement)
    json_data = adapter.get_json_field(field)
    return jsonify(json_data)

# Authentication routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password_hash and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page:
                next_page = url_for('admin.dashboard') if user.is_admin else url_for('main.index')
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(next_page)
        flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

# Admin routes
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard with statistics"""
    stats = {
        'total_users': User.query.count(),
        'total_movements': FinancialMovement.query.count(),
        'total_uploads': UploadHistory.query.count(),
        'recent_uploads': UploadHistory.query.order_by(desc(UploadHistory.uploaded_at)).limit(5).all()
    }
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/users')
@admin_required
def users():
    """List all users"""
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@admin_required
def create_user():
    """Create new user"""
    form = UserForm()
    if form.validate_on_submit():
        password_data = form.password.data
        if password_data:
            user = User(
                username=form.username.data,
                email=form.email.data,
                is_admin=form.is_admin.data,
                password_hash=generate_password_hash(password_data)
            )
        else:
            flash('Password is required', 'error')
            return render_template('admin/users.html', form=form, action='create')
        db.session.add(user)
        db.session.commit()
        flash(f'User {user.username} created successfully!', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/users.html', form=form, action='create')

@admin_bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(id):
    """Edit existing user"""
    user = User.query.get_or_404(id)
    form = EditUserForm(
        original_username=user.username,
        original_email=user.email,
        obj=user
    )
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        db.session.commit()
        flash(f'User {user.username} updated successfully!', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/users.html', form=form, user=user, action='edit')

@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
@admin_required
def delete_user(id):
    """Delete user"""
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('You cannot delete your own account!', 'error')
        return redirect(url_for('admin.users'))
    
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.username} deleted successfully!', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/upload', methods=['GET', 'POST'])
@admin_required
def upload_file():
    """Upload Excel file with financial data"""
    form = FileUploadForm()
    if form.validate_on_submit():
        # Temporarily disabled or needs update
        flash('Upload functionality is currently being updated to the new system structure. Please use the API importer.', 'warning')
        return redirect(url_for('admin.dashboard'))
        
        # Original logic commented out
        # file = form.file.data
        # filename = secure_filename(file.filename)
        # unique_filename = f"{uuid.uuid4()}_{filename}"
        # file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        # try:
        #     file.save(file_path)
        #     processor = FinancialDataProcessor()
        #     batch_id, success_count, error_count, errors, processed_data = processor.process_file(
        #         file_path, current_user.id
        #     )
        #     if hasattr(processor, "close"):
        #         try: processor.close()
        #         except: pass
        #     import time
        #     for i in range(5):
        #         try:
        #             if os.path.exists(file_path): os.remove(file_path)
        #             break
        #         except PermissionError: time.sleep(0.5)
        #     if error_count > 0:
        #         flash(f'File processed with {success_count} successful records and {error_count} errors.', 'warning')
        #     else:
        #         flash(f'File uploaded successfully! {success_count} records processed.', 'success')
        #     return redirect(url_for('admin.upload_history'))
        # except Exception as e:
        #     if os.path.exists(file_path): os.remove(file_path)
        #     flash(f'Error processing file: {str(e)}', 'error')
        #     logger.error(f"Upload processing error: {str(e)}")
    
    return render_template('admin/upload.html', form=form)

@admin_bp.route('/upload-history')
@admin_required
def upload_history():
    """View upload history"""
    page = request.args.get('page', 1, type=int)
    uploads = UploadHistory.query.order_by(desc(UploadHistory.uploaded_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/upload.html', uploads=uploads, show_history=True)

@admin_bp.route('/upload-history/<int:id>')
@admin_required
def upload_history_detail(id):
    """View detailed upload history"""
    upload = UploadHistory.query.get_or_404(id)
    movements = FinancialMovement.query.filter_by(upload_batch_id=upload.batch_id).all()
    return render_template('admin/upload.html', upload=upload, movements=movements, show_detail=True)

@admin_bp.route('/clear-movements', methods=['GET', 'POST'])
@admin_required
def clear_movements():
    """Clear all financial movements from database"""
    if request.method == 'POST':
        confirmation = request.form.get('confirmation', '').strip().lower()
        
        if confirmation == 'delete all movements':
            try:
                movement_count = FinancialMovement.query.count()
                upload_count = UploadHistory.query.count()
                
                db.session.query(FinancialMovement).delete()
                # db.session.query(UploadHistory).delete()
                db.session.commit()
                
                flash(f'Database cleared successfully! {movement_count} financial movements deleted.', 'success')
                return redirect(url_for('admin.dashboard'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error clearing database: {str(e)}', 'error')
                
        else:
            flash('Invalid confirmation text. Type exactly "delete all movements" to confirm.', 'warning')
    
    movement_count = FinancialMovement.query.count()
    upload_count = UploadHistory.query.count()
    
    return render_template('admin/clear_movements.html', 
                          movement_count=movement_count, 
                          upload_count=upload_count)
