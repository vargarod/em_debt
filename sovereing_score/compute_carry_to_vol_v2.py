"""
Compute carry-to-volatility using TWO methods:
1. Vol of returns (current method)
2. Vol of spread levels in basis points (alternative)
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
print("COMPUTING CARRY-TO-VOL: RETURNS vs SPREAD LEVELS COMPARISON")
print("="*80)
print()

# Fetch 5 years of data
cutoff_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
print(f"Fetching data from {cutoff_date} onwards...")

conn = psycopg2.connect(
    host='gwamdlquantapps-prod-postgresql-server.postgres.database.azure.com',
    port=5432,
    database='postgres',
    user='securitized_team',
    password=db_password,
    sslmode='require'
)

query = """
    SELECT country, country_code, date, z_spread, current_yield
    FROM securitized_research.emd_sovereign_score
    WHERE date >= %s
    ORDER BY country_code, date
"""

df = pd.read_sql(query, conn, params=(cutoff_date,))
conn.close()

print(f"✓ Loaded {len(df)} records for {df['country_code'].nunique()} countries")
print()

# Process each country
results = []

for country_code in sorted(df['country_code'].unique()):
    country_data = df[df['country_code'] == country_code].copy()
    country_data = country_data.sort_values('date')
    
    # Get latest carry (current yield)
    latest = country_data.iloc[-1]
    carry = latest['current_yield']
    country = latest['country']
    
    # Skip if insufficient data
    if len(country_data) < 12:
        print(f"⚠ {country:20s} ({country_code}): Insufficient data - skipping")
        continue
    
    # METHOD 1: Volatility of RETURNS (percentage changes)
    country_data['spread_return'] = country_data['z_spread'].pct_change()
    returns = country_data['spread_return'].dropna()
    
    if len(returns) < 5:
        print(f"⚠ {country:20s} ({country_code}): Insufficient return data - skipping")
        continue
    
    vol_returns_monthly = np.std(returns, ddof=1)
    vol_returns_annual = vol_returns_monthly * np.sqrt(12)
    carry_decimal = carry / 100.0
    carry_to_vol_returns = carry_decimal / vol_returns_annual if vol_returns_annual > 0 else 0
    
    # METHOD 2: Volatility of SPREAD LEVELS (in basis points)
    spreads = country_data['z_spread'].dropna()
    spread_changes = spreads.diff().dropna()
    
    vol_spread_bps_monthly = np.std(spread_changes, ddof=1)
    vol_spread_bps_annual = vol_spread_bps_monthly * np.sqrt(12)
    carry_bps = carry * 100  # Convert % to bps
    carry_to_vol_spread = carry_bps / vol_spread_bps_annual if vol_spread_bps_annual > 0 else 0
    
    results.append({
        'country': country,
        'country_code': country_code,
        'carry_pct': carry,
        'carry_bps': carry_bps,
        # Method 1: Vol of returns
        'vol_returns_annual': vol_returns_annual,
        'carry_to_vol_returns': carry_to_vol_returns,
        # Method 2: Vol of spread levels
        'vol_spread_bps_annual': vol_spread_bps_annual,
        'carry_to_vol_spread': carry_to_vol_spread,
        'data_points': len(country_data),
        'date_range': f"{country_data['date'].min():%Y-%m} to {country_data['date'].max():%Y-%m}"
    })
    
    print(f"✓ {country:20s} ({country_code:3s}): " +
          f"Method1(returns) C/V={carry_to_vol_returns:.3f}, " +
          f"Method2(spread) C/V={carry_to_vol_spread:.3f}")

print()
print("="*80)
print(f"SUMMARY: Computed metrics for {len(results)} countries")
print("="*80)
print()

# Create DataFrame
results_df = pd.DataFrame(results)

# Save to CSV
output_file = 'c:\\code\\em_debt\\sovereing_score\\carry_to_vol_comparison.csv'
results_df.to_csv(output_file, index=False)
print(f"✓ Saved to {output_file}")
print()

# Compare distributions
print("METHOD 1: VOLATILITY OF RETURNS")
print("-" * 40)
print(results_df['carry_to_vol_returns'].describe())
print()
print("Top 10 by C/V (returns method):")
top10_returns = results_df.nlargest(10, 'carry_to_vol_returns')
for _, row in top10_returns.iterrows():
    print(f"  {row['country']:20s} ({row['country_code']}): " +
          f"Carry={row['carry_pct']:.3f}%, Vol={row['vol_returns_annual']*100:.2f}%, C/V={row['carry_to_vol_returns']:.3f}")
print()

print("METHOD 2: VOLATILITY OF SPREAD LEVELS (BPS)")
print("-" * 40)
print(results_df['carry_to_vol_spread'].describe())
print()
print("Top 10 by C/V (spread vol method):")
top10_spread = results_df.nlargest(10, 'carry_to_vol_spread')
for _, row in top10_spread.iterrows():
    print(f"  {row['country']:20s} ({row['country_code']}): " +
          f"Carry={row['carry_bps']:.0f}bps, Vol={row['vol_spread_bps_annual']:.0f}bps, C/V={row['carry_to_vol_spread']:.2f}")
print()

# Show correlation between methods
correlation = results_df[['carry_to_vol_returns', 'carry_to_vol_spread']].corr().iloc[0, 1]
print(f"Correlation between two methods: {correlation:.3f}")
print()

print("="*80)
print("INTERPRETATION GUIDE")
print("="*80)
print("""
METHOD 1 (Vol of Returns):
- Similar to Sharpe ratio (return per unit of volatility)
- Typical range: 0.1 to 0.5 for EM sovereigns
- Above 0.3 = decent risk-adjusted carry
- Dimensionless ratio

METHOD 2 (Vol of Spread Levels in BPS):
- Carry in bps divided by spread volatility in bps
- More intuitive: "How many units of spread vol am I compensated?"
- Typical range: 0.5 to 5.0 for EM sovereigns
- Above 2.0 = good carry per unit of spread movement
- Industry standard for credit products

RECOMMENDATION: Method 2 (spread levels) is more common for fixed income
and easier to interpret for EM sovereign spreads.
""")
