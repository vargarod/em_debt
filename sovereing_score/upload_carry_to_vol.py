"""
Create table and upload carry-to-volatility metrics to PostgreSQL
Using Method 2: Volatility of spread levels (bps)
"""
import pandas as pd
import psycopg2
import os
from datetime import datetime

# Get DB password
db_password = os.environ.get('DB_PASSWORD')
if not db_password:
    print("ERROR: DB_PASSWORD not set")
    exit(1)

print("="*80)
print("CREATING TABLE AND UPLOADING CARRY-TO-VOL METRICS (METHOD 2)")
print("="*80)
print()

# Auto-detect latest month-end date from database
print("Detecting latest month-end date from database...")
conn_temp = psycopg2.connect(
    host='gwamdlquantapps-prod-postgresql-server.postgres.database.azure.com',
    port=5432,
    database='postgres',
    user='securitized_team',
    password=db_password,
    sslmode='require'
)
cursor_temp = conn_temp.cursor()
cursor_temp.execute("""
    SELECT MAX(date) 
    FROM securitized_research.emd_sovereign_score 
    WHERE EXTRACT(DAY FROM date + INTERVAL '1 day') = 1
""")
as_of_date = cursor_temp.fetchone()[0]
cursor_temp.close()
conn_temp.close()

if not as_of_date:
    print("ERROR: No month-end date found in database")
    exit(1)

as_of_date = as_of_date.strftime('%Y-%m-%d')
print(f"✓ As-of Date: {as_of_date} (latest month-end)")
print()

# Load computed metrics
metrics_file = 'c:\\code\\em_debt\\sovereing_score\\carry_to_vol_comparison.csv'
df = pd.read_csv(metrics_file)

print(f"✓ Loaded {len(df)} records from {metrics_file}")
print()

# Connect to database
conn = psycopg2.connect(
    host='gwamdlquantapps-prod-postgresql-server.postgres.database.azure.com',
    port=5432,
    database='postgres',
    user='securitized_team',
    password=db_password,
    sslmode='require'
)

cursor = conn.cursor()

# Create table
print("Creating table securitized_research.emd_country_carry_to_vol...")
create_table_sql = """
CREATE TABLE IF NOT EXISTS securitized_research.emd_country_carry_to_vol (
    country_code VARCHAR(10),
    as_of_date DATE,
    country VARCHAR(100),
    carry_bps NUMERIC(10, 3),
    vol_bps NUMERIC(10, 3),
    carry_to_vol NUMERIC(10, 6),
    data_points INTEGER,
    date_range VARCHAR(50),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (country_code, as_of_date)
)
"""

cursor.execute(create_table_sql)
conn.commit()
print("✓ Table created (or already exists)")
print()

# Clear existing data for this date
print(f"Clearing existing data for {as_of_date}...")
cursor.execute("DELETE FROM securitized_research.emd_country_carry_to_vol WHERE as_of_date = %s", (as_of_date,))
deleted_rows = cursor.rowcount
print(f"✓ Deleted {deleted_rows} existing records for {as_of_date}")
print()

# Insert new data
print("Inserting new metrics...")
insert_sql = """
INSERT INTO securitized_research.emd_country_carry_to_vol 
    (country_code, as_of_date, country, carry_bps, vol_bps, carry_to_vol, 
     vol_returns_annual, carry_to_vol_return_based, data_points, date_range)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

inserted = 0
for _, row in df.iterrows():
    # Handle NULL values for return-based metrics
    vol_returns = row['vol_returns_annual'] if pd.notna(row['vol_returns_annual']) else None
    ctv_return = row['carry_to_vol_return_based'] if pd.notna(row['carry_to_vol_return_based']) else None
    
    cursor.execute(insert_sql, (
        row['country_code'],
        as_of_date,
        row['country'],
        float(row['carry_bps']),
        float(row['vol_bps']),
        float(row['carry_to_vol']),
        float(vol_returns) if vol_returns is not None else None,
        float(ctv_return) if ctv_return is not None else None,
        int(row['data_points']),
        row['date_range']
    ))
    inserted += 1

conn.commit()
print(f"✓ Inserted {inserted} records")
print()

# Verify upload
cursor.execute("SELECT COUNT(*) FROM securitized_research.emd_country_carry_to_vol")
count = cursor.fetchone()[0]
print(f"✓ Verification: {count} records in table")
print()

# Show top 10
print(f"TOP 10 BY CARRY-TO-VOL (from database, as-of {as_of_date}):")
cursor.execute("""
    SELECT country_code, country, carry_bps, vol_bps, carry_to_vol
    FROM securitized_research.emd_country_carry_to_vol
    WHERE as_of_date = %s
    ORDER BY carry_to_vol DESC
    LIMIT 10
""", (as_of_date,))
for row in cursor.fetchall():
    print(f"  {row[1]:20s} ({row[0]}): Carry={row[2]:6.0f}bps, Vol={row[3]:6.0f}bps, C/V={row[4]:.3f}")

print()

# Close connection
cursor.close()
conn.close()

print("="*80)
print("✓ Upload completed successfully!")
print("="*80)
print()
print("Table: securitized_research.emd_country_carry_to_vol")
print("Columns: country_code, as_of_date, country, carry_bps, vol_bps, carry_to_vol, data_points, date_range, updated_at")
print(f"Primary Key: (country_code, as_of_date)")
print(f"This load as-of: {as_of_date}")
print()
print("METHOD: Volatility of spread levels (bps)")
print("  - carry_bps: Current yield in basis points")
print("  - vol_bps: Annualized volatility of z_spread in basis points")
print("  - carry_to_vol: Ratio of carry to volatility (dimensionless)")
print()
print("NOTE: Run this script monthly with updated as_of_date to build time series")
