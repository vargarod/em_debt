"""
Fetch sovereign ratings using polars-bloomberg BQuery with historical dates
"""
import pandas as pd
import numpy as np
from datetime import datetime
import os
from polars_bloomberg import BQuery
import polars as pl


def fetch_bloomberg_data_bql(securities, fields, reference_date=None):
    """
    Fetch data from Bloomberg using BQuery with BQL dates parameter
    
    Args:
        securities: List of securities
        fields: List of fields to fetch
        reference_date: Optional date string (YYYYMMDD) for historical data
        
    Returns:
        dict: {security: {field: value}}
    """
    # Convert YYYYMMDD to YYYY-MM-DD for BQL
    if reference_date:
        date_str = f"{reference_date[:4]}-{reference_date[4:6]}-{reference_date[6:8]}"
        print(f"  Using BQL with dates={date_str}")
    
    results = {}
    
    with BQuery() as bq:
        for security in securities:
            security_results = {}
            
            for field in fields:
                try:
                    # Build BQL query with dates parameter if provided
                    if reference_date:
                        bql_query = f"get({field.lower()}(dates={date_str})) for(['{security}'])"
                    else:
                        bql_query = f"get({field.lower()}) for(['{security}'])"
                    
                    # Execute query
                    result = bq.bql(bql_query)
                    
                    if result and len(result) > 0:
                        df = result[0]
                        
                        if not df.is_empty():
                            # Get the field column (it has dates parameter in name if historical)
                            if reference_date:
                                col_name = f"{field.lower()}(dates={date_str})"
                            else:
                                col_name = field.lower()
                            
                            if col_name in df.columns:
                                value = df[col_name][0]
                                security_results[field] = value
                            else:
                                security_results[field] = None
                        else:
                            security_results[field] = None
                    else:
                        security_results[field] = None
                        
                except Exception as e:
                    print(f"  ⚠ Error fetching {field} for {security}: {e}")
                    security_results[field] = None
            
            results[security] = security_results
    
    return results


# Test the new function
if __name__ == "__main__":
    print("="*80)
    print("TESTING NEW BQL-BASED FETCH FUNCTION")
    print("="*80)
    
    # Test 1: Ratings with historical date
    print("\nTest 1: Argentina ratings on 2021-01-31")
    result = fetch_bloomberg_data_bql(
        ['1310Z AR Equity'],
        ['RG317', 'RA123'],
        '20210131'
    )
    print(result)
    
    # Test 2: Spreads with historical date
    print("\nTest 2: Japan spread on 2026-06-30")
    result = fetch_bloomberg_data_bql(
        ['JPBYARZS Index'],
        ['PX_LAST'],
        '20260630'
    )
    print(result)
    
    # Test 3: Current data
    print("\nTest 3: Current Argentina rating")
    result = fetch_bloomberg_data_bql(
        ['1310Z AR Equity'],
        ['RG317'],
        None
    )
    print(result)
