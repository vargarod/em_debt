"""
Excel Structure Explorer
Examines em_sovereign_ratings_numeric_scorev2.xlsx to understand data structure
"""
import pandas as pd
import os

# File path
excel_file = r"c:\code\em_debt\sovereing_score\input\em_sovereign_ratings_numeric_scorev2.xlsx"

# Check if file exists
if not os.path.exists(excel_file):
    print(f"❌ File not found: {excel_file}")
    print("\nPlease save the Excel file to this location first.")
    exit()

print("=" * 80)
print("EXCEL FILE STRUCTURE ANALYSIS")
print("=" * 80)

# Read all sheet names
excel_file_obj = pd.ExcelFile(excel_file)
print(f"\n📋 Sheet names: {excel_file_obj.sheet_names}\n")

# 1. RATINGS_MAP
print("\n" + "=" * 80)
print("SHEET: ratings_map")
print("=" * 80)
df_ratings_map = pd.read_excel(excel_file, sheet_name='ratings_map', header=None)
print(f"\nShape: {df_ratings_map.shape}")
print(f"\nFirst 5 rows:")
print(df_ratings_map.head())
print(f"\nRow 1 (index 0 - headers/agency names):")
print(df_ratings_map.iloc[0])
print(f"\nRow 2 (index 1 - rating field codes):")
print(df_ratings_map.iloc[1])
print(f"\nColumn A (first 10 Bloomberg securities):")
print(df_ratings_map.iloc[:10, 0])

# 2. Z_SPREAD_AND_YIELD
print("\n" + "=" * 80)
print("SHEET: z_spread_and_yield")
print("=" * 80)
df_z_spread = pd.read_excel(excel_file, sheet_name='z_spread_and_yield')
print(f"\nShape: {df_z_spread.shape}")
print(f"\nColumn names: {list(df_z_spread.columns)}")
print(f"\nFirst 5 rows:")
print(df_z_spread.head())
print(f"\nData types:")
print(df_z_spread.dtypes)

# 3. RATING_NUM_SCALE
print("\n" + "=" * 80)
print("SHEET: rating_num_scale")
print("=" * 80)
df_rating_scale = pd.read_excel(excel_file, sheet_name='rating_num_scale')
print(f"\nShape: {df_rating_scale.shape}")
print(f"\nColumn names: {list(df_rating_scale.columns)}")
print(f"\nFirst 10 rows:")
print(df_rating_scale.head(10))

# 4. RATINGS_CLEAN (target format)
print("\n" + "=" * 80)
print("SHEET: ratings_clean (TARGET FORMAT)")
print("=" * 80)
df_ratings_clean = pd.read_excel(excel_file, sheet_name='ratings_clean')
print(f"\nShape: {df_ratings_clean.shape}")
print(f"\nColumn names: {list(df_ratings_clean.columns)}")
print(f"\nFirst 5 rows:")
print(df_ratings_clean.head())
print(f"\nData types:")
print(df_ratings_clean.dtypes)

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\n✓ Analysis complete!")
print("\nNext steps:")
print("1. Review the column structures above")
print("2. Confirm the mapping logic between sheets")
print("3. Identify all Bloomberg fields to fetch")
