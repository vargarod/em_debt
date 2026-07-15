import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import os
import psycopg2
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Page config
st.set_page_config(page_title="EM Sovereign Credit Spread Analysis", layout="wide")

# Database connection helper
def get_db_connection():
    """Create database connection using environment variable for password"""
    db_password = os.environ.get('DB_PASSWORD')
    
    if not db_password:
        st.error("Database password not configured. Please set DB_PASSWORD environment variable.")
        st.stop()
    
    conn = psycopg2.connect(
        host='gwamdlquantapps-prod-postgresql-server.postgres.database.azure.com',
        port=5432,
        database='postgres',
        user='securitized_team',
        password=db_password,
        sslmode='require'
    )
    return conn

# Get latest date from database
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_latest_date():
    """Get the latest date from database"""
    conn = get_db_connection()
    
    try:
        query = """
        SELECT MAX(date) as latest_date
        FROM securitized_research.emd_sovereign_score
        """
        
        df = pd.read_sql(query, conn)
        latest_date = pd.to_datetime(df['latest_date'].iloc[0]).date()
    finally:
        conn.close()
    
    return latest_date

# Load data from database
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data():
    """Load data from PostgreSQL database for latest date"""
    latest_date = get_latest_date()
    conn = get_db_connection()
    
    try:
        # Query data for latest date
        query = """
        SELECT 
            country,
            country_code,
            moodys_rating,
            moodys_outlook,
            moodys_rat_date,
            sp_rating,
            sp_outlook,
            st_rat_date,
            fit_rating,
            fit_outlook,
            fit_rat_date,
            avg_rating,
            z_spread,
            current_yield,
            class,
            date
        FROM securitized_research.emd_sovereign_score
        WHERE date = %s
        ORDER BY country
        """
        
        df = pd.read_sql(query, conn, params=(latest_date,))
    finally:
        conn.close()
    
    # Create rating score mapping (same as before)
    map_data = {
        'sp': ['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-', 'BBB+', 'BBB', 'BBB-',
               'BB+', 'BB', 'BB-', 'B+', 'B', 'B-', 'CCC+', 'CCC', 'CCC-', 'CC', 'C', 'SD', 'D'],
        'num_score': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                      11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
    }
    map_df = pd.DataFrame(map_data)
    
    # Regional mapping - using actual country codes from Excel file
    region_mapping = {
        # LatAM
        'ARG': 'LatAM', 'BRZ': 'LatAM', 'CHL': 'LatAM', 'COL': 'LatAM', 'MEX': 'LatAM',
        'PER': 'LatAM', 'URU': 'LatAM', 'ECU': 'LatAM', 'PAN': 'LatAM', 'CR': 'LatAM',
        'GUA': 'LatAM', 'DR': 'LatAM', 'PAR': 'LatAM', 'ESV': 'LatAM', 'VEN': 'LatAM',
        'BOL': 'LatAM', 'JAM': 'LatAM', 'T&T': 'LatAM', 'HON': 'LatAM', 'BAR': 'LatAM',
        'SUR': 'LatAM',
        # EMEA
        'SAF': 'EMEA', 'TUR': 'EMEA', 'POL': 'EMEA', 'HUN': 'EMEA', 'ROM': 'EMEA',
        'CZE': 'EMEA', 'HRV': 'EMEA', 'BGR': 'EMEA', 'EGY': 'EMEA', 'MOR': 'EMEA',
        'KEN': 'EMEA', 'NIG': 'EMEA', 'SEN': 'EMEA', 'KSA': 'EMEA', 'UAE': 'EMEA',
        'QAT': 'EMEA', 'BAH': 'EMEA', 'OMA': 'EMEA', 'JOR': 'EMEA', 'LBN': 'EMEA',
        'ISR': 'EMEA', 'RUS': 'EMEA', 'UKR': 'EMEA', 'KAZ': 'EMEA', 'SER': 'EMEA',
        'GHA': 'EMEA', 'IVY': 'EMEA', 'ANG': 'EMEA', 'ETH': 'EMEA', 'TUN': 'EMEA',
        'LEB': 'EMEA', 'GAB': 'EMEA', 'AZE': 'EMEA', 'MOZ': 'EMEA', 'GEO': 'EMEA',
        'UZB': 'EMEA', 'ARM': 'EMEA', 'BEN': 'EMEA', 'RWA': 'EMEA', 'CAM': 'EMEA',
        'IRQ': 'EMEA', 'ZAM': 'EMEA',
        # Asia
        'CHI': 'Asia', 'IND': 'Asia', 'IDO': 'Asia', 'THA': 'Asia', 'MAL': 'Asia',
        'PHI': 'Asia', 'VNM': 'Asia', 'PAK': 'Asia', 'BGD': 'Asia', 'SRL': 'Asia',
        'KOR': 'Asia', 'TWN': 'Asia', 'HKG': 'Asia', 'SGP': 'Asia', 'MAC': 'Asia',
        'MON': 'Asia', 'KHM': 'Asia', 'PAP': 'Asia',
    }
    
    df['region'] = df['country_code'].map(region_mapping)
    df['sp_rating_clean'] = df['sp_rating'].str.replace('u', '', regex=False)
    df['fit_rating_clean'] = df['fit_rating'].str.replace('u', '', regex=False) if 'fit_rating' in df.columns else df['fit_rating']
    
    # Map ratings to numeric scores
    sp_to_num = dict(zip(map_df['sp'], map_df['num_score']))
    sp_to_num['SD'] = 22  # Selective Default
    sp_to_num['NR'] = 21  # Not Rated
    sp_to_num['WR'] = 21  # Withdrawn Rating
    sp_to_num['WD'] = 21  # Withdrawn
    
    # First try S&P rating
    df['sp_num_score'] = df['sp_rating_clean'].map(sp_to_num)
    
    # Create a combined rating that uses Fitch as fallback when S&P is not rated
    def get_rating_with_fallback(row):
        sp_rating = row['sp_rating_clean']
        fit_rating = row.get('fit_rating_clean', None)
        
        # If S&P is not rated/withdrawn/defaulted, use Fitch as fallback
        if sp_rating in ['NR', 'WR', 'WD'] and pd.notna(fit_rating) and fit_rating not in ['NR', 'WR', 'WD']:
            # Use Fitch rating (same scale as S&P)
            return fit_rating
        else:
            return sp_rating
    
    df['rating_for_score'] = df.apply(get_rating_with_fallback, axis=1)
    df['sp_num_score'] = df['rating_for_score'].map(sp_to_num)
    
    # Calculate average outlook
    def get_avg_outlook(row):
        outlooks = []
        for col in ['moodys_outlook', 'sp_outlook', 'fit_outlook']:
            if pd.notna(row[col]):
                outlooks.append(row[col].upper())
        
        if not outlooks:
            return 'N/A'
        
        # Count outlook types
        stable = sum(1 for o in outlooks if 'STABLE' in o or 'STAB' in o)
        positive = sum(1 for o in outlooks if 'POS' in o or 'UP' in o)
        negative = sum(1 for o in outlooks if 'NEG' in o or 'DOWN' in o)
        
        if positive > negative and positive > stable:
            return 'Positive'
        elif negative > positive and negative > stable:
            return 'Negative'
        else:
            return 'Stable'
    
    df['avg_outlook'] = df.apply(get_avg_outlook, axis=1)
    
    # Mark outliers/non-rated - only if BOTH S&P and Fitch are not available
    def is_true_outlier(row):
        sp_rating = row['sp_rating_clean']
        fit_rating = row.get('fit_rating_clean', None)
        
        # If S&P is not rated
        if sp_rating in ['SD', 'NR', 'WR', 'WD']:
            # Check if Fitch is available and valid
            if pd.notna(fit_rating) and fit_rating not in ['SD', 'NR', 'WR', 'WD']:
                return False  # Has Fitch rating, so not an outlier
            else:
                return True  # No valid alternative rating
        else:
            # S&P is defaulted
            if sp_rating in ['SD']:
                return True
            return False
    
    df['is_outlier'] = df.apply(is_true_outlier, axis=1)
    
    return df, sp_to_num, latest_date

