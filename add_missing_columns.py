import sqlite3

db_path = 'instance/financial_data.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

columns_to_add = [
    ("upload_batch_id", "VARCHAR(36)"),
    ("uploaded_by", "INTEGER REFERENCES user(id)"),
    ("uploaded_at", "DATETIME")
]

print("Adding missing columns to financial_movement...")

for col_name, col_type in columns_to_add:
    try:
        cursor.execute(f"ALTER TABLE financial_movement ADD COLUMN {col_name} {col_type}")
        print(f"  Added column: {col_name}")
    except sqlite3.OperationalError as e:
        print(f"  Skipping {col_name}: {e} (likely already exists)")

conn.commit()
conn.close()
print("Done!")
