import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_, desc
from app import db, login_manager
from models import User, FinancialMovement, UploadHistory
from forms import LoginForm, UserForm, EditUserForm, FileUploadForm
from file_processor import FinancialDataProcessor
import logging

logger = logging.getLogger(__name__)

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
    recent_movements = FinancialMovement.query.order_by(desc(FinancialMovement.uploaded_at)).limit(10).all()
    return render_template('index.html', movements=recent_movements)

@main_bp.route('/movements')
@login_required
def movements():
    """List all movements with search, filters and pagination"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    company_filter = request.args.get('company', '', type=str)
    branch_filter = request.args.get('branch', '', type=str)
    status_filter = request.args.get('status', '', type=str)
    per_page = 25
    
    query = FinancialMovement.query
    
    # Apply search filter
    if search:
        query = query.filter(
            or_(
                FinancialMovement.internal_id.contains(search),
                FinancialMovement.number.contains(search),
                FinancialMovement.aux_customer_vendor_code.contains(search),
                FinancialMovement.observation.contains(search)
            )
        )
    
    # Apply company filter
    if company_filter:
        query = query.filter(FinancialMovement.empresa_nome.contains(company_filter))
    
    # Apply branch filter  
    if branch_filter:
        query = query.filter(FinancialMovement.filial_nome.contains(branch_filter))
    
    # Apply status filter
    if status_filter:
        query = query.filter(FinancialMovement.status == status_filter)
    
    movements = query.order_by(desc(FinancialMovement.uploaded_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get unique values for filter dropdowns
    companies = db.session.query(FinancialMovement.empresa_nome).distinct().filter(
        FinancialMovement.empresa_nome.isnot(None)
    ).order_by(FinancialMovement.empresa_nome).all()
    companies = [c[0] for c in companies if c[0]]
    
    branches = db.session.query(FinancialMovement.filial_nome).distinct().filter(
        FinancialMovement.filial_nome.isnot(None)
    ).order_by(FinancialMovement.filial_nome).all()
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
                         statuses=statuses)

@main_bp.route('/movements/<int:id>')
@login_required
def movement_detail(id):
    """Show detailed view of a specific movement"""
    movement = FinancialMovement.query.get_or_404(id)
    return render_template('movements/detail.html', movement=movement)

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
                upload_count = UploadHistory.query.count()
                
                db.session.query(FinancialMovement).delete()
                db.session.query(UploadHistory).delete()
                db.session.commit()
                
                flash(f'All data deleted successfully! {movement_count} movements and {upload_count} upload records removed.', 'success')
                return redirect(url_for('main.movements'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error deleting data: {str(e)}', 'error')
                logger.error(f"Error deleting all movements: {str(e)}")
                
        else:
            flash('Invalid confirmation text. Type exactly "delete all movements" to confirm.', 'warning')
    
    # Count current records for display
    movement_count = FinancialMovement.query.count()
    upload_count = UploadHistory.query.count()
    
    return render_template('movements/delete_all.html', 
                          movement_count=movement_count, 
                          upload_count=upload_count)

@main_bp.route('/api/movements/<int:id>/json/<field>')
@login_required
def get_movement_json_field(id, field):
    """API endpoint to get formatted JSON field data"""
    movement = FinancialMovement.query.get_or_404(id)
    json_data = movement.get_json_field(field)
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
        file = form.file.data
        filename = secure_filename(file.filename)
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        
        try:
            # Save file
            file.save(file_path)
            
            # Process file
            # Process file
            processor = FinancialDataProcessor()
            batch_id, success_count, error_count, errors, processed_data = processor.process_file(
                file_path, current_user.id
            )

            # 🔹 NOVO: tenta fechar handle explicitamente (se processor tiver método close)
            if hasattr(processor, "close"):
                try:
                    processor.close()
                except Exception:
                    pass

            # 🔹 NOVO: adiar a exclusão para só depois
            import time
            for i in range(5):  # tenta até 5 vezes
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    break
                except PermissionError:
                    time.sleep(0.5)  # espera meio segundo e tenta de novo

            
            if error_count > 0:
                flash(f'File processed with {success_count} successful records and {error_count} errors. Check upload history for details.', 'warning')
            else:
                flash(f'File uploaded successfully! {success_count} records processed.', 'success')
            
            return redirect(url_for('admin.upload_history'))
            
        except Exception as e:
            # Clean up file if processing failed
            if os.path.exists(file_path):
                os.remove(file_path)
            flash(f'Error processing file: {str(e)}', 'error')
            logger.error(f"Upload processing error: {str(e)}")
    
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
                # Delete all financial movements and their upload history
                movement_count = FinancialMovement.query.count()
                upload_count = UploadHistory.query.count()
                
                db.session.query(FinancialMovement).delete()
                db.session.query(UploadHistory).delete()
                db.session.commit()
                
                flash(f'Database cleared successfully! {movement_count} financial movements and {upload_count} upload records deleted.', 'success')
                return redirect(url_for('admin.dashboard'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error clearing database: {str(e)}', 'error')
                
        else:
            flash('Invalid confirmation text. Type exactly "delete all movements" to confirm.', 'warning')
    
    # Count current records
    movement_count = FinancialMovement.query.count()
    upload_count = UploadHistory.query.count()
    
    return render_template('admin/clear_movements.html', 
                          movement_count=movement_count, 
                          upload_count=upload_count)
