"""
Sovereign Ratings Bloomberg Data Fetcher
Fetches sovereign rating data from Bloomberg and creates a clean dataframe
"""
import pandas as pd
import numpy as np
import blpapi
from datetime import datetime
import os


def fetch_bloomberg_data(securities, fields):
    """
    Fetch reference data from Bloomberg
    
    Args:
        securities: List of securities
        fields: List of fields to fetch
        
    Returns:
        dict: {security: {field: value}}
    """
    session_options = blpapi.SessionOptions()
    session_options.setServerHost("localhost")
    session_options.setServerPort(8194)
    
    session = blpapi.Session(session_options)
    
    if not session.start():
        print("❌ Failed to start session. Is Bloomberg Terminal running?")
        return None
    
    if not session.openService("//blp/refdata"):
        print("❌ Failed to open //blp/refdata service")
        session.stop()
        return None
    
    refdata_service = session.getService("//blp/refdata")
    request = refdata_service.createRequest("ReferenceDataRequest")
    
    # Add securities and fields
    for security in securities:
        request.append("securities", security)
    
    for field in fields:
        request.append("fields", field)
    
    session.sendRequest(request)
    
    results = {}
    
    try:
        while True:
            event = session.nextEvent(500)
            
            if event.eventType() == blpapi.Event.RESPONSE or \
               event.eventType() == blpapi.Event.PARTIAL_RESPONSE:
                
                for msg in event:
                    security_data = msg.getElement("securityData")
                    
                    for i in range(security_data.numValues()):
                        field_data = security_data.getValueAsElement(i)
                        security = field_data.getElementAsString("security")
                        
                        if field_data.hasElement("securityError"):
                            print(f"⚠ {security}: Error fetching data")
                            results[security] = {field: None for field in fields}
                            continue
                        
                        field_data_element = field_data.getElement("fieldData")
                        results[security] = {}
                        
                        for field in fields:
                            if field_data_element.hasElement(field):
                                value = field_data_element.getElement(field).getValue()
                                results[security][field] = value
                            else:
                                results[security][field] = None
            
            if event.eventType() == blpapi.Event.RESPONSE:
                break
                
    finally:
        session.stop()
    
    return results


def load_excel_data(excel_file):
    """Load data from Excel file"""
    print(f"📂 Loading Excel file: {excel_file}")
    
    # Load ratings_map
    df_ratings_map = pd.read_excel(excel_file, sheet_name='ratings_map', header=None)
    
    # Load z_spread_and_yield
    df_z_spread = pd.read_excel(excel_file, sheet_name='z_spread_and_yield')
    
    # Load rating_num_scale
    df_rating_scale = pd.read_excel(excel_file, sheet_name='rating_num_scale')
    
    return df_ratings_map, df_z_spread, df_rating_scale


def extract_rating_fields(df_ratings_map):
    """Extract rating field codes from ratings_map"""
    # Row 1 (index 1) contains the field codes
    field_row = df_ratings_map.iloc[1]
    
    # Extract field codes (skip NaN values)
    fields = {}
    fields['country_name'] = field_row[1]  # DS497
    # country_code is not a Bloomberg field - it's in the Excel data
    
    # Moody's fields (columns 3-5)
    fields['moodys_rating'] = field_row[3]  # RG317
    fields['moodys_outlook'] = field_row[4]  # RA128
    fields['moodys_rat_date'] = field_row[5]  # RA404
    
    # S&P fields (columns 6-8)
    fields['sp_rating'] = field_row[6]  # RA123
    fields['sp_outlook'] = field_row[7]  # RA126
    fields['sp_rat_date'] = field_row[8]  # RA401
    
    # Fitch fields (columns 9-11)
    fields['fit_rating'] = field_row[9]  # RA935
    fields['fit_outlook'] = field_row[10]  # RA272
    fields['fit_rat_date'] = field_row[11]  # RA426
    
    return fields


