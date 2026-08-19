"""
Upload EM Sovereign Sub-Index Prices to PostgreSQL
Reads from Excel output and uploads to database
Replaces existing data for the date (DELETE + INSERT pattern)
"""
import pandas as pd
import psycopg2
import os

print("="*80)
print("UPLOAD SUB-INDEX PRICES TO POSTGRESQL")
print("="*80)

# Load data from Excel
input_file = r'c:\code\em_debt\sovereing_score\input\sub_index_prices_output.xlsx'
print(f"Loading data from: {input_file}")

df = pd.read_excel(input_file)
print(f"✓ Loaded {len(df)} records")

# Get the date from the data
data_date = df['date'].iloc[0] if len(df) > 0 else None
print(f"Data date: {data_date}")
print()

# Get DB password
db_password = os.environ.get('DB_PASSWORD')
if not db_password:
    print("ERROR: DB_PASSWORD environment variable not set")
    exit(1)

# Connect to database
print("Connecting to PostgreSQL database...")
conn = psycopg2.connect(
    host='gwamdlquantapps-prod-postgresql-server.postgres.database.azure.com',
    port=5432,
    database='postgres',
    user='securitized_team',
    password=db_password,
    sslmode='require'
)
print("✓ Connected successfully")
print()

cursor = conn.cursor()

# Delete existing data for this date
print(f"Replacing data for date: {data_date}")
delete_sql = "DELETE FROM securitized_research.emd_sub_index_prices WHERE date = %s"
cursor.execute(delete_sql, (data_date,))
deleted_count = cursor.rowcount
print(f"Deleted {deleted_count} existing records for date {data_date}")
print()

# Insert new data
print("Uploading new data...")
insert_sql = """
INSERT INTO securitized_research.emd_sub_index_prices 
    (country_code, date, country, sub_index_ticker, sub_index_price)
VALUES (%s, %s, %s, %s, %s)
"""

inserted = 0
for _, row in df.iterrows():
    cursor.execute(insert_sql, (
        row['country_code'],
        row['date'],
        row['country'],
        row['sub_index_ticker'],
        float(row['sub_index_price'])
    ))
    inserted += 1

print(f"Inserted {inserted} records")
print()

# Commit transaction
conn.commit()
print("✓ Transaction committed successfully")
print()

# Verify upload
verify_sql = """
SELECT COUNT(*) 
FROM securitized_research.emd_sub_index_prices 
WHERE date = %s
"""
cursor.execute(verify_sql, (data_date,))
count = cursor.fetchone()[0]

print("="*80)
print("UPLOAD SUMMARY")
print("="*80)
print(f"Records in database for {data_date}: {count}")
print("✓ Upload completed successfully!")
print()

# Show sample of uploaded data
sample_sql = """
SELECT country_code, country, sub_index_price
FROM securitized_research.emd_sub_index_prices
WHERE date = %s
ORDER BY country_code
LIMIT 10
"""
cursor.execute(sample_sql, (data_date,))
samples = cursor.fetchall()

print("Sample records:")
for row in samples:
    print(f"  {row[0]}: {row[1]:<30} Price={row[2]:.3f}")

# Close connection
cursor.close()
conn.close()
print()
print("Database connection closed")
print("All done!")
