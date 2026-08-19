"""
Compute carry-to-volatility using TWO methods:
1. Spread-Based C/V: Carry (bps) / Volatility of Spread Changes (bps)
   - Best for credit relative value
2. Return-Based C/V: Carry (%) / Volatility of Price Index Returns (%)
   - Best for portfolio construction / total return perspective
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
print("COMPUTING CARRY-TO-VOL: SPREAD-BASED vs RETURN-BASED")
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

# Query 1: Spread data (for spread-based C/V)
spread_query = """
    SELECT country, country_code, date, z_spread, current_yield
    FROM securitized_research.emd_sovereign_score
    WHERE date >= %s
    ORDER BY country_code, date
"""

df_spreads = pd.read_sql(spread_query, conn, params=(cutoff_date,))
print(f"✓ Loaded {len(df_spreads)} spread records for {df_spreads['country_code'].nunique()} countries")

# Query 2: Sub-index prices (for return-based C/V)
prices_query = """
    SELECT country, country_code, date, sub_index_price
    FROM securitized_research.emd_sub_index_prices
    WHERE date >= %s
    ORDER BY country_code, date
"""

df_prices = pd.read_sql(prices_query, conn, params=(cutoff_date,))
print(f"✓ Loaded {len(df_prices)} price records for {df_prices['country_code'].nunique()} countries")

conn.close()
print()

# Process each country
results = []

# Get all unique countries from spread data
for country_code in sorted(df_spreads['country_code'].unique()):
    spread_data = df_spreads[df_spreads['country_code'] == country_code].copy()
    spread_data = spread_data.sort_values('date')
    
    # Get latest carry (current yield)
    latest = spread_data.iloc[-1]
    carry = latest['current_yield']
    country = latest['country']
    
    # Skip if insufficient data
    if len(spread_data) < 12:
        print(f"⚠ {country:20s} ({country_code}): Insufficient data - skipping")
        continue
    
    # ==========================================================================
    # METHOD 1: SPREAD-BASED C/V (Credit Relative Value Perspective)
    # ==========================================================================
    # Calculate volatility of spread changes in basis points
    spreads = spread_data['z_spread'].dropna()
    spread_changes = spreads.diff().dropna()
    
    if len(spread_changes) < 5:
        print(f"⚠ {country:20s} ({country_code}): Insufficient spread data - skipping")
        continue
    
    vol_spread_bps_monthly = np.std(spread_changes, ddof=1)
    vol_spread_bps_annual = vol_spread_bps_monthly * np.sqrt(12)
    carry_bps = carry * 100  # Convert % to bps
    carry_to_vol_spread = carry_bps / vol_spread_bps_annual if vol_spread_bps_annual > 0 else 0
    
    # ==========================================================================
    # METHOD 2: RETURN-BASED C/V (Total Return / Portfolio Construction Perspective)
    # ==========================================================================
    # Calculate volatility of price index returns
    price_data = df_prices[df_prices['country_code'] == country_code].copy()
    
    if len(price_data) >= 12:
        price_data = price_data.sort_values('date')
        price_data['price_return'] = price_data['sub_index_price'].pct_change()
        price_returns = price_data['price_return'].dropna()
        
        if len(price_returns) >= 5:
            vol_returns_monthly = np.std(price_returns, ddof=1)
            vol_returns_annual = vol_returns_monthly * np.sqrt(12)
            carry_decimal = carry / 100.0
            carry_to_vol_returns = carry_decimal / vol_returns_annual if vol_returns_annual > 0 else 0
            
            has_return_data = True
        else:
            vol_returns_annual = None
            carry_to_vol_returns = None
            has_return_data = False
    else:
        vol_returns_annual = None
        carry_to_vol_returns = None
        has_return_data = False
    
    results.append({
        'country': country,
        'country_code': country_code,
        'carry_pct': carry,
        'carry_bps': carry_bps,
        # Method 1: Spread-based (always available)
        'vol_bps': vol_spread_bps_annual,
        'carry_to_vol': carry_to_vol_spread,  # Default for backward compatibility
        # Method 2: Return-based (may be None if no price data)
        'vol_returns_annual': vol_returns_annual,
        'carry_to_vol_return_based': carry_to_vol_returns,
        'data_points': len(spread_data),
        'date_range': f"{spread_data['date'].min():%Y-%m} to {spread_data['date'].max():%Y-%m}"
    })
    
    if has_return_data:
        print(f"✓ {country:20s} ({country_code:3s}): " +
              f"Spread-based C/V={carry_to_vol_spread:.2f}, " +
              f"Return-based C/V={carry_to_vol_returns:.3f}")
    else:
        print(f"✓ {country:20s} ({country_code:3s}): " +
              f"Spread-based C/V={carry_to_vol_spread:.2f} " +
              f"(no price index data)")

print()
print("="*80)
print(f"SUMMARY: Computed metrics for {len(results)} countries")
print("="*80)
print()

# Create DataFrame
results_df = pd.DataFrame(results)

# Count how many have both metrics
both_metrics = results_df['carry_to_vol_return_based'].notna().sum()
print(f"Countries with BOTH metrics: {both_metrics}/{len(results_df)}")
print()

# Create DataFrame
results_df = pd.DataFrame(results)

# Save to CSV
output_file = 'c:\\code\\em_debt\\sovereing_score\\carry_to_vol_comparison.csv'
results_df.to_csv(output_file, index=False)
print(f"✓ Saved to {output_file}")
print()

# Show statistics for spread-based C/V
print("SPREAD-BASED C/V (Credit Relative Value Perspective)")
print("-" * 60)
print(results_df['carry_to_vol'].describe())
print()
print("Top 10 by Spread-Based C/V:")
top10_spread = results_df.nlargest(10, 'carry_to_vol')
for _, row in top10_spread.iterrows():
    print(f"  {row['country']:20s} ({row['country_code']}): " +
          f"Carry={row['carry_bps']:.0f}bps, Vol={row['vol_bps']:.0f}bps, C/V={row['carry_to_vol']:.2f}")
print()

# Show statistics for return-based C/V (only for countries with data)
df_with_returns = results_df[results_df['carry_to_vol_return_based'].notna()]
if len(df_with_returns) > 0:
    print("RETURN-BASED C/V (Total Return Perspective)")
    print("-" * 60)
    print(df_with_returns['carry_to_vol_return_based'].describe())
    print()
    print("Top 10 by Return-Based C/V:")
    top10_returns = df_with_returns.nlargest(10, 'carry_to_vol_return_based')
    for _, row in top10_returns.iterrows():
        print(f"  {row['country']:20s} ({row['country_code']}): " +
              f"Carry={row['carry_pct']:.2f}%, Vol={row['vol_returns_annual']*100:.1f}%, C/V={row['carry_to_vol_return_based']:.3f}")
    print()
    
    # Show correlation between methods
    correlation = df_with_returns[['carry_to_vol', 'carry_to_vol_return_based']].corr().iloc[0, 1]
    print(f"Correlation between two methods: {correlation:.3f}")
    print()
else:
    print("⚠ No return-based C/V data available (no price index data)")
    print()

print("="*80)
print("INTERPRETATION GUIDE")
print("="*80)
print("""
SPREAD-BASED C/V (bps/bps) - Credit Risk Focus:
- Formula: Carry (bps) / Volatility of Spread Changes (bps)
- Interpretation: How many units of spread volatility am I compensated for?
- Typical Range: 2.0 to 12.0 for EM sovereigns
- Above 5.0 = good carry per unit of credit risk
- Best For: Credit relative value, trading, spread compression/widening bets
- Industry Standard: Fixed income credit products

RETURN-BASED C/V (%/%) - Total Return Focus:
- Formula: Carry (%) / Volatility of Price Index Returns (%)
- Interpretation: Like Sharpe ratio - return per unit of total volatility
- Typical Range: 0.1 to 0.5 for EM sovereigns
- Above 0.3 = decent risk-adjusted total return
- Best For: Portfolio construction, asset allocation, multi-asset investors
- Captures: Both spread risk AND duration/rate risk

WHEN TO USE EACH:
- Spread-Based: Credit traders, EM debt specialists, spread-focused strategies
- Return-Based: Portfolio managers, multi-asset investors, total return perspective
- Both Together: Identify mismatches (high return vol but low spread vol = rate-driven)
""")
print()
print("="*80)
print("✓ COMPUTATION COMPLETE")
print("="*80)
