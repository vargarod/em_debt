"""
Backfill Historical Sub-Index Prices from Bloomberg
Fetches month-end price levels from 2021-01-01 to present
Uses polars-bloomberg BQL for historical data retrieval
"""
import pandas as pd
import polars as pl
from polars_bloomberg import BQuery
import psycopg2
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

print("="*80)
print("BACKFILL HISTORICAL SUB-INDEX PRICES")
print("="*80)
print()

# Load Excel template with sub-index tickers
excel_file = r"c:\code\em_debt\sovereing_score\input\em_sovereign_ratings_numeric_scorev3.xlsx"
print(f"📂 Loading Excel file: {excel_file}")

df_template = pd.read_excel(excel_file, sheet_name='sub_index')
df_template.columns = df_template.columns.str.strip()

# Extract mapping
ticker_map = {}
for _, row in df_template.iterrows():
    country_code = row['country_code']
    ticker = row['Index'].strip()
    country_name = row['NAME']
    ticker_map[country_code] = {'ticker': ticker, 'name': country_name}

print(f"✓ Loaded {len(ticker_map)} country mappings")
print()

# Generate list of month-end dates from 2021-01-31 to present
start_date = datetime(2021, 1, 31)
end_date = datetime.now()

month_ends = []
current = start_date
while current <= end_date:
    # Get last day of current month
    next_month = current + relativedelta(months=1)
    last_day = next_month.replace(day=1) - relativedelta(days=1)
    month_ends.append(last_day.strftime('%Y-%m-%d'))
    current = next_month

print(f"Backfilling {len(month_ends)} month-ends from {month_ends[0]} to {month_ends[-1]}")
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
cursor = conn.cursor()
print("✓ Connected successfully")
print()

# Process each month-end
total_inserted = 0
errors = []

# Use BQuery with context manager
print("Processing all month-ends...")
with BQuery() as bq:
    for month_end in month_ends:
        print(f"Processing {month_end}...")
        
        try:
            # Build list of all tickers
            all_tickers = [info['ticker'] for info in ticker_map.values()]
            tickers_str = "', '".join(all_tickers)
            
            # Create BQL query for PX_LAST on this date
            # Using px_last(fill=prev, dates=YYYY-MM-DD) to get last available price
            bql_query = f"get(px_last(fill=prev, dates={month_end})) for(['{tickers_str}'])"
            
            # Execute query
            result = bq.bql(bql_query)
            
            if not result or result[0].is_empty():
                print(f"  ⚠ No data returned for {month_end}")
                errors.append((month_end, "No data returned"))
                continue
            
            # Convert to pandas dataframe
            df_result = result[0].to_pandas()
            
            # The dataframe has rows for each ticker with columns:
            # ID, px_last(fill=prev,dates=YYYY-MM-DD), DATE, CURRENCY
            # We need to find the price column (starts with "px_last")
            price_col = [col for col in df_result.columns if 'px_last' in col][0]
            
            # Delete existing data for this date
            cursor.execute("DELETE FROM securitized_research.emd_sub_index_prices WHERE date = %s", (month_end,))
            
            # Insert data
            insert_sql = """
            INSERT INTO securitized_research.emd_sub_index_prices 
                (country_code, date, country, sub_index_ticker, sub_index_price)
            VALUES (%s, %s, %s, %s, %s)
            """
            
            inserted_count = 0
            
            # Iterate through rows (each row is one ticker)
            for _, row in df_result.iterrows():
                ticker = row['ID']
                price = row[price_col]
                
                # Find country code for this ticker
                country_code = None
                for code, info in ticker_map.items():
                    if info['ticker'] == ticker:
                        country_code = code
                        break
                
                if country_code and pd.notna(price) and price > 0:
                    cursor.execute(insert_sql, (
                        country_code,
                        month_end,
                        ticker_map[country_code]['name'],
                        ticker,
                        float(price)
                    ))
                    inserted_count += 1
            
            conn.commit()
            total_inserted += inserted_count
            print(f"  ✓ Inserted {inserted_count} records")
            
        except Exception as e:
            print(f"  ⚠ Error: {str(e)[:100]}")
            errors.append((month_end, str(e)[:100]))
            conn.rollback()

print()
print("="*80)
print("BACKFILL SUMMARY")
print("="*80)
print(f"Total month-ends processed: {len(month_ends)}")
print(f"Total records inserted: {total_inserted}")
print(f"Errors: {len(errors)}")

if errors:
    print()
    print("Errors encountered:")
    for date, error in errors[:10]:  # Show first 10 errors
        print(f"  {date}: {error}")

# Verify final state
cursor.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM securitized_research.emd_sub_index_prices")
count, min_date, max_date = cursor.fetchone()

print()
print(f"Database now contains:")
print(f"  Total records: {count}")
print(f"  Date range: {min_date} to {max_date}")

# Show sample by country
print()
print("Sample records per country:")
cursor.execute("""
    SELECT country_code, COUNT(*) as num_dates
    FROM securitized_research.emd_sub_index_prices
    GROUP BY country_code
    ORDER BY country_code
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} month-ends")

cursor.close()
conn.close()

print()
print("="*80)
print("✓ BACKFILL COMPLETE")
print("="*80)