# Get latest date
latest_date = get_latest_date()

if not latest_date:
    st.error("No data available in database")
    st.stop()

# Sidebar with logo
try:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Try local input folder first (deployed), then parent directory (local dev)
    logo_paths = [
        os.path.join(base_dir, "input", "mimLogo.svg"),
        os.path.join(base_dir, "..", "input", "mimLogo.svg")
    ]
    logo_path = next((p for p in logo_paths if os.path.exists(p)), None)
    if logo_path:
        st.sidebar.image(logo_path, width=220)
except:
    pass  # If logo not found, just skip it

st.sidebar.markdown("---")

# Load data for latest date
df, sp_to_num, data_date = load_data()

# Display data date
st.sidebar.markdown(f"**Data as of:** {data_date.strftime('%Y-%m-%d')}")
st.sidebar.markdown("---")

# Sidebar filters
st.sidebar.header("Filters")

# Credit quality filter
credit_quality = st.sidebar.multiselect(
    "Credit Quality",
    options=['IG', 'HY'],
    default=['IG', 'HY']
)

# Region filter
regions = st.sidebar.multiselect(
    "Geographic Region",
    options=['LatAM', 'EMEA', 'Asia'],
    default=['LatAM', 'EMEA', 'Asia']
)

# Outlier filter
show_outliers = st.sidebar.checkbox("Include Non-Rated/Defaulted", value=False)

