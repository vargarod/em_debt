import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

##Read excel file
file_path = r"C:\code\em_debt\input\s_scores.xlsx"
sheet_name = "ratings_clean"
df = pd.read_excel(file_path, sheet_name=sheet_name)

# Read rating to numeric score mapping
map_df = pd.read_excel(file_path, sheet_name="rating_num_score")

# Show all columns
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

# Define regional groupings
region_mapping = {
    # Latin America
    'ARG': 'LatAM', 'BRA': 'LatAM', 'CHL': 'LatAM', 'COL': 'LatAM', 'MEX': 'LatAM',
    'PER': 'LatAM', 'URY': 'LatAM', 'ECU': 'LatAM', 'PAN': 'LatAM', 'CRI': 'LatAM',
    'GTM': 'LatAM', 'DOM': 'LatAM', 'PRY': 'LatAM', 'SLV': 'LatAM', 'VEN': 'LatAM',
    'BOL': 'LatAM', 'JAM': 'LatAM', 'TTO': 'LatAM',
    
    # EMEA (Europe, Middle East, Africa)
    'ZAF': 'EMEA', 'TUR': 'EMEA', 'POL': 'EMEA', 'HUN': 'EMEA', 'ROU': 'EMEA',
    'CZE': 'EMEA', 'HRV': 'EMEA', 'BGR': 'EMEA', 'EGY': 'EMEA', 'MAR': 'EMEA',
    'KEN': 'EMEA', 'NGA': 'EMEA', 'SEN': 'EMEA', 'KSA': 'EMEA', 'UAE': 'EMEA',
    'QAT': 'EMEA', 'BHR': 'EMEA', 'OMN': 'EMEA', 'JOR': 'EMEA', 'LBN': 'EMEA',
    'ISR': 'EMEA', 'RUS': 'EMEA', 'UKR': 'EMEA', 'KAZ': 'EMEA', 'SRB': 'EMEA',
    'GHA': 'EMEA', 'CIV': 'EMEA', 'AGO': 'EMEA', 'ETH': 'EMEA', 'TUN': 'EMEA',
    'LEB': 'EMEA', 'GAB': 'EMEA', 'AZE': 'EMEA', 'MOZ': 'EMEA',
    
    # Asia
    'CHI': 'Asia', 'IND': 'Asia', 'IDN': 'Asia', 'THA': 'Asia', 'MYS': 'Asia',
    'PHL': 'Asia', 'VNM': 'Asia', 'PAK': 'Asia', 'BGD': 'Asia', 'LKA': 'Asia',
    'KOR': 'Asia', 'TWN': 'Asia', 'HKG': 'Asia', 'SGP': 'Asia', 'MAC': 'Asia',
    'MNG': 'Asia', 'KHM': 'Asia',
}

# Add region column to df
df['region'] = df['country_code'].map(region_mapping)

# Clean SP rating (remove 'u' suffix if present)
df['sp_rating_clean'] = df['sp_rating'].str.replace('u', '', regex=False)

# Map SP ratings to numeric scores
sp_to_num = dict(zip(map_df['sp'], map_df['num_score']))

# Add special ratings that aren't in the standard mapping
sp_to_num['SD'] = 22  # Selective Default - worse than lowest rating
sp_to_num['NR'] = 21  # Not Rated - assign a value for plotting
sp_to_num['WR'] = 21  # Withdrawn Rating
sp_to_num['WD'] = 21  # Withdrawn

df['sp_num_score'] = df['sp_rating_clean'].map(sp_to_num)

# Check which countries are still missing sp_num_score
print("\nCountries with missing S&P numeric scores:")
missing_sp = df[df['sp_num_score'].isna()][['country', 'country_code', 'sp_rating', 'sp_rating_clean', 'z_spread']]
if len(missing_sp) > 0:
    print(missing_sp[['country_code', 'sp_rating_clean', 'z_spread']].to_string())
else:
    print("None - all countries have numeric scores now!")

# Remove rows with missing critical data
df_plot = df[df['z_spread'].notna() & df['avg_rating'].notna() & df['sp_num_score'].notna()].copy()

print(f"\nData prepared for plotting: {len(df_plot)} countries")
print(f"Regions: {df_plot['region'].value_counts()}")
print(f"Classes: {df_plot['class'].value_counts()}")

# Create figure with single plot
fig, ax = plt.subplots(1, 1, figsize=(14, 8))
fig.suptitle('Sovereign Credit Spread vs Rating Score', fontsize=16, fontweight='bold')

# Define colors and markers
colors = {'IG': '#2E86AB', 'HY': '#A23B72', np.nan: '#808080'}
markers = {'LatAM': 'o', 'EMEA': 's', 'Asia': '^'}
region_labels = {'LatAM': 'Latin America', 'EMEA': 'EMEA', 'Asia': 'Asia'}

