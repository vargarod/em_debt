"""
Upload carry-to-volatility metrics to PostgreSQL for PREVIOUS MONTH-END
This script automatically calculates the previous month-end date and uploads data for that date.
Designed to run 3-4 days after month-end when data is stable.
"""
import pandas as pd
import psycopg2
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Get DB password
db_password = os.environ.get('DB_PASSWORD')
if not db_password:
    print("ERROR: DB_PASSWORD not set")
    exit(1)

print("="*80)
print("UPLOADING CARRY-TO-VOL METRICS FOR PREVIOUS MONTH-END")
print("="*80)
print()

# Calculate previous month-end date
today = datetime.now().date()
first_of_current_month = today.replace(day=1)
last_day_of_prev_month = first_of_current_month - relativedelta(days=1)
as_of_date = last_day_of_prev_month.strftime('%Y-%m-%d')

print(f"Today's date: {today}")
print(f"Previous month-end: {as_of_date}")
print()

# Verify data exists in sovereign_score table for this date
conn_check = psycopg2.connect(
    host='gwamdlquantapps-prod-postgresql-server.postgres.database.azure.com',
    port=5432,
    database='postgres',
    user='securitized_team',
    password=db_password,
    sslmode='require'
)
cursor_check = conn_check.cursor()
cursor_check.execute("""
    SELECT COUNT(*) 
    FROM securitized_research.emd_sovereign_score 
    WHERE date = %s
""", (as_of_date,))
record_count = cursor_check.fetchone()[0]
cursor_check.close()
conn_check.close()

if record_count == 0:
    print(f"ERROR: No data found in emd_sovereign_score for {as_of_date}")
    print(f"Please ensure sovereign ratings data exists for this month-end date.")
    exit(1)

print(f"✓ Found {record_count} records in emd_sovereign_score for {as_of_date}")
print()

# Load computed metrics
metrics_file = 'c:\\code\\em_debt\\sovereing_score\\carry_to_vol_comparison.csv'
if not os.path.exists(metrics_file):
    print(f"ERROR: Metrics file not found: {metrics_file}")
    print(f"Please run compute_carry_to_vol_v2.py first")
    exit(1)

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

# Create table (if not exists)
print("Ensuring table securitized_research.emd_country_carry_to_vol exists...")
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
print("✓ Table ready")
print()

# Check if data already exists for this date
cursor.execute("SELECT COUNT(*) FROM securitized_research.emd_country_carry_to_vol WHERE as_of_date = %s", (as_of_date,))
existing_count = cursor.fetchone()[0]

if existing_count > 0:
    print(f"⚠ WARNING: {existing_count} records already exist for {as_of_date}")
    print(f"  These will be REPLACED with new data")
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
print(f"✓ Inserted {inserted} records for {as_of_date}")
print()

# Verify upload
cursor.execute("SELECT COUNT(*) FROM securitized_research.emd_country_carry_to_vol WHERE as_of_date = %s", (as_of_date,))
final_count = cursor.fetchone()[0]

print("="*80)
print(f"✓ UPLOAD COMPLETE")
print(f"  As-of Date: {as_of_date}")
print(f"  Total Records: {final_count}")
print("="*80)

cursor.close()
conn.close()