# Title
st.title("🌍 EM Sovereign Credit Spread Analysis")
st.markdown("Interactive analysis of sovereign credit spreads vs. rating score")

# Filter data
df_filtered = df[
    (df['z_spread'].notna()) & 
    (df['sp_num_score'].notna()) &
    (df['region'].isin(regions))
].copy()

# Apply credit quality filter
if credit_quality:
    if show_outliers:
        # Include selected credit qualities OR outliers/non-rated
        df_filtered = df_filtered[
            (df_filtered['class'].isin(credit_quality)) | 
            (df_filtered['is_outlier'])
        ]
    else:
        # Only include selected credit qualities
        df_filtered = df_filtered[df_filtered['class'].isin(credit_quality)]

# Apply outlier filter (exclude outliers if checkbox not selected)
if not show_outliers:
    df_filtered = df_filtered[~df_filtered['is_outlier']]

# Main content
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Countries", len(df_filtered))
with col2:
    st.metric("Avg Z-Spread", f"{df_filtered['z_spread'].mean():.1f} bps")
with col3:
    st.metric("Spread Range", f"{df_filtered['z_spread'].min():.0f} - {df_filtered['z_spread'].max():.0f} bps")

# Function to calculate optimal text positions to avoid overlap
def get_text_positions(df_data, all_points_x, all_points_y):
    """
    Dynamically assign text positions based on point density and proximity to ALL points.
    Returns array of position strings for each point.
    
    Args:
        df_data: DataFrame subset for this group
        all_points_x: All x-coordinates in the entire filtered dataset
        all_points_y: All y-coordinates in the entire filtered dataset
    """
    if len(df_data) == 0:
        return []
    
    # Position options with their relative offsets (for scoring)
    # Format: (position_name, x_offset, y_offset) where offsets indicate direction
    position_options = [
        ('top center', 0, 1),
        ('bottom center', 0, -1),
        ('middle right', 1, 0),
        ('middle left', -1, 0),
        ('top right', 0.7, 0.7),
        ('top left', -0.7, 0.7),
        ('bottom right', 0.7, -0.7),
        ('bottom left', -0.7, -0.7)
    ]
    
    # Get coordinates for this group
    x_vals = df_data['sp_num_score'].values
    y_vals = df_data['z_spread'].values
    
    if len(x_vals) == 0:
        return []
    
    # Normalize all coordinates (global normalization)
    x_range = all_points_x.max() - all_points_x.min() if all_points_x.max() != all_points_x.min() else 1
    y_range = all_points_y.max() - all_points_y.min() if all_points_y.max() != all_points_y.min() else 1
    
    all_x_norm = (all_points_x - all_points_x.min()) / x_range if x_range > 0 else all_points_x
    all_y_norm = (all_points_y - all_points_y.min()) / y_range if y_range > 0 else all_points_y
    
    x_norm = (x_vals - all_points_x.min()) / x_range if x_range > 0 else x_vals
    y_norm = (y_vals - all_points_y.min()) / y_range if y_range > 0 else y_vals
    
    positions = []
    
    # For each point in this group, find the best position
    for i in range(len(df_data)):
        current_x = x_norm[i]
        current_y = y_norm[i]
        
        # Calculate distances to ALL points in the plot
        distances = np.sqrt((all_x_norm - current_x)**2 + (all_y_norm - current_y)**2)
        
        # Score each position based on how well it avoids other points
        best_position = 'top center'
        best_score = -float('inf')
        
        for pos_name, x_offset, y_offset in position_options:
            # Calculate where the label would be placed (approximate offset in normalized space)
            label_offset = 0.03  # Approximate label offset distance
            label_x = current_x + x_offset * label_offset
            label_y = current_y + y_offset * label_offset
            
            # Calculate distances from label position to all points
            label_distances = np.sqrt((all_x_norm - label_x)**2 + (all_y_norm - label_y)**2)
            
            # Score: minimum distance to any point (we want to maximize this)
            # Also consider average distance to nearby points
            min_distance = label_distances.min()
            nearby_mask = distances < 0.12  # Points near the current point
            avg_nearby_distance = label_distances[nearby_mask].mean() if nearby_mask.sum() > 0 else 1.0
            
            # Combined score: prioritize not being too close to any point
            score = min_distance * 2 + avg_nearby_distance
            
            # Special handling for vertically stacked points (same x, close y)
            vertical_stack_mask = (np.abs(all_x_norm - current_x) < 0.02) & (distances > 0) & (distances < 0.15)
            if vertical_stack_mask.sum() > 0:
                # For stacked points, prefer horizontal positions
                if 'left' in pos_name or 'right' in pos_name:
                    score *= 1.5
            
            if score > best_score:
                best_score = score
                best_position = pos_name
        
        positions.append(best_position)
    
    return positions

