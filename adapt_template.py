# -*- coding: utf-8 -*-
"""
Script para adaptar o template detail.html original para usar dados V2.
Mantém o layout idêntico, mas troca o acesso aos dados.
"""

# Mapeamento de campos do sistema antigo para V2
FIELD_MAPPINGS = {
    # Campos diretos do movimento
    'movement.company_id': 'movement.company.code',
    'movement.branch_id': 'movement.branch.code',
    'movement.customer_vendor_name': 'movement.customer_vendor.name if movement.customer_vendor else "-"',
    'movement.filial_nome': 'movement.branch.name',
    
    # Campos que já existem e não mudam
    'movement.internal_id': 'movement.internal_id',
    'movement.id': 'movement.id',
    'movement.number': 'movement.number',
    'movement.series': 'movement.series',
    'movement.movement_type_code': 'movement.movement_type_code',
    'movement.date': 'movement.date',
    'movement.status': 'movement.status',
    'movement.gross_value': 'movement.gross_value',
    'movement.net_value': 'movement.net_value',
    'movement.warehouse_code': 'movement.warehouse_code',
    'movement.observation': 'movement.observation',
}

# Lê o template original
with open('templates/movements/detail.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Substitui os campos
for old_field, new_field in FIELD_MAPPINGS.items():
    content = content.replace(old_field, new_field)

# Remove lógica de JSON parsing
# Procura por padrões como movement.get_json_field() e substitui

# Salva o novo template
with open('templates/movements_v2/detail.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Template adaptado com sucesso!")
print("📄 Arquivo: templates/movements_v2/detail.html")
