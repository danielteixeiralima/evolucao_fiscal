import sqlite3
import shutil
import os

# 1. Overwrite main DB with V2 DB
src = 'instance/financial_data_v2.db'
dst = 'instance/financial_data.db'

if not os.path.exists(src):
    print(f"Error: {src} not found!")
    exit(1)

print(f"Copying {src} to {dst}...")
shutil.copy2(src, dst)

# 2. Connect to the new main DB
conn = sqlite3.connect(dst)
cursor = conn.cursor()

# 3. List of tables to migrate
tables_map = {
    'company_v2': 'company',
    'branch_v2': 'branch',
    'cost_center_v2': 'cost_center',
    'product_v2': 'product',
    'customer_vendor_v2': 'customer_vendor',
    'financial_movement_v2': 'financial_movement',
    'movement_item_v2': 'movement_item',
    'cost_center_apportionment_v2': 'cost_center_apportionment',
    'budgetary_nature_v2': 'budgetary_nature'
}

print("Migrating tables...")

# Disable foreign keys to allow dropping/renaming
cursor.execute("PRAGMA foreign_keys = OFF;")

for v2_name, v1_name in tables_map.items():
    # Drop v1 table if it exists
    cursor.execute(f"DROP TABLE IF EXISTS {v1_name}")
    
    # Rename v2 table to v1
    try:
        cursor.execute(f"ALTER TABLE {v2_name} RENAME TO {v1_name}")
        print(f"  Renamed {v2_name} -> {v1_name}")
    except sqlite3.OperationalError as e:
        print(f"  Skipping {v2_name}: {e} (maybe already renamed or doesn't exist)")

# Re-enable foreign keys
cursor.execute("PRAGMA foreign_keys = ON;")

conn.commit()
conn.close()
print("Migration done!")