# Create scatter plot
fig = go.Figure()

# Color and symbol mapping
color_map = {'IG': '#2E86AB', 'HY': '#A23B72', 'Not Rated': '#808080'}
symbol_map = {'LatAM': 'circle', 'EMEA': 'square', 'Asia': 'triangle-up'}

# Separate outliers from regular countries
df_regular = df_filtered[~df_filtered['is_outlier']]
df_outliers = df_filtered[df_filtered['is_outlier']]

# Get all point coordinates for global awareness in label positioning
all_points_x = df_filtered['sp_num_score'].values
all_points_y = df_filtered['z_spread'].values

# Add scatter points by group - Regular countries (IG and HY)
for class_type in ['IG', 'HY']:
    for region in ['LatAM', 'EMEA', 'Asia']:
        data = df_regular[(df_regular['class'] == class_type) & (df_regular['region'] == region)]
        
        if len(data) > 0:
            # Get dynamic text positions with global point awareness
            text_positions = get_text_positions(data, all_points_x, all_points_y)
            
            fig.add_trace(go.Scatter(
                x=data['sp_num_score'],
                y=data['z_spread'],
                mode='markers+text',
                name=f'{class_type} - {region}',
                marker=dict(
                    size=12,
                    color=color_map.get(class_type, '#808080'),
                    symbol=symbol_map.get(region, 'circle'),
                    line=dict(width=1, color='black')
                ),
                text=data['country_code'],
                textposition=text_positions,
                textfont=dict(size=8),
                customdata=np.column_stack((
                    data['country'],
                    data['rating_for_score'],
                    data['avg_outlook'],
                    data['moodys_rating'],
                    data['fit_rating'],
                    data['sp_rating_clean'],
                    data['current_yield']
                )),
                hovertemplate='<b>%{customdata[0]}</b><br>' +
                              'Rating (for chart): %{customdata[1]}<br>' +
                              'S&P: %{customdata[5]}<br>' +
                              "Moody's: %{customdata[3]}<br>" +
                              'Fitch: %{customdata[4]}<br>' +
                              'Z-Spread: %{y:.1f} bps<br>' +
                              'Current Yield: %{customdata[6]:.3f}%<br>' +
                              'Numeric Score: %{x:.1f}<br>' +
                              'Avg Outlook: %{customdata[2]}<br>' +
                              '<extra></extra>'
            ))

