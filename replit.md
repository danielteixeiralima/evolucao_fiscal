# Overview

This is a Flask-based financial data management system designed for importing, storing, and analyzing financial movement data from Excel files. The application features a role-based user system with administrative controls for user management and data upload capabilities. Users can browse and search through financial movement records, while administrators can upload Excel files containing structured financial data and manage user accounts.

**Recent Update (Aug 2025)**: System now supports complete 117-field Excel structure with all JSON fields properly processed and displayed. Added 4 new company/branch identification fields: `Empresa_Code`, `Empresa_Nome`, `Filial_Code`, `Filial_Nome`. Upload functionality fully working with batch tracking and error handling.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Web Framework
- **Flask** with SQLAlchemy ORM for database operations
- **Flask-Login** for user session management and authentication
- **Flask-WTF** for form handling and CSRF protection
- Blueprint-based routing for modular organization (main, admin, auth)

## Authentication & Authorization
- Password-based authentication with hashed storage using Werkzeug
- Role-based access control with admin/regular user distinction
- Session-based login with "remember me" functionality
- Decorator-based route protection for admin-only features

## Database Design
- SQLAlchemy with SQLite default (configurable via DATABASE_URL)
- **User model**: Basic user management with admin flags
- **FinancialMovement model**: Comprehensive financial transaction records with 40+ fields
- **UploadHistory model**: Tracks file upload batches and processing results
- Connection pooling and automatic table creation

## Data Processing
- **FinancialDataProcessor class**: Handles Excel file parsing and data transformation
- Column mapping from Excel headers to database fields
- Batch processing with error handling and validation
- Support for complex financial data structures including dates, currencies, and business logic fields

## Frontend Architecture
- Bootstrap 5 dark theme for responsive UI
- jQuery and DataTables for enhanced table functionality
- Template inheritance using Jinja2
- Progressive enhancement with JavaScript for user interactions
- File upload interface with drag-and-drop support

## File Management
- Secure file upload handling with size limits (50MB)
- Excel file processing with pandas
- Upload history tracking with success/failure metrics
- Organized upload directory structure

# External Dependencies

## Core Framework Dependencies
- **Flask**: Web application framework
- **SQLAlchemy/Flask-SQLAlchemy**: Database ORM and integration
- **Flask-Login**: User session management
- **Flask-WTF/WTForms**: Form handling and validation
- **Werkzeug**: WSGI utilities and security helpers

## Data Processing
- **pandas**: Excel file reading and data manipulation
- **openpyxl**: Excel file format support

## Frontend Libraries (CDN)
- **Bootstrap 5**: UI framework with dark theme
- **DataTables**: Enhanced table functionality
- **Font Awesome**: Icon library
- **jQuery**: JavaScript utilities

## Infrastructure
- **SQLite**: Default database (production can use PostgreSQL via DATABASE_URL)
- **ProxyFix**: WSGI middleware for proper URL generation behind proxies
- File system storage for uploaded Excel files

## Security Features
- CSRF protection through Flask-WTF
- Password hashing with Werkzeug
- Secure filename handling for uploads
- Session-based authentication with configurable secrets