"""
Validate output from fetch_sovereign_ratings.py
"""
import pandas as pd

# Load the output file
output_file = r"c:\code\em_debt\sovereing_score\input\sovereign_ratings_output.xlsx"
df = pd.read_excel(output_file)

print("=" * 80)
print("OUTPUT VALIDATION")
print("=" * 80)

print(f"\nShape: {df.shape}")
print(f"\nColumns: {list(df.columns)}")

print("\n" + "=" * 80)
print("DATA COMPLETENESS")
print("=" * 80)
for col in df.columns:
    non_null = df[col].notna().sum()
    null_count = df[col].isna().sum()
    print(f"{col:20s}: {non_null:3d} non-null, {null_count:3d} null")

print("\n" + "=" * 80)
print("CLASS DISTRIBUTION")
print("=" * 80)
print(df['class'].value_counts(dropna=False))

print("\n" + "=" * 80)
print("SAMPLE DATA (first 10 rows)")
print("=" * 80)
print(df[['country', 'country_code', 'moodys_rating', 'sp_rating', 'fit_rating', 
         'avg_rating', 'z_spread', 'current_yield', 'class']].head(10))

print("\n" + "=" * 80)
print("COUNTRIES WITH COMPLETE DATA")
print("=" * 80)
complete_data = df[df['z_spread'].notna() & df['current_yield'].notna()]
print(f"Count: {len(complete_data)}")
if not complete_data.empty:
    print(complete_data[['country', 'country_code', 'z_spread', 'current_yield', 'class']].head())