# Plot outliers/non-rated countries in gray (if included)
if show_outliers and len(df_outliers) > 0:
    for region in ['LatAM', 'EMEA', 'Asia']:
        data = df_outliers[df_outliers['region'] == region]
        
        if len(data) > 0:
            # Get dynamic text positions for outliers with global point awareness
            text_positions = get_text_positions(data, all_points_x, all_points_y)
            
            fig.add_trace(go.Scatter(
                x=data['sp_num_score'],
                y=data['z_spread'],
                mode='markers+text',
                name=f'Non-Rated - {region}',
                marker=dict(
                    size=12,
                    color='#808080',  # Gray for all non-rated
                    symbol=symbol_map.get(region, 'circle'),
                    line=dict(width=1, color='black')
                ),
                text=data['country_code'],
                textposition=text_positions,
                textfont=dict(size=8),
                customdata=np.column_stack((
                    data['country'],
                    data['rating_for_score'],
                    data['avg_outlook'],
                    data['moodys_rating'],
                    data['fit_rating'],
                    data['sp_rating_clean'],
                    data['current_yield']
                )),
                hovertemplate='<b>%{customdata[0]}</b><br>' +
                              'Rating (for chart): %{customdata[1]}<br>' +
                              'S&P: %{customdata[5]}<br>' +
                              "Moody's: %{customdata[3]}<br>" +
                              'Fitch: %{customdata[4]}<br>' +
                              'Z-Spread: %{y:.1f} bps<br>' +
                              'Current Yield: %{customdata[6]:.3f}%<br>' +
                              'Numeric Score: %{x:.1f}<br>' +
                              'Avg Outlook: %{customdata[2]}<br>' +
                              '<extra></extra>'
            ))

# Add fitted curve
if len(df_filtered) > 5:
    X = df_filtered['sp_num_score'].values.reshape(-1, 1)
    y = df_filtered['z_spread'].values
    
    # Fit polynomial regression (degree 2)
    poly = PolynomialFeatures(degree=2)
    X_poly = poly.fit_transform(X)
    model = LinearRegression()
    model.fit(X_poly, y)
    
    # Generate smooth curve
    x_curve = np.linspace(X.min(), X.max(), 100).reshape(-1, 1)
    x_curve_poly = poly.transform(x_curve)
    y_curve = model.predict(x_curve_poly)
    
    fig.add_trace(go.Scatter(
        x=x_curve.flatten(),
        y=y_curve,
        mode='lines',
        name='Fitted Curve',
        line=dict(color='red', width=2, dash='dash'),
        hoverinfo='skip'
    ))

