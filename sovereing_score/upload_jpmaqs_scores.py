"""
Upload JPMaQS Fundamental Risk Scores to PostgreSQL
====================================================

Explores the calculated macro risk scores and uploads to:
securitized_research.emd_jpmaqs_fundamental_scoring

Author: Securitized Research Team
Date: 2026-07-23
"""

import os
import sys
import pandas as pd
import psycopg2
from datetime import datetime
from macro_risk_calculator import MacroRiskCalculator


def get_db_connection():
    """Create database connection using environment variable for password"""
    db_password = os.environ.get('DB_PASSWORD')
    
    if not db_password:
        raise ValueError("Database password not configured. Please set DB_PASSWORD environment variable.")
    
    conn = psycopg2.connect(
        host='gwamdlquantapps-prod-postgresql-server.postgres.database.azure.com',
        port=5432,
        database='postgres',
        user='securitized_team',
        password=db_password,
        sslmode='require'
    )
    return conn


def explore_data(calculator, all_scores):
    """
    Explore and analyze the calculated scores
    """
    print("\n" + "="*80)
    print("DATA EXPLORATION")
    print("="*80)
    
    # Get latest scores
    latest = calculator.get_latest_scores()
    
    print(f"\n1. OVERALL STATISTICS")
    print(f"   Total countries with data: {len(latest)}")
    print(f"   Date of latest data: {all_scores['real_date'].max()}")
    print(f"   Total historical observations: {len(all_scores):,}")
    
    # Composite score distribution
    if 'MACRORISK_COMPOSITE_ZN' in latest.columns:
        composite = latest['MACRORISK_COMPOSITE_ZN'].dropna()
        print(f"\n2. COMPOSITE MACRO RISK SCORE DISTRIBUTION (Equal-Weighted 7-Factor)")
        print(f"   Mean: {composite.mean():.3f}")
        print(f"   Median: {composite.median():.3f}")
        print(f"   Std Dev: {composite.std():.3f}")
        print(f"   Min: {composite.min():.3f} ({composite.idxmin()})")
        print(f"   Max: {composite.max():.3f} ({composite.idxmax()})")
    
    # 4-Factor composite distribution
    if 'MACRORISK_4FACTOR_ZN' in latest.columns:
        composite_4f = latest['MACRORISK_4FACTOR_ZN'].dropna()
        print(f"\n   4-FACTOR COMPOSITE (Govt Finance + Ext Balance + Intl Invest + Governance)")
        print(f"   Mean: {composite_4f.mean():.3f}")
        print(f"   Median: {composite_4f.median():.3f}")
        print(f"   Min: {composite_4f.min():.3f} ({composite_4f.idxmin()})")
        print(f"   Max: {composite_4f.max():.3f} ({composite_4f.idxmax()})")
    
    # Risk level categories
    print(f"\n3. RISK LEVEL BREAKDOWN (Composite Score)")
    if 'MACRORISK_COMPOSITE_ZN' in latest.columns:
        composite = latest['MACRORISK_COMPOSITE_ZN'].dropna()
        
        very_low = (composite < -1.5).sum()
        low = ((composite >= -1.5) & (composite < -0.5)).sum()
        average = ((composite >= -0.5) & (composite <= 0.5)).sum()
        elevated = ((composite > 0.5) & (composite <= 1.5)).sum()
        high = ((composite > 1.5) & (composite <= 2.5)).sum()
        very_high = (composite > 2.5).sum()
        
        print(f"   Very Low Risk  (< -1.5):     {very_low:2d} countries")
        print(f"   Low Risk       (-1.5 to -0.5): {low:2d} countries")
        print(f"   Average Risk   (-0.5 to +0.5): {average:2d} countries")
        print(f"   Elevated Risk  (+0.5 to +1.5): {elevated:2d} countries")
        print(f"   High Risk      (+1.5 to +2.5): {high:2d} countries")
        print(f"   Very High Risk (> +2.5):       {very_high:2d} countries")
    
    # Top 5 and Bottom 5
    print(f"\n4. TOP 5 LOWEST RISK (Safest)")
    if 'MACRORISK_COMPOSITE_ZN' in latest.columns:
        lowest = latest.nsmallest(5, 'MACRORISK_COMPOSITE_ZN')[['country_name', 'MACRORISK_COMPOSITE_ZN']]
        for idx, (cid, row) in enumerate(lowest.iterrows(), 1):
            print(f"   {idx}. {row['country_name']:20s} {row['MACRORISK_COMPOSITE_ZN']:+.3f}")
    
    print(f"\n5. TOP 5 HIGHEST RISK (Most Vulnerable)")
    if 'MACRORISK_COMPOSITE_ZN' in latest.columns:
        highest = latest.nsmallest(5, 'MACRORISK_COMPOSITE_ZN', keep='last').tail()
        highest = latest.nlargest(5, 'MACRORISK_COMPOSITE_ZN')[['country_name', 'MACRORISK_COMPOSITE_ZN']]
        for idx, (cid, row) in enumerate(highest.iterrows(), 1):
            print(f"   {idx}. {row['country_name']:20s} {row['MACRORISK_COMPOSITE_ZN']:+.3f}")
    
    # Factor correlation
    print(f"\n6. FACTOR SCORE CORRELATIONS")
    factor_cols = ['GOVT_FINANCERISK', 'EXTERNAL_BALANCERISK', 'INTL_INVESTMENTRISK',
                   'FOREIGN_DEBTRISK', 'GOVERNANCERISK', 'GROWTHRISK', 'INFLATIONRISK']
    available_factors = [col for col in factor_cols if col in latest.columns]
    
    if len(available_factors) > 1:
        corr_matrix = latest[available_factors].corr()
        print("\n   Correlation with Governance Risk:")
        if 'GOVERNANCERISK' in corr_matrix.columns:
            gov_corr = corr_matrix['GOVERNANCERISK'].drop('GOVERNANCERISK').sort_values(ascending=False)
            for factor, corr in gov_corr.items():
                print(f"      {factor:25s} {corr:+.3f}")
    
    # Regional breakdown
    print(f"\n7. REGIONAL RISK SUMMARY")
    regions = {
        'LatAM': ['BRL', 'CLP', 'COP', 'DOP', 'MXN', 'PEN', 'UYU'],
        'EMEA': ['HUF', 'PLN', 'RSD', 'RUB', 'TRY', 'AED', 'EGP', 'NGN', 'OMR', 'QAR', 'ZAR', 'SAR'],
        'Asia': ['CNY', 'IDR', 'INR', 'PHP']
    }
    
    if 'MACRORISK_COMPOSITE_ZN' in latest.columns:
        for region, countries in regions.items():
            region_data = latest.loc[latest.index.intersection(countries), 'MACRORISK_COMPOSITE_ZN']
            if len(region_data) > 0:
                print(f"   {region:6s}: Avg={region_data.mean():+.3f}, "
                      f"Min={region_data.min():+.3f}, Max={region_data.max():+.3f}, "
                      f"Countries={len(region_data)}")
    
    # Data completeness
    print(f"\n8. DATA COMPLETENESS (% of countries with data)")
    for col in available_factors + ['MACRORISK_COMPOSITE_ZN', 'MACRORISK_4FACTOR_ZN']:
        if col in latest.columns:
            pct_complete = (latest[col].notna().sum() / len(latest)) * 100
            print(f"   {col:30s} {pct_complete:5.1f}%")
    
    print("\n" + "="*80)
    
    return latest


