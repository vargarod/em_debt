"""
Compute 5-year carry-to-volatility metric for sovereign credits
"""
import pandas as pd
import numpy as np
import psycopg2
import os
from datetime import datetime, timedelta

# Get DB password
db_password = os.environ.get('DB_PASSWORD')
if not db_password:
    print("ERROR: DB_PASSWORD not set")
    exit(1)

print("="*80)
print("COMPUTING 5-YEAR CARRY-TO-VOLATILITY METRICS")
print("="*80)
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

# Get all historical data (last 5 years minimum)
cutoff_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')

query = """
SELECT 
    date,
    country,
    country_code,
    z_spread,
    current_yield
FROM securitized_research.emd_sovereign_score
WHERE date >= %s
ORDER BY country, date
"""

print(f"Fetching data from {cutoff_date} onwards...")
df = pd.read_sql(query, conn, params=(cutoff_date,))
conn.close()

df['date'] = pd.to_datetime(df['date'])
print(f"✓ Loaded {len(df)} records for {df['country'].nunique()} countries")
print()

# Compute carry-to-vol for each country
results = []

for country in sorted(df['country'].unique()):
    country_data = df[df['country'] == country].sort_values('date').copy()
    
    # Need at least 12 months of data (ideally 60 for 5 years)
    if len(country_data) < 12:
        print(f"⚠ {country}: Only {len(country_data)} data points - skipping")
        continue
    
    # Get latest carry (current yield)
    latest = country_data.iloc[-1]
    carry = latest['current_yield']  # Already in percentage
    country_code = latest['country_code']
    
    # Compute monthly returns from z-spread changes
    # Option 1: Use spread changes as proxy for returns
    country_data['spread_return'] = country_data['z_spread'].pct_change()
    
    # Drop NaN from first row
    returns = country_data['spread_return'].dropna()
    
    if len(returns) < 12:
        print(f"⚠ {country}: Insufficient return data - skipping")
        continue
    
    # Compute volatility
    vol_monthly = np.std(returns, ddof=1)  # Standard deviation of monthly returns
    vol_annual = vol_monthly * np.sqrt(12)  # Annualize
    
    # Compute carry-to-vol
    carry_decimal = carry / 100.0  # Convert percentage to decimal
    carry_to_vol = carry_decimal / vol_annual if vol_annual > 0 else 0
    
    results.append({
        'country': country,
        'country_code': country_code,
        'carry': carry,  # Current yield in %
        'vol_annual': vol_annual,  # Annualized volatility (decimal)
        'carry_to_vol': carry_to_vol,
        'data_points': len(country_data),
        'date_range': f"{country_data['date'].min().strftime('%Y-%m')} to {country_data['date'].max().strftime('%Y-%m')}"
    })
    
    print(f"✓ {country:20s} ({country_code}): Carry={carry:6.3f}%, Vol={vol_annual*100:6.2f}%, C/V={carry_to_vol:.3f}, N={len(country_data)}")

print()
print("="*80)
print(f"SUMMARY: Computed metrics for {len(results)} countries")
print("="*80)
print()

# Create dataframe
results_df = pd.DataFrame(results)

# Sort by carry-to-vol descending
results_df = results_df.sort_values('carry_to_vol', ascending=False)

# Display summary statistics
print("CARRY-TO-VOL DISTRIBUTION:")
print(results_df['carry_to_vol'].describe())
print()

print("TOP 10 BY CARRY-TO-VOL:")
print(results_df[['country', 'country_code', 'carry', 'vol_annual', 'carry_to_vol', 'data_points']].head(10).to_string(index=False))
print()

print("BOTTOM 10 BY CARRY-TO-VOL:")
print(results_df[['country', 'country_code', 'carry', 'vol_annual', 'carry_to_vol', 'data_points']].tail(10).to_string(index=False))
print()

# Save to CSV for exploration
output_file = 'carry_to_vol_metrics.csv'
results_df.to_csv(output_file, index=False)
print(f"✓ Saved results to {output_file}")
print()

print("="*80)
print("DATAFRAME PREVIEW:")
print("="*80)
print(results_df.to_string(index=False))
print()

print("="*80)
print("Ready to create database table? Review the CSV file first.")
print("Next step: Create table and upload using upload_carry_to_vol.py")
print("="*80)