# Create annotations for rating labels at top of chart
annotations = []
if len(df_filtered) > 0:
    # Get unique numeric scores and their corresponding ratings
    unique_scores = sorted(df_filtered['sp_num_score'].unique())
    
    for score in unique_scores:
        # Find rating(s) for this score
        ratings = [k for k, v in sp_to_num.items() if v == score]
        if ratings:
            # Use the first rating or combine multiple
            rating_label = '/'.join(sorted(ratings)[:2])  # Show max 2 ratings if multiple
            
            annotations.append(
                dict(
                    x=score,
                    y=1.08,  # Position above the plot
                    xref='x',
                    yref='paper',
                    text=rating_label,
                    showarrow=False,
                    font=dict(size=9, color='#666'),
                    xanchor='center',
                    yanchor='bottom'
                )
            )

# Update layout
fig.update_layout(
    title="",
    xaxis_title="Numeric Rating Score (Lower = Better)",
    yaxis_title="Z-Spread (bps)",
    hovermode='closest',
    height=650,  # Increased height to accommodate top labels
    showlegend=True,
    legend=dict(
        orientation="v",
        yanchor="top",
        y=1,
        xanchor="left",
        x=1.02
    ),
    plot_bgcolor='white',
    xaxis=dict(
        showgrid=True,
        gridcolor='lightgray',
        zeroline=False
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor='lightgray',
        zeroline=False
    ),
    annotations=annotations,
    margin=dict(t=100)  # Extra top margin for rating labels
)

st.plotly_chart(fig, use_container_width=True)

# Data table
st.subheader("📊 Underlying Data")

# Prepare display dataframe
df_display = df_filtered[[
    'country', 'country_code', 'region', 'class', 
    'rating_for_score', 'sp_rating', 'moodys_rating', 'fit_rating',
    'avg_rating', 'sp_num_score', 'z_spread', 'current_yield', 'avg_outlook'
]].copy()

df_display.columns = [
    'Country', 'Code', 'Region', 'Class',
    'Rating (Chart)', 'S&P', "Moody's", 'Fitch',
    'Avg Rating', 'Numeric Score', 'Z-Spread (bps)', 'Current Yield (%)', 'Outlook'
]

df_display = df_display.sort_values('Z-Spread (bps)', ascending=False)

# Display with formatting
st.dataframe(
    df_display.style.format({
        'Avg Rating': '{:.2f}',
        'Numeric Score': '{:.1f}',
        'Z-Spread (bps)': '{:.2f}',
        'Current Yield (%)': '{:.3f}'
    }).background_gradient(subset=['Z-Spread (bps)'], cmap='RdYlGn_r'),
    use_container_width=True,
    height=400
)

# Download button
csv = df_display.to_csv(index=False)
st.download_button(
    label="📥 Download Data as CSV",
    data=csv,
    file_name="sovereign_spread_data.csv",
    mime="text/csv"
)

# Summary statistics
st.subheader("📈 Summary Statistics by Group")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**By Credit Quality**")
    if len(df_filtered[df_filtered['class'].notna()]) > 0:
        summary_class = df_filtered.groupby('class')['z_spread'].agg(['count', 'mean', 'median', 'std'])
        summary_class.columns = ['Count', 'Mean Spread', 'Median Spread', 'Std Dev']
        st.dataframe(summary_class.style.format({
            'Mean Spread': '{:.1f}',
            'Median Spread': '{:.1f}',
            'Std Dev': '{:.1f}'
        }))

with col2:
    st.markdown("**By Region**")
    summary_region = df_filtered.groupby('region')['z_spread'].agg(['count', 'mean', 'median', 'std'])
    summary_region.columns = ['Count', 'Mean Spread', 'Median Spread', 'Std Dev']
    st.dataframe(summary_region.style.format({
        'Mean Spread': '{:.1f}',
        'Median Spread': '{:.1f}',
        'Std Dev': '{:.1f}'
    }))