def create_table(conn):
    """
    Create the table in PostgreSQL if it doesn't exist
    """
    print("\nCreating table securitized_research.emd_jpmaqs_fundamental_scoring...")
    
    cursor = conn.cursor()
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS securitized_research.emd_jpmaqs_fundamental_scoring (
        country_code VARCHAR(10) NOT NULL,
        country_name VARCHAR(100),
        date DATE NOT NULL,
        
        -- Individual factor scores (z-scores, positive = higher risk)
        govt_finance_score NUMERIC(10, 6),
        external_balance_score NUMERIC(10, 6),
        intl_investment_score NUMERIC(10, 6),
        foreign_debt_score NUMERIC(10, 6),
        governance_score NUMERIC(10, 6),
        growth_risk_score NUMERIC(10, 6),
        inflation_risk_score NUMERIC(10, 6),
        
        -- Composite scores
        composite_macro_risk NUMERIC(10, 6),
        composite_4factor_risk NUMERIC(10, 6),
        
        -- Metadata
        data_source VARCHAR(50) DEFAULT 'JPMaQS',
        calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        PRIMARY KEY (country_code, date)
    );
    
    -- Create indexes for common queries
    CREATE INDEX IF NOT EXISTS idx_jpmaqs_date 
        ON securitized_research.emd_jpmaqs_fundamental_scoring(date);
    
    CREATE INDEX IF NOT EXISTS idx_jpmaqs_country 
        ON securitized_research.emd_jpmaqs_fundamental_scoring(country_code);
    
    CREATE INDEX IF NOT EXISTS idx_jpmaqs_composite 
        ON securitized_research.emd_jpmaqs_fundamental_scoring(composite_macro_risk);
    
    -- Add comments for documentation
    COMMENT ON TABLE securitized_research.emd_jpmaqs_fundamental_scoring IS 
        'Fundamental macro risk scores for EM sovereigns from JPMaQS data. Positive scores indicate higher risk.';
    
    COMMENT ON COLUMN securitized_research.emd_jpmaqs_fundamental_scoring.composite_macro_risk IS 
        'Equal-weighted composite of 7 macro risk factors. Z-score normalized. Positive = higher risk.';
    
    COMMENT ON COLUMN securitized_research.emd_jpmaqs_fundamental_scoring.composite_4factor_risk IS 
        '4-factor structural risk composite (Govt Finance + Ext Balance + Intl Investment + Governance). Z-score normalized. Positive = higher risk.';
    """
    
    cursor.execute(create_table_sql)
    conn.commit()
    cursor.close()
    
    print("   [OK] Table created/verified successfully")


def upload_data(conn, db_df, as_of_date=None):
    """
    Upload data to PostgreSQL, replacing data for the given date
    
    Args:
        conn: Database connection
        db_df: DataFrame formatted for database
        as_of_date: Date to replace (default: today)
    """
    if as_of_date is None:
        as_of_date = datetime.now().date()
    
    cursor = conn.cursor()
    
    print(f"\nUploading data for date: {as_of_date}")
    print(f"Total rows to upload: {len(db_df)}")
    
    # Delete existing data for this date
    print("   Deleting existing data for this date...")
    cursor.execute(
        "DELETE FROM securitized_research.emd_jpmaqs_fundamental_scoring WHERE date = %s",
        (as_of_date,)
    )
    deleted_rows = cursor.rowcount
    print(f"   Deleted {deleted_rows} existing rows")
    
    # Insert new data
    print("   Inserting new data...")
    
    insert_sql = """
    INSERT INTO securitized_research.emd_jpmaqs_fundamental_scoring 
    (country_code, country_name, date, 
     govt_finance_score, external_balance_score, intl_investment_score, 
     foreign_debt_score, governance_score, growth_risk_score, 
     inflation_risk_score, composite_macro_risk, composite_4factor_risk)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    inserted_count = 0
    for _, row in db_df.iterrows():
        try:
            cursor.execute(insert_sql, (
                row['country_code'],
                row['country_name'],
                row['date'],
                row.get('govt_finance_score'),
                row.get('external_balance_score'),
                row.get('intl_investment_score'),
                row.get('foreign_debt_score'),
                row.get('governance_score'),
                row.get('growth_risk_score'),
                row.get('inflation_risk_score'),
                row.get('composite_macro_risk'),
                row.get('composite_4factor_risk'),
            ))
            inserted_count += 1
        except Exception as e:
            print(f"   Error inserting row for {row['country_code']}: {e}")
    
    conn.commit()
    cursor.close()
    
    print(f"   [OK] Successfully inserted {inserted_count} rows")
    
    # Verify upload
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM securitized_research.emd_jpmaqs_fundamental_scoring WHERE date = %s",
        (as_of_date,)
    )
    final_count = cursor.fetchone()[0]
    cursor.close()
    
    print(f"   [OK] Verified: {final_count} rows in database for {as_of_date}")
    
    return inserted_count


