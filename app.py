import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_migrate import Migrate

# ---------------------------------------------
# CONFIGURAÇÃO DE LOG
# ---------------------------------------------
logging.basicConfig(level=logging.DEBUG)


# ---------------------------------------------
# BASE MODEL (usada pelo SQLAlchemy 2.0)
# ---------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------
# INICIALIZAÇÃO DAS EXTENSÕES
# ---------------------------------------------
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
migrate = Migrate()


# ---------------------------------------------
# FUNÇÃO FACTORY PRINCIPAL DO APP
# ---------------------------------------------
def create_app():
    app = Flask(__name__)
    @app.template_filter('translate_field')
    def translate_field(field_name):
        """Traduz os nomes técnicos dos campos JSON para português."""
        labels = {
            'companyId': 'Empresa',
            'movementId': 'Movimento',
            'paymentSequentialId': 'Sequência do Pagamento',
            'debitCredit': 'Débito/Crédito',
            'value': 'Valor',
            'paymentType': 'Tipo de Pagamento',
            'dueDate': 'Data de Vencimento',
            'paymentFormId': 'Forma de Pagamento (ID)',
            'entryId': 'Lançamento',
            'cashAccountCompanyId': 'Empresa da Conta Caixa',
            'cashAccount': 'Conta Caixa',
            'administrateTax': 'Administrar Imposto',
            'multiplePayment': 'Pagamento Múltiplo',
            'paymentFormType': 'Tipo de Forma de Pagamento',
            'paymentFormDescription': 'Descrição da Forma de Pagamento',
            'movementItemSequentialId': 'Seq. do Item do Movimento',
            'taxId': 'ID do Imposto',
            'calculationBasis': 'Base de Cálculo',
            'aliquot': 'Alíquota (%)',
            'fullBase': 'Base Completa',
            'edited': 'Editado',
            'description': 'Descrição',
            'registerDate': 'Data de Registro',
            'deliveryDate': 'Data de Entrega',
            'entryDate': 'Data de Entrada',
            'exitDate': 'Data de Saída',
            'creationDate': 'Data de Criação'
        }
        return labels.get(field_name, field_name)

    # -----------------------------
    # CONFIGURAÇÕES GERAIS
    # -----------------------------
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///financial_data.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB
    app.config["UPLOAD_FOLDER"] = "uploads"

    # Garante que a pasta de upload existe
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # -----------------------------
    # INICIALIZA AS EXTENSÕES
    # -----------------------------
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."

    # Corrige URLs em servidores com proxy/reverso (Nginx etc.)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # -----------------------------
    # REGISTRA MODELOS E USUÁRIO ADMIN PADRÃO
    # -----------------------------
    with app.app_context():
        import models  # importa todos os modelos para registrar

        db.create_all()  # cria tabelas se ainda não existirem

        # Cria usuário admin se não existir
        from models import User
        from werkzeug.security import generate_password_hash

        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@example.com",
                is_admin=True,
                password_hash=generate_password_hash("admin123"),
            )
            db.session.add(admin)
            db.session.commit()
            logging.info("✅ Created admin user: admin / admin123")

    # -----------------------------
    # REGISTRA BLUEPRINTS
    # -----------------------------
    from routes import main_bp, admin_bp, auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(auth_bp, url_prefix="/auth")

    return app


# ---------------------------------------------
# INSTÂNCIA GLOBAL DO APP (usada pelo flask run)
# ---------------------------------------------
app = create_app()
