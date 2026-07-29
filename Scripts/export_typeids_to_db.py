import csv
import sqlite3
import os

"""
This script seeds the SQLite database with all marketable type IDs from a CSV file.
It is intended to be run once during the initial setup of the application.
It reads from `invTypes2.csv`, filters for items that have a `marketGroupID`,
and inserts them into the `market_prices` table.
"""

# --- Configuration ---
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
csv_file = os.path.join(root_dir, 'invTypes2.csv')
db_file = os.path.join(root_dir, 'market_prices.db')
table_name = 'market_prices'

# Connect to SQLite DB
conn = sqlite3.connect(db_file)
cur = conn.cursor()

# Ensure the market_prices table exists with the correct schema.
cur.execute(f'''
    CREATE TABLE IF NOT EXISTS {table_name} (
        typeID INTEGER PRIMARY KEY,
        buy_price REAL,
        sell_price REAL,
        updated_at TEXT
    )
''')

# Clear all existing entries from the table to ensure a fresh import.
cur.execute(f'DELETE FROM {table_name}')

# Read the CSV file and extract typeIDs for items that are on the market.
with open(csv_file, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    type_ids = [row['typeID'] for row in reader if row.get('marketGroupID') and row['marketGroupID'] != 'None']

# Insert the filtered typeIDs into the database. `INSERT OR IGNORE` prevents errors on duplicates.
for tid in type_ids:
    cur.execute(f'INSERT OR IGNORE INTO {table_name} (typeID) VALUES (?)', (tid,))

conn.commit()
conn.close()

print(f"Inserted {len(type_ids)} typeIDs with marketGroupID into {table_name} table in {db_file}")