def main():
    """
    Main execution flow
    """
    print("="*80)
    print("JPMaQS FUNDAMENTAL RISK SCORES - DATA UPLOAD PIPELINE")
    print("="*80)
    
    # Step 1: Calculate scores
    print("\nSTEP 1: Calculating macro risk scores...")
    calc = MacroRiskCalculator(
        credentials_path=r"client_credentials.json"
    )
    
    # Need at least 3-4 years for z-score calculation (min 783 daily obs)
    # Using 2020 provides enough history while being reasonably fast
    all_scores = calc.process_all_scores(start_date="2020-01-01")
    
    if len(all_scores) == 0:
        print("\n[ERROR] No scores calculated. Exiting.")
        return
    
    # Step 2: Explore data
    print("\nSTEP 2: Exploring calculated scores...")
    latest = explore_data(calc, all_scores)
    
    # Step 3: Format for database
    print("\nSTEP 3: Formatting data for database...")
    db_df = calc.format_for_database()
    print(f"   Formatted {len(db_df)} country records")
    
    # Show sample
    print("\n   Sample data (first 3 rows):")
    print(db_df.head(3).to_string(index=False))
    
    # Step 4: Connect to database
    print("\nSTEP 4: Connecting to database...")
    try:
        conn = get_db_connection()
        print("   [OK] Connected to PostgreSQL")
    except Exception as e:
        print(f"   [ERROR] Could not connect to database: {e}")
        print("\n   Make sure DB_PASSWORD environment variable is set:")
        print("   $env:DB_PASSWORD = 'your_password'")
        return
    
    # Step 5: Create table
    try:
        create_table(conn)
    except Exception as e:
        print(f"   [ERROR] Could not create table: {e}")
        conn.close()
        return
    
    # Step 6: Upload data
    print("\nSTEP 5: Uploading data to PostgreSQL...")
    try:
        upload_data(conn, db_df)
        print("\n" + "="*80)
        print("[SUCCESS] Data upload completed successfully!")
        print("="*80)
        print("\nYou can now query the data with:")
        print("  SELECT * FROM securitized_research.emd_jpmaqs_fundamental_scoring")
        print("  WHERE date = (SELECT MAX(date) FROM securitized_research.emd_jpmaqs_fundamental_scoring)")
        print("  ORDER BY composite_macro_risk DESC;")
    except Exception as e:
        print(f"\n[ERROR] Upload failed: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    main()
