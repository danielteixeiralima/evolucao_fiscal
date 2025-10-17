import pandas as pd
import json
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)

class FinancialDataProcessor:
    """Process Excel files containing financial movement data"""
    
    # Complete column mapping for all 113 fields
    COLUMN_MAPPING = {
        'internalId': 'internal_id',
        'companyId': 'company_id',
        'movementId': 'movement_id',
        'branchId': 'branch_id',
        'warehouseCode': 'warehouse_code',
        'destinyWarehouseCode': 'destiny_warehouse_code',
        'number': 'number',
        'series': 'series',
        'movementTypeCode': 'movement_type_code',
        'type': 'type',
        'status': 'status',
        'printed': 'printed',
        'documentPrinted': 'document_printed',
        'billPrinted': 'bill_printed',
        'registerDate': 'register_date',
        'exitDate': 'exit_date',
        'commercialRepresentativeCharge': 'commercial_representative_charge',
        'grossValue': 'gross_value',
        'netValue': 'net_value',
        'informedNetValue': 'informed_net_value',
        'otherValues': 'other_values',
        'discountPercentage': 'discount_percentage',
        'expensePercentage': 'expense_percentage',
        'expenseValue': 'expense_value',
        'extraPercentage1': 'extra_percentage1',
        'extraValue1': 'extra_value1',
        'extraPercentage2': 'extra_percentage2',
        'extraValue2': 'extra_value2',
        'transportedProductNetWeight': 'transported_product_net_weight',
        'transportedProductGrossWeight': 'transported_product_gross_weight',
        'classificationTable5Code': 'classification_table5_code',
        'financialOptionalTable2Code': 'financial_optional_table2_code',
        'netValueCurrencyCode': 'net_value_currency_code',
        'date': 'date',
        'hasGeneratedBill': 'has_generated_bill',
        'auxCustomerVendorCode': 'aux_customer_vendor_code',
        'auxCustomerVendorCompanyId': 'aux_customer_vendor_company_id',
        'costCenterCode': 'cost_center_code',
        'salesman1Code': 'salesman1_code',
        'chargePercentage': 'charge_percentage',
        'salesman2ChargePercentage': 'salesman2_charge_percentage',
        'salesman3ChargePercentage': 'salesman3_charge_percentage',
        'salesman4ChargePercentage': 'salesman4_charge_percentage',
        'userCode': 'user_code',
        'destinyBranchId': 'destiny_branch_id',
        'lotGenerated': 'lot_generated',
        'accountingExportStatus': 'accounting_export_status',
        'deliveryDate': 'delivery_date',
        'hasGeneratedWorkAccount': 'has_generated_work_account',
        'workAccountGenerated': 'work_account_generated',
        'lastEditTime': 'last_edit_time',
        'indicateObjectUse': 'indicate_object_use',
        'bonumIntegrated': 'bonum_integrated',
        'processedFlag': 'processed_flag',
        'icmsDeductionValue': 'icms_deduction_value',
        'creationUser': 'creation_user',
        'creationDate': 'creation_date',
        'emailStatus': 'email_status',
        'internalGrossValue': 'internal_gross_value',
        'otherCompanyINSSBaseValue': 'other_company_inss_base_value',
        'conditionalDiscountValue': 'conditional_discount_value',
        'conditionalExpenseValue': 'conditional_expense_value',
        'affectStockOrder': 'affect_stock_order',
        'commercialAutomationExported': 'commercial_automation_exported',
        'aplicationIntegration': 'aplication_integration',
        'entryDate': 'entry_date',
        'extemporaneous': 'extemporaneous',
        'merchandiseValue': 'merchandise_value',
        'usesFinancialValueApportionment': 'uses_financial_value_apportionment',
        'conclusionFlag': 'conclusion_flag',
        'paradigmaStatus': 'paradigma_status',
        'paradigmaAutoIntegrated': 'paradigma_auto_integrated',
        'originalGrossValue': 'original_gross_value',
        'originalNetValue': 'original_net_value',
        'originalOtherValues': 'original_other_values',
        'operationId': 'operation_id',
        'scpBranchId': 'scp_branch_id',
        'movementItems': 'movement_items',
        'payments': 'payments',
        'costCenterApportionments': 'cost_center_apportionments',
        'departmentApportionments': 'department_apportionments',
        'taxes': 'taxes',
        'fiscal': 'fiscal',
        'norm': 'norm',
        'cargoComponent': 'cargo_component',
        'thirdPartyNF': 'third_party_nf',
        'safetyDevice': 'safety_device',
        'nfe': 'nfe',
        'inputCTRC': 'input_ctrc',
        'outputCTRC': 'output_ctrc',
        'ctrc': 'ctrc',
        'transportData': 'transport_data',
        'documentAuthorization': 'document_authorization',
        'judicialProcess': 'judicial_process',
        'serviceOrder': 'service_order',
        'relatedMovement': 'related_movement',
        'exportRelatedMovement': 'export_related_movement',
        'linkedMovement': 'linked_movement',
        'cTe': 'c_te',
        'eaiIntegration': 'eai_integration',
        'electronicInvoiceFreeFields': 'electronic_invoice_free_fields',
        'customerVendorCode': 'customer_vendor_code',
        'paymentTermCode': 'payment_term_code',
        'observation': 'observation',
        'financialOptionalTable1Code': 'financial_optional_table1_code',
        'financialEntryMovementId': 'financial_entry_movement_id',
        'generatedEntryNumber': 'generated_entry_number',
        'openEntryNumber': 'open_entry_number',
        'cashAccountCode': 'cash_account_code',
        'customerVendorCompanyId': 'customer_vendor_company_id',
        'fluxusGroupedFlag': 'fluxus_grouped_flag',
        'cashAccountCompanyId': 'cash_account_company_id',
        'longHistory': 'long_history',
    }
    
    # JSON fields that need special processing
    JSON_FIELDS = {
        'movement_items', 'payments', 'cost_center_apportionments', 'department_apportionments',
        'taxes', 'fiscal', 'norm', 'cargo_component', 'third_party_nf', 'safety_device',
        'nfe', 'input_ctrc', 'output_ctrc', 'ctrc', 'transport_data', 'document_authorization',
        'judicial_process', 'service_order', 'related_movement', 'export_related_movement',
        'linked_movement', 'c_te', 'eai_integration', 'electronic_invoice_free_fields'
    }
    
    # Date fields that need special processing
    DATE_FIELDS = {
        'register_date', 'exit_date', 'delivery_date', 'creation_date', 'last_edit_time', 
        'date', 'entry_date'
    }

    def __init__(self):
        self.batch_id = None

    def process_file(self, file_path: str, user_id: int) -> Tuple[str, int, int, List[str], List[dict]]:
        """
        Process an Excel file and return results
        
        Returns:
            Tuple containing:
            - batch_id (str): Unique identifier for this upload batch
            - success_count (int): Number of successfully processed records
            - error_count (int): Number of records with errors
            - errors (List[str]): List of error messages
            - processed_data (List[dict]): List of processed records for database insertion
        """
        from app import db
        from models import FinancialMovement, UploadHistory
        
        self.batch_id = str(uuid.uuid4())
        errors = []
        processed_data = []
        success_count = 0
        error_count = 0
        
        try:
            # Read Excel file
            logger.info(f"Reading Excel file: {file_path}")
            df = pd.read_excel(file_path)
            logger.info(f"Read Excel file with {len(df)} rows")
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    # Convert row to dictionary and map columns
                    record_data = self._process_row(row)
                    
                    # Add tracking fields
                    record_data['upload_batch_id'] = self.batch_id
                    record_data['uploaded_by'] = user_id
                    record_data['uploaded_at'] = datetime.utcnow()
                    
                    processed_data.append(record_data)
                    success_count += 1
                    
                except Exception as e:
                    error_msg = f"Row {index + 1}: {str(e)}"
                    errors.append(error_msg)
                    error_count += 1
                    logger.error(error_msg)
            
            # Create database records
            if processed_data:
                self._save_to_database(processed_data, file_path, user_id, success_count, error_count, errors)
            
            return self.batch_id, success_count, error_count, errors, processed_data
            
        except Exception as e:
            error_msg = f"Failed to process file: {str(e)}"
            logger.error(error_msg)
            return self.batch_id or str(uuid.uuid4()), 0, 1, [error_msg], []

    def _process_row(self, row: pd.Series) -> Dict[str, Any]:
        """Process a single row of data"""
        processed = {}
        
        for excel_col, db_col in self.COLUMN_MAPPING.items():
            if excel_col in row:
                value = row[excel_col]
                
                # Handle None/NaN values
                if pd.isna(value):
                    processed[db_col] = None
                    continue
                
                # Process JSON fields
                if db_col in self.JSON_FIELDS:
                    processed[db_col] = self._process_json_field(value)
                
                # Process date fields
                elif db_col in self.DATE_FIELDS:
                    processed[db_col] = self._process_date_field(value)
                
                # Process boolean fields
                elif isinstance(value, bool) or db_col.endswith('_flag') or db_col.startswith('has_'):
                    processed[db_col] = bool(value) if value is not None else None
                
                # Process numeric fields
                elif isinstance(value, (int, float)):
                    processed[db_col] = value
                
                # Process string fields
                else:
                    processed[db_col] = str(value) if value is not None else None
            else:
                processed[db_col] = None
                
        return processed

    def _process_json_field(self, value: Any) -> str:
        """Process JSON field values"""
        if value is None or pd.isna(value):
            return None
        
        if isinstance(value, str):
            # If it's already a JSON string, return as is
            try:
                json.loads(value)
                return value
            except (json.JSONDecodeError, TypeError):
                return json.dumps([])
        
        if isinstance(value, list):
            return json.dumps(value)
        
        # For other types, wrap in array
        return json.dumps([value] if value else [])

    def _process_date_field(self, value: Any) -> datetime:
        """Process date field values"""
        if value is None or pd.isna(value):
            return None
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                try:
                    return pd.to_datetime(value).to_pydatetime()
                except (ValueError, TypeError):
                    return None
        
        if hasattr(value, 'to_pydatetime'):
            return value.to_pydatetime()
        
        return None

    def _save_to_database(self, processed_data: List[Dict], filename: str, 
                         user_id: int, success_count: int, error_count: int, errors: List[str]):
        """Save processed data to database"""
        from app import db
        from models import FinancialMovement, UploadHistory
        
        # Create upload history record
        upload_history = UploadHistory(
            batch_id=self.batch_id,
            filename=filename.split('/')[-1],  # Get just filename without path
            uploaded_by=user_id,
            total_rows=len(processed_data),
            success_count=success_count,
            error_count=error_count,
            errors=json.dumps(errors) if errors else None,
            status='completed' if error_count == 0 else 'completed_with_errors'
        )
        
        # Create movement records
        movements = [FinancialMovement(**data) for data in processed_data]
        
        # Save to database
        db.session.add(upload_history)
        db.session.add_all(movements)
        db.session.commit()
        
        logger.info(f"Saved {success_count} records to database with batch_id {self.batch_id}")