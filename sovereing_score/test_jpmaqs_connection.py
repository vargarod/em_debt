"""
Test script for JPMaQS DataQuery API connectivity
Tests authentication and basic data retrieval for EM sovereign macro indicators
"""

import json
import os
from pathlib import Path
import pandas as pd
from macrosynergy.download import JPMaQSDownload

# Load credentials from JSON file
def load_credentials():
    """Load JPMaQS credentials from downloaded JSON file"""
    credentials_path = Path(r"client_credentials.json")
    
    if not credentials_path.exists():
        raise FileNotFoundError(f"Credentials file not found at: {credentials_path}")
    
    with open(credentials_path, 'r') as f:
        credentials = json.load(f)
    
    client_id = credentials.get('client_id')
    client_secret = credentials.get('client_secret')
    
    if not client_id or not client_secret:
        raise ValueError("client_id or client_secret not found in credentials file")
    
    print(f"✓ Credentials loaded successfully")
    print(f"  Client ID: {client_id[:20]}...")
    
    return client_id, client_secret


# Test basic connectivity
def test_connection(client_id, client_secret):
    """Test basic connection to JPMaQS"""
    print("\n" + "="*60)
    print("Testing JPMaQS Connection...")
    print("="*60)
    
    try:
        with JPMaQSDownload(
            client_id=client_id,
            client_secret=client_secret,
            proxy={}
        ) as downloader:
            print("✓ Successfully authenticated with JPMaQS")
            return True
    except Exception as e:
        print(f"✗ Connection failed: {str(e)}")
        return False


# Test data download for a small sample
def test_sample_download(client_id, client_secret):
    """Download a small sample of macro data for EM countries"""
    print("\n" + "="*60)
    print("Testing Sample Data Download...")
    print("="*60)
    
    # Test with a few key EM countries and one simple indicator
    test_cids = ["BRL", "MXN", "ZAR", "TRY", "IDR"]  # Brazil, Mexico, South Africa, Turkey, Indonesia
    test_xcats = ["GGOBGDPRATIO_NSA"]  # Government balance to GDP ratio
    
    test_tickers = [f"{cid}_{xcat}" for cid in test_cids for xcat in test_xcats]
    
    print(f"\nTesting with {len(test_cids)} countries and {len(test_xcats)} indicator(s)")
    print(f"Countries: {', '.join(test_cids)}")
    print(f"Indicator: {', '.join(test_xcats)}")
    print(f"Total tickers: {len(test_tickers)}")
    
    try:
        with JPMaQSDownload(
            client_id=client_id,
            client_secret=client_secret,
            proxy={}
        ) as downloader:
            df = downloader.download(
                tickers=test_tickers,
                start_date="2023-01-01",
                metrics=["value"],
                suppress_warning=True,
                show_progress=True,
                report_time_taken=True,
            )
        
        print(f"\n✓ Successfully downloaded {len(df)} rows of data")
        print(f"\nData shape: {df.shape}")
        print(f"Date range: {df['real_date'].min()} to {df['real_date'].max()}")
        print(f"\nFirst few rows:")
        print(df.head(10))
        
        print(f"\nData summary by country:")
        summary = df.groupby('cid').agg({
            'real_date': ['min', 'max', 'count'],
            'value': ['mean', 'min', 'max']
        }).round(2)
        print(summary)
        
        return df
        
    except Exception as e:
        print(f"\n✗ Download failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


# Test downloading multiple macro indicators
def test_macro_indicators(client_id, client_secret):
    """Test downloading key macro indicators used for sovereign risk scoring"""
    print("\n" + "="*60)
    print("Testing Macro Indicators for Sovereign Risk Scoring...")
    print("="*60)
    
    # Use the same indicators from the notebook
    test_cids = ["BRL", "MXN", "TRY"]  # Just 3 countries for quick test
    
    # Key macro indicators from the notebook
    indicators = {
        "Government Finance": ["GGOBGDPRATIO_NSA", "GGDGDPRATIO_NSA"],
        "External Balance": ["CABGDPRATIO_NSA_12MMA", "MTBGDPRATIO_NSA_12MMA"],
        "Governance": ["ACCOUNTABILITY_NSA", "POLSTAB_NSA", "CORRCONTROL_NSA"],
        "Growth": ["RGDP_SA_P1Q1QL4"],
        "Inflation": ["CPIH_SA_P1M1ML12", "CPIC_SA_P1M1ML12"],
    }
    
    print(f"\nTesting {len(test_cids)} countries:")
    print(f"  {', '.join(test_cids)}")
    print(f"\nIndicator categories:")
    for category, xcats in indicators.items():
        print(f"  {category}: {len(xcats)} indicator(s)")
    
    # Flatten indicators
    all_xcats = [xcat for xcats in indicators.values() for xcat in xcats]
    test_tickers = [f"{cid}_{xcat}" for cid in test_cids for xcat in all_xcats]
    
    print(f"\nTotal tickers to download: {len(test_tickers)}")
    
    try:
        with JPMaQSDownload(
            client_id=client_id,
            client_secret=client_secret,
            proxy={}
        ) as downloader:
            df = downloader.download(
                tickers=test_tickers,
                start_date="2024-01-01",
                metrics=["value"],
                suppress_warning=True,
                show_progress=True,
                report_time_taken=True,
            )
        
        print(f"\n✓ Successfully downloaded {len(df)} rows of data")
        
        # Check data availability by category
        print(f"\nData availability by category:")
        for category, xcats in indicators.items():
            category_data = df[df['xcat'].isin(xcats)]
            if len(category_data) > 0:
                print(f"  {category}: {len(category_data)} rows, "
                      f"{category_data['cid'].nunique()} countries, "
                      f"latest date: {category_data['real_date'].max()}")
            else:
                print(f"  {category}: No data available")
        
        # Show sample data for each category
        print(f"\nSample data (latest values per country):")
        latest_df = df.sort_values('real_date').groupby(['cid', 'xcat']).tail(1)
        sample = latest_df.pivot_table(
            index='cid',
            columns='xcat',
            values='value',
            aggfunc='first'
        )
        print(sample.to_string())
        
        return df
        
    except Exception as e:
        print(f"\n✗ Download failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main test function"""
    print("\n" + "="*60)
    print("JPMaQS DataQuery API Connection Test")
    print("="*60)
    
    try:
        # Load credentials
        client_id, client_secret = load_credentials()
        
        # Test connection
        if not test_connection(client_id, client_secret):
            print("\n✗ Connection test failed. Please check credentials.")
            return
        
        # Test basic download
        sample_df = test_sample_download(client_id, client_secret)
        if sample_df is None:
            print("\n✗ Sample download failed.")
            return
        
        # Test macro indicators
        macro_df = test_macro_indicators(client_id, client_secret)
        if macro_df is None:
            print("\n✗ Macro indicators download failed.")
            return
        
        print("\n" + "="*60)
        print("✓ All tests passed successfully!")
        print("="*60)
        print("\nNext steps:")
        print("1. Review the downloaded data above")
        print("2. Proceed to build macro risk scoring functions")
        print("3. Create database schema for storing scores")
        print("4. Integrate with app.py for visualization")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