def extract_securities(df_ratings_map):
    """Extract Bloomberg securities and country codes from ratings_map"""
    # Securities start from row 2 (index 2)
    # Column 0: Bloomberg security
    # Column 2: Country code
    securities_data = []
    
    for idx in range(2, len(df_ratings_map)):
        security = df_ratings_map.iloc[idx, 0]
        country_code = df_ratings_map.iloc[idx, 2]
        
        if pd.notna(security):
            securities_data.append({
                'security': security,
                'country_code': country_code
            })
    
    return securities_data


def fetch_ratings_data(securities_data, rating_fields):
    """Fetch all ratings data from Bloomberg"""
    securities = [s['security'] for s in securities_data]
    print(f"\n📡 Fetching ratings data for {len(securities)} securities...")
    
    # Prepare list of Bloomberg fields to fetch
    bb_fields = [
        rating_fields['country_name'],
        rating_fields['moodys_rating'],
        rating_fields['moodys_outlook'],
        rating_fields['moodys_rat_date'],
        rating_fields['sp_rating'],
        rating_fields['sp_outlook'],
        rating_fields['sp_rat_date'],
        rating_fields['fit_rating'],
        rating_fields['fit_outlook'],
        rating_fields['fit_rat_date']
    ]
    
    # Fetch data from Bloomberg
    results = fetch_bloomberg_data(securities, bb_fields)
    
    if results:
        print(f"✓ Successfully fetched data for {len(results)} securities")
        
        # Add country_code from Excel data to results
        for sec_data in securities_data:
            security = sec_data['security']
            if security in results:
                results[security]['country_code_excel'] = sec_data['country_code']
    
    return results


def fetch_spread_yield_data(df_z_spread):
    """Fetch z_spread and current_yield data from Bloomberg"""
    print(f"\n📡 Fetching z_spread and current_yield data...")
    
    # Extract unique Bloomberg indices for z_spread and current_yield
    z_spread_indices = df_z_spread['z_spread'].dropna().unique().tolist()
    current_yield_indices = df_z_spread['current_yield'].dropna().unique().tolist()
    
    all_indices = z_spread_indices + current_yield_indices
    
    # Fetch PX_LAST for all indices
    results = fetch_bloomberg_data(all_indices, ['PX_LAST'])
    
    if results:
        print(f"✓ Successfully fetched data for {len(results)} indices")
    
    return results


def map_rating_to_numeric(rating, df_rating_scale, agency):
    """Map text rating to numeric score"""
    if pd.isna(rating) or rating in ['WR', 'NR', 'WD', 'SD', 'D']:
        return None
    
    # Clean rating (remove whitespace)
    rating = str(rating).strip()
    
    # Look up in rating scale
    mask = df_rating_scale[agency] == rating
    if mask.any():
        row = df_rating_scale[mask].iloc[0]
        return row['num_score']
    
    return None


