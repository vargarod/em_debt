"""
Upload Sovereign Ratings Data to PostgreSQL
Replaces data for the current date in securitized_research.emd_sovereign_score
"""
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import os


def get_db_connection():
    """Create PostgreSQL database connection"""
    conn = psycopg2.connect(
        host="gwamdlquantapps-prod-postgresql-server.postgres.database.azure.com",
        port=5432,
        database="postgres",  # Update if different
        user="securitized_team",
        password="K8#TqL5Z!sA9",
        sslmode="require"  # Azure PostgreSQL requires SSL
    )
    return conn


def delete_existing_data(conn, date_str):
    """Delete existing data for the given date"""
    cursor = conn.cursor()
    
    delete_query = """
        DELETE FROM securitized_research.emd_sovereign_score
        WHERE date = %s
    """
    
    cursor.execute(delete_query, (date_str,))
    deleted_count = cursor.rowcount
    
    print(f"Deleted {deleted_count} existing records for date {date_str}")
    
    cursor.close()
    return deleted_count


def insert_data(conn, df):
    """Insert data into PostgreSQL table"""
    cursor = conn.cursor()
    
    # Prepare insert query
    insert_query = """
        INSERT INTO securitized_research.emd_sovereign_score (
            country, country_code, moodys_rating, moodys_outlook, moodys_rat_date,
            sp_rating, sp_outlook, st_rat_date, fit_rating, fit_outlook, fit_rat_date,
            avg_rating, z_spread, current_yield, class, date
        ) VALUES %s
    """
    
    # Convert DataFrame to list of tuples
    # Handle NaN/None values properly
    data_tuples = []
    for _, row in df.iterrows():
        tuple_data = (
            row['country'],
            row['country_code'],
            row['moodys_rating'],
            row['moodys_outlook'] if pd.notna(row['moodys_outlook']) else None,
            row['moodys_rat_date'] if pd.notna(row['moodys_rat_date']) else None,
            row['sp_rating'],
            row['sp_outlook'] if pd.notna(row['sp_outlook']) else None,
            row['st_rat_date'] if pd.notna(row['st_rat_date']) else None,
            row['fit_rating'],
            row['fit_outlook'] if pd.notna(row['fit_outlook']) else None,
            row['fit_rat_date'] if pd.notna(row['fit_rat_date']) else None,
            int(row['avg_rating']) if pd.notna(row['avg_rating']) else None,
            float(row['z_spread']) if pd.notna(row['z_spread']) else None,
            float(row['current_yield']) if pd.notna(row['current_yield']) else None,
            row['class'] if pd.notna(row['class']) else None,
            row['date']
        )
        data_tuples.append(tuple_data)
    
    # Execute batch insert
    execute_values(cursor, insert_query, data_tuples)
    inserted_count = cursor.rowcount
    
    print(f"Inserted {inserted_count} records")
    
    cursor.close()
    return inserted_count


def upload_to_postgres(excel_file):
    """Main function to upload data to PostgreSQL"""
    print("=" * 80)
    print("UPLOAD SOVEREIGN RATINGS TO POSTGRESQL")
    print("=" * 80)
    
    # Check if file exists
    if not os.path.exists(excel_file):
        print(f"ERROR: File not found: {excel_file}")
        return False
    
    # Load data from Excel
    print(f"\nLoading data from: {excel_file}")
    df = pd.read_excel(excel_file)
    print(f"✓ Loaded {len(df)} records")
    
    # Get the date from the data (should all be the same)
    unique_dates = df['date'].unique()
    if len(unique_dates) > 1:
        print(f"WARNING: Multiple dates found in data: {unique_dates}")
    
    current_date = df['date'].iloc[0]
    print(f"Data date: {current_date}")
    
    # Connect to database
    print("\nConnecting to PostgreSQL database...")
    try:
        conn = get_db_connection()
        print("✓ Connected successfully")
    except Exception as e:
        print(f"ERROR: Connection failed: {e}")
        return False
    
    try:
        # Delete existing data for this date
        print(f"\nReplacing data for date: {current_date}")
        delete_existing_data(conn, current_date)
        
        # Insert new data
        print("\nUploading new data...")
        insert_data(conn, df)
        
        # Commit transaction
        conn.commit()
        print("\n✓ Transaction committed successfully")
        
        # Verify upload
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*), MIN(date), MAX(date)
            FROM securitized_research.emd_sovereign_score
            WHERE date = %s
        """, (current_date,))
        count, min_date, max_date = cursor.fetchone()
        cursor.close()
        
        print("\n" + "=" * 80)
        print("UPLOAD SUMMARY")
        print("=" * 80)
        print(f"Records in database for {current_date}: {count}")
        print(f"✓ Upload completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"\nERROR during upload: {e}")
        conn.rollback()
        print("WARNING: Transaction rolled back")
        return False
        
    finally:
        conn.close()
        print("\nDatabase connection closed")


def main():
    """Main execution"""
    excel_file = r"c:\code\em_debt\sovereing_score\input\sovereign_ratings_output.xlsx"
    
    try:
        success = upload_to_postgres(excel_file)
        if success:
            print("\nAll done!")
        else:
            print("\nUpload failed")
            
    except Exception as e:
        print(f"\nERROR occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