# Store all points for smart label positioning
all_points = []

# Plot: Z-Spread vs S&P Rating (numeric score)
for class_type in ['IG', 'HY', np.nan]:
    for region in ['LatAM', 'EMEA', 'Asia']:
        # Filter data
        if pd.isna(class_type):
            mask = df_plot['class'].isna() & (df_plot['region'] == region)
            label = f'Not Rated - {region_labels[region]}'
        else:
            mask = (df_plot['class'] == class_type) & (df_plot['region'] == region)
            label = f'{class_type} - {region_labels[region]}'
        
        data = df_plot[mask]
        
        if len(data) > 0:
            ax.scatter(data['sp_num_score'], data['z_spread'], 
                       c=[colors.get(class_type, colors[np.nan])], 
                       marker=markers[region],
                       s=100, alpha=0.7, edgecolors='black', linewidth=0.5,
                       label=label)
            
            # Store points for label positioning
            for idx, row in data.iterrows():
                all_points.append({
                    'x': row['sp_num_score'],
                    'y': row['z_spread'],
                    'label': row['country_code']
                })

# Smart label positioning to avoid overlaps
# Define offset patterns (in order of preference)
offset_patterns = [
    (6, 6),     # top-right
    (-6, 6),    # top-left
    (6, -6),    # bottom-right
    (-6, -6),   # bottom-left
    (10, 0),    # right
    (-10, 0),   # left
    (0, 10),    # top
    (0, -10),   # bottom
]

def check_overlap(x1, y1, x2, y2, threshold_x=0.4, threshold_y=120):
    """Check if two points are too close (would cause label overlap)"""
    return abs(x1 - x2) < threshold_x and abs(y1 - y2) < threshold_y

# Sort points by x then y to process systematically
all_points_sorted = sorted(all_points, key=lambda p: (p['x'], p['y']))

# Group points by same x-coordinate
from collections import defaultdict
x_groups = defaultdict(list)
for point in all_points_sorted:
    x_groups[point['x']].append(point)

used_positions = []

for point in all_points_sorted:
    x, y = point['x'], point['y']
    
    # Check if there are multiple points at the same x-coordinate
    same_x_points = x_groups[x]
    
    if len(same_x_points) > 1:
        # Multiple points at same rating - use strategic positioning
        idx = same_x_points.index(point)
        
        # Alternate positioning for same x-coordinate
        if idx == 0:
            best_offset = (8, 8)   # First: top-right
        elif idx == 1:
            best_offset = (-8, 8)  # Second: top-left
        elif idx == 2:
            best_offset = (8, -8)  # Third: bottom-right
        else:
            best_offset = (-8, -8) # Fourth: bottom-left
    else:
        # Find best offset that avoids other labels
        best_offset = offset_patterns[0]
        for offset in offset_patterns:
            overlaps = False
            for used_pos in used_positions:
                if check_overlap(x, y, used_pos['x'], used_pos['y']):
                    # Check if this offset would help avoid overlap
                    # This is a simplified check - just try different offsets
                    overlaps = True
                    break
            
            if not overlaps:
                best_offset = offset
                break
    
    # Add label with best offset
    ax.annotate(point['label'], 
               (x, y),
               fontsize=8, alpha=0.85, fontweight='bold',
               xytext=best_offset, textcoords='offset points',
               ha='left' if best_offset[0] >= 0 else 'right',
               va='bottom' if best_offset[1] >= 0 else 'top')
    
    used_positions.append({'x': x, 'y': y})

ax.set_xlabel('Numeric Rating Score', fontsize=12, fontweight='bold')
ax.set_ylabel('Z-Spread (bps)', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3, linestyle='--')
ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)

# Add secondary x-axis with S&P rating labels
ax_top = ax.twiny()
ax_top.set_xlim(ax.get_xlim())
sp_ticks = sorted(df_plot['sp_num_score'].unique())
sp_labels = []
for score in sp_ticks:
    # Find the SP rating for this score (handle multiple ratings with same score)
    ratings = [k for k, v in sp_to_num.items() if v == score]
    if len(ratings) > 1:
        # Multiple ratings map to same score - show all or prioritize
        sp_labels.append('/'.join(sorted(ratings)))
    else:
        sp_labels.append(ratings[0] if ratings else str(int(score)))
ax_top.set_xticks(sp_ticks)
ax_top.set_xticklabels(sp_labels, fontsize=8, rotation=45)
ax_top.set_xlabel('S&P Rating', fontsize=10)

plt.tight_layout()
plt.savefig('sovereign_spread_scatter.png', dpi=300, bbox_inches='tight')
plt.show()

print("\nPlot saved as 'sovereign_spread_scatter.png'")