def create_clean_dataframe(ratings_data, spread_yield_data, df_z_spread, df_rating_scale, rating_fields):
    """Create clean dataframe matching ratings_clean format"""
    print(f"\n🔧 Creating clean dataframe...")
    
    rows = []
    
    for security, data in ratings_data.items():
        if data is None:
            continue
        
        country_code = data.get('country_code_excel')
        country_name = data.get(rating_fields['country_name'])
        
        # Get z_spread and current_yield
        z_spread_val = None
        current_yield_val = None
        
        if country_code:
            z_spread_match = df_z_spread[df_z_spread['country_code'] == country_code]
            if not z_spread_match.empty:
                z_spread_index = z_spread_match.iloc[0]['z_spread']
                current_yield_index = z_spread_match.iloc[0]['current_yield']
                
                if z_spread_index and z_spread_index in spread_yield_data:
                    z_spread_val = spread_yield_data[z_spread_index].get('PX_LAST')
                
                if current_yield_index and current_yield_index in spread_yield_data:
                    current_yield_val = spread_yield_data[current_yield_index].get('PX_LAST')
        
        # Skip rows with negative z_spread (data quality issue)
        if z_spread_val is not None and z_spread_val < 0:
            continue
        
        # Get ratings
        moodys_rating = data.get(rating_fields['moodys_rating'])
        sp_rating = data.get(rating_fields['sp_rating'])
        fit_rating = data.get(rating_fields['fit_rating'])
        
        # Convert to numeric
        moodys_numeric = map_rating_to_numeric(moodys_rating, df_rating_scale, 'moodys')
        sp_numeric = map_rating_to_numeric(sp_rating, df_rating_scale, 'sp')
        fit_numeric = map_rating_to_numeric(fit_rating, df_rating_scale, 'fitch')
        
        # Calculate average rating
        numeric_ratings = [r for r in [moodys_numeric, sp_numeric, fit_numeric] if r is not None]
        avg_rating = round(np.mean(numeric_ratings)) if numeric_ratings else None
        
        # Determine class (IG/HY)
        rating_class = None
        if avg_rating is not None:
            rating_class = 'IG' if avg_rating <= 10 else 'HY'
        
        row = {
            'country': country_name,
            'country_code': country_code,
            'moodys_rating': moodys_rating,
            'moodys_outlook': data.get(rating_fields['moodys_outlook']),
            'moodys_rat_date': data.get(rating_fields['moodys_rat_date']),
            'sp_rating': sp_rating,
            'sp_outlook': data.get(rating_fields['sp_outlook']),
            'st_rat_date': data.get(rating_fields['sp_rat_date']),
            'fit_rating': fit_rating,
            'fit_outlook': data.get(rating_fields['fit_outlook']),
            'fit_rat_date': data.get(rating_fields['fit_rat_date']),
            'avg_rating': avg_rating,
            'z_spread': z_spread_val,
            'current_yield': current_yield_val,
            'class': rating_class,
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        rows.append(row)
    
    df_clean = pd.DataFrame(rows)
    print(f"✓ Created dataframe with {len(df_clean)} rows")
    
    return df_clean


def main():
    """Main execution function"""
    print("=" * 80)
    print("SOVEREIGN RATINGS BLOOMBERG DATA FETCHER")
    print("=" * 80)
    
    # File paths
    excel_file = r"c:\code\em_debt\sovereing_score\input\em_sovereign_ratings_numeric_scorev2.xlsx"
    output_file = r"c:\code\em_debt\sovereing_score\input\sovereign_ratings_output.xlsx"
    
    # Check if file exists
    if not os.path.exists(excel_file):
        print(f"❌ File not found: {excel_file}")
        return
    
    # Load Excel data
    df_ratings_map, df_z_spread, df_rating_scale = load_excel_data(excel_file)
    
    # Extract rating fields and securities
    rating_fields = extract_rating_fields(df_ratings_map)
    securities_data = extract_securities(df_ratings_map)
    
    print(f"\n📊 Found {len(securities_data)} securities to process")
    print(f"📊 Rating fields: {list(rating_fields.values())}")
    
    # Fetch ratings data from Bloomberg
    ratings_data = fetch_ratings_data(securities_data, rating_fields)
    
    if not ratings_data:
        print("❌ Failed to fetch ratings data")
        return
    
    # Fetch spread and yield data
    spread_yield_data = fetch_spread_yield_data(df_z_spread)
    
    if not spread_yield_data:
        print("❌ Failed to fetch spread/yield data")
        return
    
    # Create clean dataframe
    df_clean = create_clean_dataframe(ratings_data, spread_yield_data, df_z_spread, 
                                      df_rating_scale, rating_fields)
    
    # Save to Excel
    print(f"\n💾 Saving to {output_file}...")
    df_clean.to_excel(output_file, index=False, sheet_name='ratings_clean')
    print(f"✓ Saved successfully!")
    
    # Display summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal countries: {len(df_clean)}")
    print(f"Investment Grade: {len(df_clean[df_clean['class'] == 'IG'])}")
    print(f"High Yield: {len(df_clean[df_clean['class'] == 'HY'])}")
    print(f"\nFirst 5 rows:")
    print(df_clean.head())
    
    print(f"\n✓ Process complete! Output saved to: {output_file}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
