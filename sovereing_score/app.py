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

# Regional mapping - using actual country codes from Excel file
REGION_MAPPING = {
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

# Get all available dates from database
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_available_dates():
    """Get all available dates from database (latest + month-end dates)"""
    conn = get_db_connection()
    
    try:
        # Get latest date (could be daily)
        latest_query = """
        SELECT MAX(date) as latest_date
        FROM securitized_research.emd_sovereign_score
        """
        latest_df = pd.read_sql(latest_query, conn)
        latest_date = pd.to_datetime(latest_df['latest_date'].iloc[0]).date()
        
        # Get all month-end dates
        month_end_query = """
        SELECT DISTINCT date
        FROM securitized_research.emd_sovereign_score
        WHERE EXTRACT(DAY FROM date + INTERVAL '1 day') = 1  -- Month-end dates only
        ORDER BY date DESC
        """
        month_end_df = pd.read_sql(month_end_query, conn)
        month_end_dates = [pd.to_datetime(d).date() for d in month_end_df['date']]
        
        # Combine: latest first, then month-ends (excluding latest if it's already a month-end)
        if latest_date in month_end_dates:
            dates = month_end_dates
        else:
            dates = [latest_date] + month_end_dates
            
    finally:
        conn.close()
    
    return dates

# Load data from database
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data(selected_date):
    """Load data from PostgreSQL database for selected date"""
    conn = get_db_connection()
    
    try:
        # Query data for selected date
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
        
        df = pd.read_sql(query, conn, params=(selected_date,))
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
    
    df['region'] = df['country_code'].map(REGION_MAPPING)
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
    
    # Mark outliers/non-rated - includes high-spread distressed countries
    def is_true_outlier(row):
        sp_rating = row['sp_rating_clean']
        fit_rating = row.get('fit_rating_clean', None)
        z_spread = row.get('z_spread', None)
        
        # Check for extreme spreads (> 3000 bps indicates distressed/defaulted)
        if pd.notna(z_spread) and z_spread > 3000:
            return True
        
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
    
    return df, sp_to_num, selected_date

# Load carry-to-vol data from database
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_carry_to_vol_data(as_of_date):
    """Load carry-to-vol metrics for a specific as-of date, joined with latest ratings"""
    conn = get_db_connection()
    
    try:
        # Query carry-to-vol data and join with latest sovereign score for ratings
        query = """
        WITH latest_date AS (
            SELECT MAX(date) as max_date
            FROM securitized_research.emd_sovereign_score
        )
        SELECT 
            c.country_code,
            c.country,
            c.carry_bps,
            c.vol_bps,
            c.carry_to_vol,
            c.data_points,
            c.as_of_date,
            s.sp_rating,
            s.moodys_rating,
            s.fit_rating,
            s.avg_rating,
            s.z_spread,
            s.current_yield,
            s.class
        FROM securitized_research.emd_country_carry_to_vol c
        LEFT JOIN securitized_research.emd_sovereign_score s 
            ON c.country_code = s.country_code 
            AND s.date = (SELECT max_date FROM latest_date)
        WHERE c.as_of_date = %s
        ORDER BY c.carry_to_vol DESC
        """
        
        df = pd.read_sql(query, conn, params=(as_of_date,))
        
        # Add region mapping
        df['region'] = df['country_code'].map(REGION_MAPPING)
        
    finally:
        conn.close()
    
    return df

# Get available dates and default to latest
available_dates = get_available_dates()

if not available_dates:
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

# Date selector
st.sidebar.header("Data Selection")
selected_date = st.sidebar.selectbox(
    "Select Date",
    options=available_dates,
    index=0,  # Default to latest (first in list)
    format_func=lambda x: x.strftime('%Y-%m-%d')
)
st.sidebar.markdown("---")

# Load data for selected date
df, sp_to_num, data_date = load_data(selected_date)

# Display selected date
st.sidebar.markdown(f"**Showing data for:** {data_date.strftime('%Y-%m-%d')}")
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
show_outliers = st.sidebar.checkbox(
    "Include Non-Rated/Defaulted", 
    value=False,
    help="Show countries with extreme spreads (>3000 bps), defaulted, or completely unrated in the data table. These are excluded from the chart for cleaner visualization."
)

# Title
st.title("🌍 EM Sovereign Credit Spread Analysis")

# Create tabs
tab1, tab2, tab3 = st.tabs(["📊 Sovereign Score", "📉 Carry-to-Vol", "📈 Historical Spread"])

# ============================================================================
# TAB 1: SOVEREIGN SCORE (Current scatter plot)
# ============================================================================
with tab1:
    st.markdown("Interactive analysis of sovereign credit spreads vs. rating score")
    
    # Filter data - start with basic filters
    df_filtered = df[
        (df['z_spread'].notna()) & 
        (df['region'].isin(regions))
    ].copy()

    # Apply credit quality filter
    if credit_quality:
        if show_outliers:
            # Include selected credit qualities OR outliers/non-rated
            # Outliers can have NULL avg_rating (completely unrated countries)
            df_filtered = df_filtered[
                (df_filtered['class'].isin(credit_quality)) | 
                (df_filtered['is_outlier'])
            ]
        else:
            # Only include selected credit qualities, and require avg_rating for plotting
            df_filtered = df_filtered[
                (df_filtered['class'].isin(credit_quality)) &
                (df_filtered['avg_rating'].notna())
            ]
    else:
        # If no credit quality selected, require avg_rating for non-outliers
        if show_outliers:
            df_filtered = df_filtered[
                (df_filtered['avg_rating'].notna()) | 
                (df_filtered['is_outlier'])
            ]
        else:
            df_filtered = df_filtered[df_filtered['avg_rating'].notna()]

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
        x_vals = df_data['avg_rating'].values
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
                label_offset = 0.04  # Increased offset distance for larger labels
                label_x = current_x + x_offset * label_offset
                label_y = current_y + y_offset * label_offset
                
                # Calculate distances from label position to all points
                label_distances = np.sqrt((all_x_norm - label_x)**2 + (all_y_norm - label_y)**2)
                
                # Score: minimum distance to any point (we want to maximize this)
                # Also consider average distance to nearby points
                min_distance = label_distances.min()
                nearby_mask = distances < 0.15  # Points near the current point (increased for larger labels)
                avg_nearby_distance = label_distances[nearby_mask].mean() if nearby_mask.sum() > 0 else 1.0
                
                # Combined score: prioritize not being too close to any point
                score = min_distance * 2 + avg_nearby_distance
                
                # Special handling for vertically stacked points (same x, close y)
                vertical_stack_mask = (np.abs(all_x_norm - current_x) < 0.03) & (distances > 0) & (distances < 0.18)
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

    # For plotting, only use countries with valid avg_rating (need x-coordinate)
    # and exclude all outliers for cleaner chart (outliers only appear in data table)
    df_plottable = df_filtered[
    (df_filtered['avg_rating'].notna()) & 
    (~df_filtered['is_outlier'])
    ].copy()

    # Get all point coordinates for global awareness in label positioning
    all_points_x = df_plottable['avg_rating'].values
    all_points_y = df_plottable['z_spread'].values

    # Add scatter points by group - Regular countries (IG and HY)
    for class_type in ['IG', 'HY']:
        for region in ['LatAM', 'EMEA', 'Asia']:
            data = df_plottable[(df_plottable['class'] == class_type) & (df_plottable['region'] == region)]
            
            if len(data) > 0:
                # Get dynamic text positions with global point awareness
                text_positions = get_text_positions(data, all_points_x, all_points_y)
                
                fig.add_trace(go.Scatter(
                x=data['avg_rating'],
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
                textfont=dict(size=12),
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
                              'Avg Rating: %{x:.2f}<br>' +
                              'Avg Outlook: %{customdata[2]}<br>' +
                              '<extra></extra>'
            ))

    # Note: Outliers/non-rated countries are excluded from chart for cleaner visualization
    # but are included in the data table when checkbox is checked

    # Add fitted curve
    if len(df_plottable) > 5:
        X = df_plottable['avg_rating'].values.reshape(-1, 1)
        y = df_plottable['z_spread'].values
        
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
    if len(df_plottable) > 0:
        # Get the range of avg_rating values to determine which rating labels to show
        min_rating = df_plottable['avg_rating'].min()
        max_rating = df_plottable['avg_rating'].max()
        
        # Show integer rating scores within the visible range
        for int_score in range(int(np.floor(min_rating)), int(np.ceil(max_rating)) + 1):
            # Find rating(s) for this integer score
            ratings = [k for k, v in sp_to_num.items() if v == int_score]
            if ratings:
                # Use the first rating or combine multiple
                rating_label = '/'.join(sorted(ratings)[:2])  # Show max 2 ratings if multiple
                
                annotations.append(
                    dict(
                        x=int_score,
                        y=1.08,  # Position above the plot
                        xref='x',
                        yref='paper',
                        text=rating_label,
                        showarrow=False,
                        font=dict(size=11, color='#666'),
                        xanchor='center',
                        yanchor='bottom'
                    )
                )

    # Update layout
    fig.update_layout(
        title="",
        xaxis_title="Average Rating Score (Lower = Better)",
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
        'avg_rating', 'z_spread', 'current_yield', 'avg_outlook'
    ]].copy()

    df_display.columns = [
        'Country', 'Code', 'Region', 'Class',
        'Rating (Chart)', 'S&P', "Moody's", 'Fitch',
        'Avg Rating', 'Z-Spread (bps)', 'Current Yield (%)', 'Outlook'
    ]

    df_display = df_display.sort_values('Z-Spread (bps)', ascending=False)

    # Display with formatting (handle NaN values in avg_rating)
    st.dataframe(
        df_display.style.format({
            'Avg Rating': lambda x: f'{x:.2f}' if pd.notna(x) else 'N/A',
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

# ============================================================================
# TAB 2: CARRY-TO-VOL ANALYSIS
# ============================================================================
with tab2:
    st.markdown("Carry-to-Volatility analysis: Current yield (bps) per unit of spread volatility (bps)")
    
    # Load carry-to-vol data for latest month-end (2026-06-30)
    ctv_as_of_date = '2026-06-30'
    df_ctv = load_carry_to_vol_data(ctv_as_of_date)
    
    if df_ctv.empty:
        st.warning(f"No carry-to-vol data available for {ctv_as_of_date}")
    else:
        # Clean ratings and detect outliers
        df_ctv['sp_rating_clean'] = df_ctv['sp_rating'].str.replace('u', '', regex=False)
        df_ctv['fit_rating_clean'] = df_ctv['fit_rating'].str.replace('u', '', regex=False) if 'fit_rating' in df_ctv.columns else df_ctv['fit_rating']
        
        # Mark outliers - same logic as main tab
        def is_ctv_outlier(row):
            sp_rating = row['sp_rating_clean']
            fit_rating = row.get('fit_rating_clean', None)
            z_spread = row.get('z_spread', None)
            
            # Check for extreme spreads (> 3000 bps indicates distressed/defaulted)
            if pd.notna(z_spread) and z_spread > 3000:
                return True
            
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
        
        df_ctv['is_outlier'] = df_ctv.apply(is_ctv_outlier, axis=1)
        
        # Apply filters: credit quality, region, avg_rating, and outliers
        # Start with basic filters
        df_ctv_filtered = df_ctv[df_ctv['region'].isin(regions)].copy()
        
        # Apply credit quality filter
        if credit_quality:
            if show_outliers:
                # Include selected credit qualities OR outliers/non-rated
                df_ctv_filtered = df_ctv_filtered[
                    (df_ctv_filtered['class'].isin(credit_quality)) | 
                    (df_ctv_filtered['is_outlier'])
                ]
            else:
                # Only include selected credit qualities, and require avg_rating for plotting
                df_ctv_filtered = df_ctv_filtered[
                    (df_ctv_filtered['class'].isin(credit_quality)) &
                    (df_ctv_filtered['avg_rating'].notna())
                ]
        else:
            # If no credit quality selected, require avg_rating for non-outliers
            if show_outliers:
                df_ctv_filtered = df_ctv_filtered[
                    (df_ctv_filtered['avg_rating'].notna()) | 
                    (df_ctv_filtered['is_outlier'])
                ]
            else:
                df_ctv_filtered = df_ctv_filtered[df_ctv_filtered['avg_rating'].notna()]
        
        # Apply outlier filter (exclude outliers if checkbox not selected)
        if not show_outliers:
            df_ctv_filtered = df_ctv_filtered[~df_ctv_filtered['is_outlier']]
        
        # Main metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Countries", len(df_ctv_filtered))
        with col2:
            avg_ctv = df_ctv_filtered['carry_to_vol'].mean() if len(df_ctv_filtered) > 0 else 0
            st.metric("Avg Carry-to-Vol", f"{avg_ctv:.2f}")
        with col3:
            if len(df_ctv_filtered) > 0:
                st.metric("C/V Range", f"{df_ctv_filtered['carry_to_vol'].min():.2f} - {df_ctv_filtered['carry_to_vol'].max():.2f}")
            else:
                st.metric("C/V Range", "N/A")
        
        if len(df_ctv_filtered) == 0:
            st.warning("No countries match the selected filters")
        else:
            # Function to calculate optimal text positions for carry-to-vol chart
            def get_ctv_text_positions(df_data, all_points_x, all_points_y):
                """
                Dynamically assign text positions based on point density and proximity.
                Adapted for carry-to-vol chart.
                """
                if len(df_data) == 0:
                    return []
                
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
                
                x_vals = df_data['avg_rating'].values
                y_vals = df_data['carry_to_vol'].values
                
                if len(x_vals) == 0:
                    return []
                
                # Normalize coordinates
                x_range = all_points_x.max() - all_points_x.min() if all_points_x.max() != all_points_x.min() else 1
                y_range = all_points_y.max() - all_points_y.min() if all_points_y.max() != all_points_y.min() else 1
                
                all_x_norm = (all_points_x - all_points_x.min()) / x_range if x_range > 0 else all_points_x
                all_y_norm = (all_points_y - all_points_y.min()) / y_range if y_range > 0 else all_points_y
                
                x_norm = (x_vals - all_points_x.min()) / x_range if x_range > 0 else x_vals
                y_norm = (y_vals - all_points_y.min()) / y_range if y_range > 0 else y_vals
                
                positions = []
                
                for i in range(len(df_data)):
                    current_x = x_norm[i]
                    current_y = y_norm[i]
                    
                    distances = np.sqrt((all_x_norm - current_x)**2 + (all_y_norm - current_y)**2)
                    
                    best_position = 'top center'
                    best_score = -float('inf')
                    
                    for pos_name, x_offset, y_offset in position_options:
                        label_offset = 0.04
                        label_x = current_x + x_offset * label_offset
                        label_y = current_y + y_offset * label_offset
                        
                        label_distances = np.sqrt((all_x_norm - label_x)**2 + (all_y_norm - label_y)**2)
                        
                        min_distance = label_distances.min()
                        nearby_mask = distances < 0.15
                        avg_nearby_distance = label_distances[nearby_mask].mean() if nearby_mask.sum() > 0 else 1.0
                        
                        score = min_distance * 2 + avg_nearby_distance
                        
                        # Prefer horizontal positions for vertically stacked points
                        vertical_stack_mask = (np.abs(all_x_norm - current_x) < 0.03) & (distances > 0) & (distances < 0.18)
                        if vertical_stack_mask.sum() > 0:
                            if 'left' in pos_name or 'right' in pos_name:
                                score *= 1.5
                        
                        if score > best_score:
                            best_score = score
                            best_position = pos_name
                    
                    positions.append(best_position)
                
                return positions
            
            # For plotting, exclude outliers from chart (even if show_outliers is True)
            # Outliers will only show in the data table
            df_ctv_plottable = df_ctv_filtered[
                (df_ctv_filtered['avg_rating'].notna()) & 
                (~df_ctv_filtered['is_outlier'])
            ].copy()
            
            # Get all point coordinates for smart label positioning
            all_points_x = df_ctv_plottable['avg_rating'].values
            all_points_y = df_ctv_plottable['carry_to_vol'].values
            
            # Calculate optimal text positions
            text_positions = get_ctv_text_positions(df_ctv_plottable, all_points_x, all_points_y)
            
            # Create scatter plot
            fig_ctv = go.Figure()
            
            # Add scatter points
            fig_ctv.add_trace(go.Scatter(
                x=df_ctv_plottable['avg_rating'],
                y=df_ctv_plottable['carry_to_vol'],
                mode='markers+text',
                text=df_ctv_plottable['country_code'],
                textposition=text_positions,
                textfont=dict(size=12),
                marker=dict(
                    size=10,
                    color=df_ctv_plottable['carry_to_vol'],
                    colorscale='RdYlGn',
                    colorbar=dict(title="Carry-to-Vol"),
                    showscale=True
                ),
                customdata=np.column_stack((
                    df_ctv_plottable['country'],
                    df_ctv_plottable['sp_rating'].fillna('N/A'),
                    df_ctv_plottable['moodys_rating'].fillna('N/A'),
                    df_ctv_plottable['fit_rating'].fillna('N/A'),
                    df_ctv_plottable['carry_bps'],
                    df_ctv_plottable['vol_bps'],
                    df_ctv_plottable['z_spread'].fillna(0),
                    df_ctv_plottable['current_yield'].fillna(0),
                    df_ctv_plottable['region'].fillna('N/A'),
                    df_ctv_plottable['class'].fillna('N/A')
                )),
                hovertemplate='<b>%{customdata[0]}</b> (%{text})<br>' +
                             'Avg Rating: %{x:.2f}<br>' +
                             'Carry-to-Vol: %{y:.3f}<br>' +
                             '<br>' +
                             'Carry: %{customdata[4]:.0f} bps<br>' +
                             'Volatility: %{customdata[5]:.0f} bps<br>' +
                             'Z-Spread: %{customdata[6]:.1f} bps<br>' +
                             'Current Yield: %{customdata[7]:.3f}%<br>' +
                             '<br>' +
                             'S&P: %{customdata[1]}<br>' +
                             "Moody's: %{customdata[2]}<br>" +
                             'Fitch: %{customdata[3]}<br>' +
                             'Region: %{customdata[8]}<br>' +
                             'Class: %{customdata[9]}<br>' +
                             '<extra></extra>'
            ))
            
            # Add fitted curve
            if len(df_ctv_plottable) > 5:
                X = df_ctv_plottable['avg_rating'].values.reshape(-1, 1)
                y = df_ctv_plottable['carry_to_vol'].values
                
                # Fit polynomial regression (degree 2)
                poly = PolynomialFeatures(degree=2)
                X_poly = poly.fit_transform(X)
                model = LinearRegression()
                model.fit(X_poly, y)
                
                # Generate smooth curve
                x_curve = np.linspace(X.min(), X.max(), 100).reshape(-1, 1)
                x_curve_poly = poly.transform(x_curve)
                y_curve = model.predict(x_curve_poly)
                
                fig_ctv.add_trace(go.Scatter(
                    x=x_curve.flatten(),
                    y=y_curve,
                    mode='lines',
                    name='Fitted Curve',
                    line=dict(color='red', width=2, dash='dash'),
                    hoverinfo='skip'
                ))
            
            # Update layout with rating scale annotations
            fig_ctv.update_layout(
                title=f"Carry-to-Volatility vs. Credit Rating (as of {ctv_as_of_date})",
                xaxis_title="Average Rating Score",
                yaxis_title="Carry-to-Vol (bps/bps)",
                hovermode='closest',
                height=600,
                xaxis=dict(
                    range=[0, 24],
                    tickmode='array',
                    tickvals=[1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23],
                    ticktext=['AAA', 'AA', 'A+', 'A-', 'BBB', 'BB+', 'BB-', 'B', 'CCC+', 'CCC-', 'CC', 'D'],
                    tickfont=dict(size=11),
                    autorange='reversed'  # Better ratings (lower numbers) on left
                ),
                yaxis=dict(
                    tickfont=dict(size=11)
                ),
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig_ctv, use_container_width=True)
            
            # Data table
            st.subheader("📊 Carry-to-Vol Metrics by Country")
            
            display_ctv = df_ctv_filtered[['country', 'country_code', 'region', 'class', 
                                            'carry_bps', 'vol_bps', 'carry_to_vol', 
                                            'sp_rating', 'moodys_rating', 'fit_rating', 'avg_rating', 
                                            'z_spread', 'current_yield']].copy()
            
            display_ctv.columns = ['Country', 'Code', 'Region', 'Class', 'Carry (bps)', 'Vol (bps)', 'Carry-to-Vol',
                                   'S&P', "Moody's", 'Fitch', 'Avg Rating', 'Z-Spread (bps)', 'Current Yield (%)']
            
            st.dataframe(
                display_ctv.style.format({
                    'Carry (bps)': '{:.0f}',
                    'Vol (bps)': '{:.0f}',
                    'Carry-to-Vol': '{:.3f}',
                    'Avg Rating': lambda x: f'{x:.2f}' if pd.notna(x) else 'N/A',
                    'Z-Spread (bps)': lambda x: f'{x:.1f}' if pd.notna(x) else 'N/A',
                    'Current Yield (%)': lambda x: f'{x:.3f}' if pd.notna(x) else 'N/A'
                }).background_gradient(subset=['Carry-to-Vol'], cmap='RdYlGn'),
                use_container_width=True,
                height=500
            )
        
        # Interpretation guide
        st.markdown("---")
        st.subheader("📖 Interpretation Guide")
        st.markdown("""
        **Carry-to-Volatility Ratio** measures how many basis points of carry (current yield) you earn per unit of spread volatility (risk).
        
        - **High C/V (>7.0)**: Strong risk-adjusted carry - stable spreads relative to yield
        - **Medium C/V (3.0-7.0)**: Moderate risk-adjusted carry
        - **Low C/V (<3.0)**: Weak risk-adjusted carry - volatile spreads relative to yield
        
        **Methodology:**
        - Carry: Current yield in basis points
        - Volatility: Annualized standard deviation of monthly z-spread changes (in bps) over 5 years
        - Ratio: Carry (bps) ÷ Volatility (bps)
        """)

# ============================================================================
# TAB 3: HISTORICAL SPREAD
# ============================================================================
with tab3:
    st.markdown("Historical view of sovereign credit spreads and ratings over time")
    
    # Get list of all unique countries
    @st.cache_data(ttl=300)
    def get_country_list():
        """Get list of countries that have historical data"""
        conn = get_db_connection()
        try:
            query = """
            SELECT DISTINCT country, country_code
            FROM securitized_research.emd_sovereign_score
            ORDER BY country
            """
            df = pd.read_sql(query, conn)
        finally:
            conn.close()
        return df
    
    # Get historical data for a country
    @st.cache_data(ttl=300)
    def get_country_historical_data(country_name):
        """Get all historical data for a specific country"""
        conn = get_db_connection()
        try:
            query = """
            SELECT 
                date,
                country,
                country_code,
                moodys_rating,
                moodys_outlook,
                sp_rating,
                sp_outlook,
                fit_rating,
                fit_outlook,
                avg_rating,
                z_spread,
                current_yield
            FROM securitized_research.emd_sovereign_score
            WHERE country = %s
            ORDER BY date
            """
            df = pd.read_sql(query, conn, params=(country_name,))
            df['date'] = pd.to_datetime(df['date'])
        finally:
            conn.close()
        return df
    
    # Country selector - multi-select
    countries_df = get_country_list()
    country_options = list(countries_df['country'])
    country_codes = dict(zip(countries_df['country'], countries_df['country_code']))
    
    selected_countries = st.multiselect(
        "Select Countries (max 10)",
        options=country_options,
        default=[country_options[0]] if len(country_options) > 0 else [],
        max_selections=10
    )
    
    if len(selected_countries) == 0:
        st.info("Please select at least one country to view historical data")
    else:
        # Define color palette for multiple countries
        color_palette = [
            '#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E',
            '#BC4B51', '#5E60CE', '#F72585', '#4361EE', '#7209B7'
        ]
        
        # Get historical data for all selected countries
        all_hist_data = {}
        for country in selected_countries:
            hist_data = get_country_historical_data(country)
            if len(hist_data) > 0:
                all_hist_data[country] = hist_data
        
        if len(all_hist_data) == 0:
            st.warning("No historical data available for selected countries")
        else:
            # Show different metrics based on single vs multiple selection
            if len(selected_countries) == 1:
                # Single country - detailed metrics
                country = selected_countries[0]
                hist_data = all_hist_data[country]
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Data Points", len(hist_data))
                with col2:
                    st.metric("Date Range", f"{hist_data['date'].min().strftime('%Y-%m')} to {hist_data['date'].max().strftime('%Y-%m')}")
                with col3:
                    latest_spread = hist_data.iloc[-1]['z_spread']
                    st.metric("Latest Z-Spread", f"{latest_spread:.1f} bps")
                with col4:
                    if len(hist_data) > 1:
                        spread_change = hist_data.iloc[-1]['z_spread'] - hist_data.iloc[0]['z_spread']
                        st.metric("Spread Change", f"{spread_change:+.1f} bps", delta=f"{spread_change:+.1f}")
            else:
                # Multiple countries - summary comparison table
                st.subheader("📊 Country Comparison Summary")
                summary_data = []
                for country in selected_countries:
                    if country in all_hist_data:
                        hist_data = all_hist_data[country]
                        summary_data.append({
                            'Country': country,
                            'Code': country_codes[country],
                            'Latest Spread (bps)': hist_data.iloc[-1]['z_spread'],
                            'Latest Current Yield (%)': hist_data.iloc[-1]['current_yield'],
                            'Spread Change (bps)': hist_data.iloc[-1]['z_spread'] - hist_data.iloc[0]['z_spread'] if len(hist_data) > 1 else 0,
                            'Latest Score': hist_data.iloc[-1]['avg_rating'] if pd.notna(hist_data.iloc[-1]['avg_rating']) else None,
                            'Date Range': f"{hist_data['date'].min().strftime('%Y-%m')} to {hist_data['date'].max().strftime('%Y-%m')}"
                        })
                
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(
                    summary_df.style.format({
                        'Latest Spread (bps)': '{:.1f}',
                        'Latest Current Yield (%)': '{:.3f}',
                        'Spread Change (bps)': '{:+.1f}',
                        'Latest Score': lambda x: f'{x:.2f}' if pd.notna(x) else 'N/A'
                    }).background_gradient(subset=['Latest Spread (bps)'], cmap='RdYlGn_r'),
                    use_container_width=True,
                    hide_index=True
                )
            
            # Create time series chart
            fig_ts = go.Figure()
            
            # Add trace for each country
            for idx, country in enumerate(selected_countries):
                if country in all_hist_data:
                    hist_data = all_hist_data[country]
                    color = color_palette[idx % len(color_palette)]
                    
                    # Prepare customdata for hover
                    customdata = np.column_stack((
                        hist_data['sp_rating'].fillna('N/A'),
                        hist_data['moodys_rating'].fillna('N/A'),
                        hist_data['fit_rating'].fillna('N/A'),
                        hist_data['sp_outlook'].fillna('N/A'),
                        hist_data['moodys_outlook'].fillna('N/A'),
                        hist_data['fit_outlook'].fillna('N/A'),
                        hist_data['avg_rating'].fillna(0),
                        hist_data['current_yield'].fillna(0)
                    ))
                    
                    fig_ts.add_trace(go.Scatter(
                        x=hist_data['date'],
                        y=hist_data['z_spread'],
                        mode='lines+markers',
                        name=f"{country} ({country_codes[country]})",
                        line=dict(color=color, width=2),
                        marker=dict(size=4),
                        customdata=customdata,
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                     '%{x|%Y-%m-%d}<br>' +
                                     '<br>' +
                                     'Z-Spread: %{y:.1f} bps<br>' +
                                     'Current Yield: %{customdata[7]:.3f}%<br>' +
                                     'S&P: %{customdata[0]} (%{customdata[3]})<br>' +
                                     'Avg Score: %{customdata[6]:.2f}<br>' +
                                     '<extra></extra>'
                    ))
            
            # Update layout
            chart_title = "Historical Z-Spread Comparison" if len(selected_countries) > 1 else f"{selected_countries[0]} ({country_codes[selected_countries[0]]}) - Historical Z-Spread"
            
            fig_ts.update_layout(
                title=chart_title,
                xaxis_title="Date",
                yaxis_title="Z-Spread (bps)",
                hovermode='x unified',
                height=500,
                showlegend=len(selected_countries) > 1,
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.02
                )
            )
            
            st.plotly_chart(fig_ts, use_container_width=True)
            
            # Show detailed table only for single country selection
            if len(selected_countries) == 1:
                country = selected_countries[0]
                hist_data = all_hist_data[country]
                
                st.subheader("📊 Ratings Evolution")
                
                # Show recent rating changes
                display_hist = hist_data[['date', 'sp_rating', 'sp_outlook', 'moodys_rating', 'moodys_outlook', 
                                           'fit_rating', 'fit_outlook', 'avg_rating', 'z_spread', 'current_yield']].copy()
                display_hist['date'] = display_hist['date'].dt.strftime('%Y-%m-%d')
                display_hist.columns = ['Date', 'S&P', 'S&P Outlook', "Moody's", "Moody's Outlook", 
                                        'Fitch', 'Fitch Outlook', 'Avg Rating', 'Z-Spread (bps)', 'Current Yield (%)']
                
                # Sort by date descending (most recent first)
                display_hist = display_hist.sort_values('Date', ascending=False)
                
                st.dataframe(
                    display_hist.style.format({
                        'Avg Rating': lambda x: f'{x:.2f}' if pd.notna(x) else 'N/A',
                        'Z-Spread (bps)': '{:.2f}',
                        'Current Yield (%)': '{:.3f}'
                    }),
                    use_container_width=True,
                    height=400
                )

