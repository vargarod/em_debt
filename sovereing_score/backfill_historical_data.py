"""
Backfill Historical Sovereign Ratings Data
Fetches data for multiple historical dates and uploads to PostgreSQL
"""
from datetime import datetime, timedelta
import sys
import os
import time


def get_month_ends(start_date_str, end_date_str):
    """Generate list of month-end dates between start and end dates
    
    Args:
        start_date_str: Start date in YYYY-MM-DD format
        end_date_str: End date in YYYY-MM-DD format
    
    Returns:
        List of month-end dates in YYYYMMDD format
    """
    from dateutil.relativedelta import relativedelta
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    month_ends = []
    current_date = start_date
    
    while current_date <= end_date:
        # Get last day of month
        next_month = current_date + relativedelta(months=1)
        month_end = next_month.replace(day=1) - timedelta(days=1)
        
        if month_end <= end_date:
            month_ends.append(month_end.strftime('%Y%m%d'))
        
        current_date = next_month
    
    return month_ends


def fetch_and_upload_for_date(reference_date):
    """Fetch Bloomberg data and upload to PostgreSQL for a specific date
    
    Args:
        reference_date: Date in YYYYMMDD format
    """
    print("\n" + "=" * 80)
    print(f"PROCESSING DATE: {reference_date}")
    print("=" * 80)
    
    # Import the main functions
    from fetch_sovereign_ratings import main as fetch_main
    from upload_to_postgres import upload_to_postgres
    
    try:
        # Step 1: Fetch data
        print("\n[1] Fetching Bloomberg data...")
        fetch_main(reference_date)
        print(f"✓ Fetch completed for {reference_date}")
        
        # Small delay to ensure file is written
        time.sleep(1)
        
        # Step 2: Upload to database
        print("\n[2] Uploading to PostgreSQL...")
        excel_file = r"c:\code\em_debt\sovereing_score\input\sovereign_ratings_output.xlsx"
        success = upload_to_postgres(excel_file)
        
        if not success:
            print(f"ERROR: Failed to upload data for {reference_date}")
            return False
        
        print(f"✓ Upload completed for {reference_date}")
        
        # Small delay to ensure transaction commits
        time.sleep(1)
        
        return True
        
    except Exception as e:
        print(f"ERROR: Exception occurred for {reference_date}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution"""
    print("=" * 80)
    print("BACKFILL HISTORICAL SOVEREIGN RATINGS DATA")
    print("=" * 80)
    
    # Backfill previous 5 years
    end_date = '2026-07-15'  # Today
    start_date = '2021-01-01'  # Last 5 years
    
    print(f"\nGenerating month-end dates from {start_date} to {end_date}...")
    
    try:
        month_ends = get_month_ends(start_date, end_date)
        print(f"Found {len(month_ends)} month-end dates: {month_ends}")
        
        # Change to script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        successful = 0
        failed = 0
        
        for date in month_ends:
            if fetch_and_upload_for_date(date):
                successful += 1
            else:
                failed += 1
        
        # Summary
        print("\n" + "=" * 80)
        print("BACKFILL SUMMARY")
        print("=" * 80)
        print(f"\nTotal dates processed: {len(month_ends)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        
        if failed == 0:
            print("\nBackfill completed successfully!")
        else:
            print(f"\nWARNING: Backfill completed with {failed} failures")
            
    except Exception as e:
        print(f"\nERROR occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check if dateutil is available
    try:
        import dateutil
    except ImportError:
        print("ERROR: python-dateutil is required for backfilling")
        print("Install with: pip install python-dateutil")
        sys.exit(1)
    
    main()
