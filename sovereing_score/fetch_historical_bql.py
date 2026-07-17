"""
Fetch Historical Sovereign Ratings using BQL rating() function
Uses BQL rating(rating_source=..., dates=...) for ratings
Uses BQL credit_rating_outlook(credit_rating_source=..., dates=...) for outlooks
Uses BQL px_last(fill=PREV, dates=...) for market data
"""
import pandas as pd
import numpy as np
from datetime import datetime
import os


def fetch_historical_bql(reference_date_str):
    """
    Fetch historical data using BQL rating() function
    
    Args:
        reference_date_str: Date in YYYYMMDD format
        
    Returns:
        DataFrame with historical data
    """
    from polars_bloomberg import BQuery
    import polars as pl
    
    # Convert YYYYMMDD to YYYY-MM-DD
    date_formatted = f"{reference_date_str[:4]}-{reference_date_str[4:6]}-{reference_date_str[6:8]}"
    
    print(f"\n{'='*80}")
    print(f"FETCHING HISTORICAL DATA FOR: {date_formatted}")
    print(f"{'='*80}")
    
    # Load Excel mapping file
    excel_file = r"c:\code\em_debt\sovereing_score\input\em_sovereign_ratings_numeric_scorev2.xlsx"
    df_ratings_map = pd.read_excel(excel_file, sheet_name='ratings_map', header=None)
    df_z_spread = pd.read_excel(excel_file, sheet_name='z_spread_and_yield')
    df_rating_scale = pd.read_excel(excel_file, sheet_name='rating_num_scale')
    
    # Extract securities and country codes
    securities_data = []
    for idx in range(2, len(df_ratings_map)):
        security = df_ratings_map.iloc[idx, 0]
        country_code = df_ratings_map.iloc[idx, 2]
        country_name = df_ratings_map.iloc[idx, 1]
        
        if pd.notna(security):
            securities_data.append({
                'security': security,
                'country_code': country_code,
                'country_name': country_name
            })
    
    print(f"\n✓ Found {len(securities_data)} securities to process")
    
    # Fetch historical ratings and outlooks using BQL
    print(f"\nFetching historical ratings and outlooks using BQL...")
    
    ratings_data = {}
    
    with BQuery() as bq:
        for sec_data in securities_data:
            security = sec_data['security']
            print(f"  Processing {sec_data['country_name']}...", end='')
            
            try:
                # Fetch Moody's rating and outlook
                moody_query = f"get(rating(rating_source=MOODY, dates={date_formatted})) for(['{security}'])"
                moody_result = bq.bql(moody_query)
                moody_rating = moody_result[0][moody_result[0].columns[1]][0] if moody_result and not moody_result[0].is_empty() else None
                
                moody_outlook_query = f"get(credit_rating_outlook(credit_rating_source=MOODY, dates={date_formatted})) for(['{security}'])"
                moody_outlook_result = bq.bql(moody_outlook_query)
                moody_outlook = moody_outlook_result[0][moody_outlook_result[0].columns[1]][0] if moody_outlook_result and not moody_outlook_result[0].is_empty() else None
                
                # Fetch S&P rating and outlook
                sp_query = f"get(rating(rating_source=SP, dates={date_formatted})) for(['{security}'])"
                sp_result = bq.bql(sp_query)
                sp_rating = sp_result[0][sp_result[0].columns[1]][0] if sp_result and not sp_result[0].is_empty() else None
                
                sp_outlook_query = f"get(credit_rating_outlook(credit_rating_source=SP, dates={date_formatted})) for(['{security}'])"
                sp_outlook_result = bq.bql(sp_outlook_query)
                sp_outlook = sp_outlook_result[0][sp_outlook_result[0].columns[1]][0] if sp_outlook_result and not sp_outlook_result[0].is_empty() else None
                
                # Fetch Fitch rating and outlook
                fitch_query = f"get(rating(rating_source=FITCH, dates={date_formatted})) for(['{security}'])"
                fitch_result = bq.bql(fitch_query)
                fitch_rating = fitch_result[0][fitch_result[0].columns[1]][0] if fitch_result and not fitch_result[0].is_empty() else None
                
                fitch_outlook_query = f"get(credit_rating_outlook(credit_rating_source=FITCH, dates={date_formatted})) for(['{security}'])"
                fitch_outlook_result = bq.bql(fitch_outlook_query)
                fitch_outlook = fitch_outlook_result[0][fitch_outlook_result[0].columns[1]][0] if fitch_outlook_result and not fitch_outlook_result[0].is_empty() else None
                
                ratings_data[security] = {
                    'country': sec_data['country_name'],
                    'country_code': sec_data['country_code'],
                    'moodys_rating': moody_rating,
                    'moodys_outlook': moody_outlook,
                    'sp_rating': sp_rating,
                    'sp_outlook': sp_outlook,
                    'fit_rating': fitch_rating,
                    'fit_outlook': fitch_outlook
                }
                
                print(f" ✓")
                
            except Exception as e:
                print(f" ERROR: {e}")
                ratings_data[security] = {
                    'country': sec_data['country_name'],
                    'country_code': sec_data['country_code'],
                    'moodys_rating': None,
                    'moodys_outlook': None,
                    'sp_rating': None,
                    'sp_outlook': None,
                    'fit_rating': None,
                    'fit_outlook': None
                }
    
    print(f"\n✓ Successfully fetched ratings and outlooks for {len(ratings_data)} securities")
    
    # Fetch historical market data (z_spread and current_yield)
    print(f"\nFetching historical market data using BQL px_last(fill=PREV)...")
    
    market_data = {}
    
    with BQuery() as bq:
        # Get all unique indices
        all_indices = list(df_z_spread['z_spread'].dropna().unique()) + list(df_z_spread['current_yield'].dropna().unique())
        
        for index in all_indices:
            try:
                # Use px_last with fill=PREV to get last available value
                query = f"get(px_last(fill=PREV, dates={date_formatted})) for(['{index}'])"
                result = bq.bql(query)
                
                if result and not result[0].is_empty():
                    value = result[0][result[0].columns[1]][0]
                    market_data[index] = value
                else:
                    market_data[index] = None
                    
            except Exception as e:
                print(f"  WARNING: Failed to fetch {index}: {e}")
                market_data[index] = None
    
    print(f"✓ Successfully fetched market data for {len(market_data)} indices")
    
    # Create clean dataframe
    print(f"\nCreating clean dataframe...")
    
    rows = []
    
    for security, data in ratings_data.items():
        country_code = data['country_code']
        
        # Get z_spread and current_yield from market data
        z_spread_val = None
        current_yield_val = None
        
        if country_code:
            z_spread_match = df_z_spread[df_z_spread['country_code'] == country_code]
            if not z_spread_match.empty:
                z_spread_index = z_spread_match.iloc[0]['z_spread']
                current_yield_index = z_spread_match.iloc[0]['current_yield']
                
                z_spread_val = market_data.get(z_spread_index)
                current_yield_val = market_data.get(current_yield_index)
        
        # Skip rows with negative z_spread
        if z_spread_val is not None and z_spread_val < 0:
            continue
        
        # Map ratings to numeric
        def map_rating(rating, agency):
            if pd.isna(rating) or rating in ['WR', 'NR', 'WD', 'SD', 'D']:
                return None
            rating = str(rating).strip()
            mask = df_rating_scale[agency] == rating
            if mask.any():
                return df_rating_scale[mask].iloc[0]['num_score']
            return None
        
        moodys_numeric = map_rating(data['moodys_rating'], 'moodys')
        sp_numeric = map_rating(data['sp_rating'], 'sp')
        fit_numeric = map_rating(data['fit_rating'], 'fitch')
        
        # Calculate average rating (no rounding)
        numeric_ratings = [r for r in [moodys_numeric, sp_numeric, fit_numeric] if r is not None]
        avg_rating = np.mean(numeric_ratings) if numeric_ratings else None
        
        # Determine class
        rating_class = None
        if avg_rating is not None:
            rating_class = 'IG' if avg_rating <= 10 else 'HY'
        
        row = {
            'country': data['country'],
            'country_code': country_code,
            'moodys_rating': data['moodys_rating'],
            'moodys_outlook': data['moodys_outlook'],
            'moodys_rat_date': None,  # Not available in historical BQL
            'sp_rating': data['sp_rating'],
            'sp_outlook': data['sp_outlook'],
            'st_rat_date': None,  # Not available in historical BQL
            'fit_rating': data['fit_rating'],
            'fit_outlook': data['fit_outlook'],
            'fit_rat_date': None,  # Not available in historical BQL
            'avg_rating': avg_rating,
            'z_spread': z_spread_val,
            'current_yield': current_yield_val,
            'class': rating_class,
            'date': date_formatted
        }
        
        rows.append(row)
    
    df_clean = pd.DataFrame(rows)
    
    print(f"✓ Created dataframe with {len(df_clean)} rows")
    
    if len(df_clean) > 0:
        print(f"\nInvestment Grade: {len(df_clean[df_clean['class'] == 'IG'])}")
        print(f"High Yield: {len(df_clean[df_clean['class'] == 'HY'])}")
        print(f"\nFirst 5 rows:")
        print(df_clean[['country', 'moodys_rating', 'moodys_outlook', 'sp_rating', 'sp_outlook', 'fit_rating', 'fit_outlook', 'avg_rating', 'z_spread']].head())
    
    # Save to Excel
    output_file = r"c:\code\em_debt\sovereing_score\input\sovereign_ratings_output.xlsx"
    df_clean.to_excel(output_file, index=False, sheet_name='ratings_clean')
    print(f"\n✓ Saved to {output_file}")
    
    return df_clean


if __name__ == "__main__":
    import sys
    
    # Test with Jan 2021
    reference_date = sys.argv[1] if len(sys.argv) > 1 else "20210131"
    
    try:
        df = fetch_historical_bql(reference_date)
        print(f"\n{'='*80}")
        print("SUCCESS!")
        print(f"{'='*80}")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
