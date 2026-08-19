"""
Fetch EM Sovereign Sub-Index Prices from Bloomberg
Fetches daily price levels for JP Morgan EMBIG sub-indices
Used for return-based carry-to-volatility calculations
"""
import blpapi
import pandas as pd
import numpy as np
from datetime import datetime
import os

print("="*80)
print("EM SOVEREIGN SUB-INDEX PRICES - BLOOMBERG DATA FETCHER")
print("="*80)
print("Fetching current data (as of today)")

# Load Excel template with sub-index tickers
excel_file = r"c:\code\em_debt\sovereing_score\input\em_sovereign_ratings_numeric_scorev3.xlsx"
print(f"📂 Loading Excel file: {excel_file}")

df_template = pd.read_excel(excel_file, sheet_name='sub_index')
print(f"Found {len(df_template)} sub-indices to process")

# Clean column names (remove trailing spaces)
df_template.columns = df_template.columns.str.strip()

# Extract mapping: country_code -> (ticker, country_name)
ticker_map = {}
for _, row in df_template.iterrows():
    country_code = row['country_code']
    ticker = row['Index'].strip()  # Bloomberg ticker like "JPGCARPI Index"
    country_name = row['NAME']
    ticker_map[country_code] = {'ticker': ticker, 'name': country_name}

print(f"Loaded {len(ticker_map)} country mappings")
print()

# Initialize Bloomberg session
print("Connecting to Bloomberg...")
sessionOptions = blpapi.SessionOptions()
sessionOptions.setServerHost("localhost")
sessionOptions.setServerPort(8194)
session = blpapi.Session(sessionOptions)

if not session.start():
    print("ERROR: Failed to start Bloomberg session")
    exit(1)

if not session.openService("//blp/refdata"):
    print("ERROR: Failed to open //blp/refdata service")
    session.stop()
    exit(1)

refDataService = session.getService("//blp/refdata")
print("✓ Connected to Bloomberg")
print()

# Prepare request for sub-index prices
print(f"Fetching sub-index prices for {len(ticker_map)} countries...")
request = refDataService.createRequest("ReferenceDataRequest")

# Add all tickers
tickers = [info['ticker'] for info in ticker_map.values()]
for ticker in tickers:
    request.append("securities", ticker)

# Request PX_LAST field
request.append("fields", "PX_LAST")

# Send request
session.sendRequest(request)

# Process responses
results = {}
error_count = 0

while True:
    event = session.nextEvent(500)
    
    if event.eventType() == blpapi.Event.RESPONSE or event.eventType() == blpapi.Event.PARTIAL_RESPONSE:
        for msg in event:
            securityDataArray = msg.getElement("securityData")
            
            for i in range(securityDataArray.numValues()):
                securityData = securityDataArray.getValue(i)
                ticker = securityData.getElement("security").getValue()
                
                # Find country code for this ticker
                country_code = None
                for code, info in ticker_map.items():
                    if info['ticker'] == ticker:
                        country_code = code
                        break
                
                if country_code is None:
                    continue
                
                fieldData = securityData.getElement("fieldData")
                
                # Check for errors
                if securityData.hasElement("securityError"):
                    error_count += 1
                    print(f"⚠ Error fetching {ticker} ({country_code})")
                    continue
                
                # Extract price
                try:
                    price = fieldData.getElementAsFloat("PX_LAST")
                    results[country_code] = {
                        'ticker': ticker,
                        'price': price,
                        'country': ticker_map[country_code]['name']
                    }
                except:
                    error_count += 1
                    print(f"⚠ No price data for {ticker} ({country_code})")
    
    if event.eventType() == blpapi.Event.RESPONSE:
        break

session.stop()
print(f"✓ Successfully fetched data for {len(results)} sub-indices")
if error_count > 0:
    print(f"⚠ {error_count} errors encountered")
print()

# Create output dataframe
output_data = []
current_date = datetime.now().strftime('%Y-%m-%d')

for country_code, data in results.items():
    output_data.append({
        'country_code': country_code,
        'country': data['country'],
        'sub_index_ticker': data['ticker'],
        'sub_index_price': data['price'],
        'date': current_date
    })

df_output = pd.DataFrame(output_data)
df_output = df_output.sort_values('country_code')

# Save to Excel
output_file = r'c:\code\em_debt\sovereing_score\input\sub_index_prices_output.xlsx'
print(f"Saving to {output_file}...")
df_output.to_excel(output_file, index=False)
print("✓ Saved successfully!")
print()

# Display summary
print("="*80)
print("SUMMARY")
print("="*80)
print(f"Total countries: {len(df_output)}")
print(f"Date: {current_date}")
print()
print("First 5 rows:")
print(df_output.head())
print()
print(f"✓ Process complete! Output saved to: {output_file}")
