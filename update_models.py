#!/usr/bin/env python3
"""
Script to generate complete FinancialMovement model with all 113 fields
"""

# All 113 fields from the Excel file
EXCEL_COLUMNS = [
    'internalId', 'companyId', 'movementId', 'branchId', 'warehouseCode', 'destinyWarehouseCode', 
    'number', 'series', 'movementTypeCode', 'type', 'status', 'printed', 'documentPrinted', 
    'billPrinted', 'registerDate', 'exitDate', 'commercialRepresentativeCharge', 'grossValue', 
    'netValue', 'informedNetValue', 'otherValues', 'discountPercentage', 'expensePercentage', 
    'expenseValue', 'extraPercentage1', 'extraValue1', 'extraPercentage2', 'extraValue2', 
    'transportedProductNetWeight', 'transportedProductGrossWeight', 'classificationTable5Code', 
    'financialOptionalTable2Code', 'netValueCurrencyCode', 'date', 'hasGeneratedBill', 
    'auxCustomerVendorCode', 'auxCustomerVendorCompanyId', 'costCenterCode', 'salesman1Code', 
    'chargePercentage', 'salesman2ChargePercentage', 'salesman3ChargePercentage', 
    'salesman4ChargePercentage', 'userCode', 'destinyBranchId', 'lotGenerated', 
    'accountingExportStatus', 'deliveryDate', 'hasGeneratedWorkAccount', 'workAccountGenerated', 
    'lastEditTime', 'indicateObjectUse', 'bonumIntegrated', 'processedFlag', 'icmsDeductionValue', 
    'creationUser', 'creationDate', 'emailStatus', 'internalGrossValue', 'otherCompanyINSSBaseValue', 
    'conditionalDiscountValue', 'conditionalExpenseValue', 'affectStockOrder', 
    'commercialAutomationExported', 'aplicationIntegration', 'entryDate', 'extemporaneous', 
    'merchandiseValue', 'usesFinancialValueApportionment', 'conclusionFlag', 'paradigmaStatus', 
    'paradigmaAutoIntegrated', 'originalGrossValue', 'originalNetValue', 'originalOtherValues', 
    'operationId', 'scpBranchId', 'movementItems', 'payments', 'costCenterApportionments', 
    'departmentApportionments', 'taxes', 'fiscal', 'norm', 'cargoComponent', 'thirdPartyNF', 
    'safetyDevice', 'nfe', 'inputCTRC', 'outputCTRC', 'ctrc', 'transportData', 
    'documentAuthorization', 'judicialProcess', 'serviceOrder', 'relatedMovement', 
    'exportRelatedMovement', 'linkedMovement', 'cTe', 'eaiIntegration', 
    'electronicInvoiceFreeFields', 'customerVendorCode', 'paymentTermCode', 'observation', 
    'financialOptionalTable1Code', 'financialEntryMovementId', 'generatedEntryNumber', 
    'openEntryNumber', 'cashAccountCode', 'customerVendorCompanyId', 'fluxusGroupedFlag', 
    'cashAccountCompanyId', 'longHistory'
]

def camel_to_snake(name):
    """Convert camelCase to snake_case"""
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

# JSON fields that should be stored as JSON text
JSON_FIELDS = {
    'movementItems', 'payments', 'costCenterApportionments', 'departmentApportionments', 
    'taxes', 'fiscal', 'norm', 'cargoComponent', 'thirdPartyNF', 'safetyDevice', 
    'nfe', 'inputCTRC', 'outputCTRC', 'ctrc', 'transportData', 'documentAuthorization', 
    'judicialProcess', 'serviceOrder', 'relatedMovement', 'exportRelatedMovement', 
    'linkedMovement', 'cTe', 'eaiIntegration', 'electronicInvoiceFreeFields'
}

# Generate column mapping
print("# Complete column mapping for file_processor.py:")
print("COLUMN_MAPPING = {")
for col in EXCEL_COLUMNS:
    snake_name = camel_to_snake(col)
    print(f"    '{col}': '{snake_name}',")
print("}")
print()

# Generate model fields
print("# Fields for FinancialMovement model:")
for col in EXCEL_COLUMNS:
    snake_name = camel_to_snake(col)
    
    if col in JSON_FIELDS:
        print(f"    {snake_name} = db.Column(db.Text, nullable=True)  # JSON field")
    elif col.endswith('Date') or col.endswith('Time'):
        print(f"    {snake_name} = db.Column(db.DateTime, nullable=True)")
    elif col.endswith('Id') or col.endswith('Code') or col.endswith('Number'):
        print(f"    {snake_name} = db.Column(db.String(50), nullable=True)")
    elif col.endswith('Value') or col.endswith('Percentage') or col.endswith('Charge') or col.endswith('Weight'):
        print(f"    {snake_name} = db.Column(db.Float, nullable=True)")
    elif col.endswith('Flag') or col.startswith('has') or col.startswith('is') or col in ['printed', 'documentPrinted', 'billPrinted', 'bonumIntegrated', 'processedFlag', 'usesFinancialValueApportionment', 'paradigmaAutoIntegrated']:
        print(f"    {snake_name} = db.Column(db.Boolean, nullable=True)")
    else:
        print(f"    {snake_name} = db.Column(db.String(255), nullable=True)")

print()
print("# JSON field processing methods:")
print("""    def get_json_field(self, field_name):
        \"\"\"Get a JSON field as a Python object\"\"\"
        field_value = getattr(self, field_name, None)
        if field_value:
            try:
                return json.loads(field_value) if isinstance(field_value, str) else field_value
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def set_json_field(self, field_name, value):
        \"\"\"Set a JSON field from a Python object\"\"\"
        if value:
            json_value = json.dumps(value) if not isinstance(value, str) else value
            setattr(self, field_name, json_value)
        else:
            setattr(self, field_name, None)""")