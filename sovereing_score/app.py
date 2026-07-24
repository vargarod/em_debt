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
    # LatAM - Currency codes (for JPMaQS)
    'BRL': 'LatAM', 'CLP': 'LatAM', 'COP': 'LatAM', 'DOP': 'LatAM', 'MXN': 'LatAM',
    'PEN': 'LatAM', 'UYU': 'LatAM',
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
    # EMEA - Currency codes (for JPMaQS)
    'HUF': 'EMEA', 'PLN': 'EMEA', 'RUB': 'EMEA', 'RSD': 'EMEA', 'TRY': 'EMEA',
    'AED': 'EMEA', 'EGP': 'EMEA', 'NGN': 'EMEA', 'OMR': 'EMEA', 'QAR': 'EMEA',
    'ZAR': 'EMEA', 'SAR': 'EMEA',
    # Asia
    'CHI': 'Asia', 'IND': 'Asia', 'IDO': 'Asia', 'THA': 'Asia', 'MAL': 'Asia',
    'PHI': 'Asia', 'VNM': 'Asia', 'PAK': 'Asia', 'BGD': 'Asia', 'SRL': 'Asia',
    'KOR': 'Asia', 'TWN': 'Asia', 'HKG': 'Asia', 'SGP': 'Asia', 'MAC': 'Asia',
    'MON': 'Asia', 'KHM': 'Asia', 'PAP': 'Asia',
    # Asia - Currency codes (for JPMaQS)
    'CNY': 'Asia', 'IDR': 'Asia', 'INR': 'Asia', 'PHP': 'Asia',
}

# Currency code to country code mapping (for JPMaQS data)
CURRENCY_TO_COUNTRY = {
    # LatAM
    'BRL': 'BRZ', 'CLP': 'CHL', 'COP': 'COL', 'DOP': 'DR', 'MXN': 'MEX',
    'PEN': 'PER', 'UYU': 'URU',
    # EMEA
    'HUF': 'HUN', 'PLN': 'POL', 'RUB': 'RUS', 'RSD': 'SER', 'TRY': 'TUR',
    'AED': 'UAE', 'EGP': 'EGY', 'NGN': 'NIG', 'OMR': 'OMA', 'QAR': 'QAT',
    'ZAR': 'SAF', 'SAR': 'KSA',
    # Asia
    'CNY': 'CHI', 'IDR': 'IDO', 'INR': 'IND', 'PHP': 'PHI',
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
        # Query data for selected date with 3M, 6M, and 12M momentum
        query = """
        WITH month_end_dates AS (
            -- Get all month-end dates
            SELECT DISTINCT date
            FROM securitized_research.emd_sovereign_score
            WHERE EXTRACT(DAY FROM date + INTERVAL '1 day') = 1
               OR date = (SELECT MAX(date) FROM securitized_research.emd_sovereign_score)
            ORDER BY date DESC
        ),
        three_months_ago AS (
            -- Get the month-end date closest to 3 months ago from selected date
            SELECT date as past_date
            FROM month_end_dates
            WHERE date <= %s - INTERVAL '3 months'
            ORDER BY date DESC
            LIMIT 1
        ),
        six_months_ago AS (
            -- Get the month-end date closest to 6 months ago from selected date
            SELECT date as past_date
            FROM month_end_dates
            WHERE date <= %s - INTERVAL '6 months'
            ORDER BY date DESC
            LIMIT 1
        ),
        twelve_months_ago AS (
            -- Get the month-end date closest to 12 months ago from selected date
            SELECT date as past_date
            FROM month_end_dates
            WHERE date <= %s - INTERVAL '12 months'
            ORDER BY date DESC
            LIMIT 1
        )
        SELECT 
            curr.country,
            curr.country_code,
            curr.moodys_rating,
            curr.moodys_outlook,
            curr.moodys_rat_date,
            curr.sp_rating,
            curr.sp_outlook,
            curr.st_rat_date,
            curr.fit_rating,
            curr.fit_outlook,
            curr.fit_rat_date,
            curr.avg_rating,
            curr.z_spread,
            curr.current_yield,
            curr.class,
            curr.date,
            past_3m.z_spread as z_spread_3m_ago,
            past_6m.z_spread as z_spread_6m_ago,
            past_12m.z_spread as z_spread_12m_ago
        FROM securitized_research.emd_sovereign_score curr
        LEFT JOIN securitized_research.emd_sovereign_score past_3m
            ON curr.country_code = past_3m.country_code
            AND past_3m.date = (SELECT past_date FROM three_months_ago)
        LEFT JOIN securitized_research.emd_sovereign_score past_6m
            ON curr.country_code = past_6m.country_code
            AND past_6m.date = (SELECT past_date FROM six_months_ago)
        LEFT JOIN securitized_research.emd_sovereign_score past_12m
            ON curr.country_code = past_12m.country_code
            AND past_12m.date = (SELECT past_date FROM twelve_months_ago)
        WHERE curr.date = %s
        ORDER BY curr.country
        """
        
        df = pd.read_sql(query, conn, params=(selected_date, selected_date, selected_date, selected_date))
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
    
    # Add rating bucket for peer comparison
    def get_rating_bucket(rating):
        if pd.isna(rating):
            return 'NR'
        elif rating <= 3:
            return 'AAA-AA'
        elif rating <= 5:
            return 'A'
        elif rating <= 9:
            return 'BBB'
        elif rating <= 13:
            return 'BB'
        elif rating <= 17:
            return 'B'
        else:
            return 'CCC+'
    
    df['rating_bucket'] = df['avg_rating'].apply(get_rating_bucket)
    
    # Calculate z-score (std devs from peer mean) for spread within rating bucket
    # Negative z-score = cheap vs peers, Positive = expensive vs peers
    df['spread_zscore'] = df.groupby('rating_bucket')['z_spread'].transform(
        lambda x: (x - x.mean()) / x.std() if len(x) > 2 and x.std() > 0 else 0
    )
    
    # Add visual signal for relative value
    # Positive z-score = wider spread than peers = CHEAP (good value)
    # Negative z-score = tighter spread than peers = RICH (expensive)
    def get_value_signal(z):
        if pd.isna(z):
            return '⚪ N/A'
        elif z > 1.0:
            return '🟢 Very Cheap'
        elif z > 0.5:
            return '🟢 Cheap'
        elif z > -0.5:
            return '🟡 Fair'
        elif z > -1.0:
            return '🔴 Rich'
        else:
            return '🔴 Very Rich'
    
    df['value_signal'] = df['spread_zscore'].apply(get_value_signal)
    
    # Calculate 3-month, 6-month, and 12-month momentum (spread change)
    # Positive momentum = spread tightening (good), Negative = spread widening (bad)
    df['momentum_3m'] = np.where(
        df['z_spread_3m_ago'].notna(),
        ((df['z_spread_3m_ago'] - df['z_spread']) / df['z_spread_3m_ago'] * 100),
        np.nan
    )
    
    df['momentum_6m'] = np.where(
        df['z_spread_6m_ago'].notna(),
        ((df['z_spread_6m_ago'] - df['z_spread']) / df['z_spread_6m_ago'] * 100),
        np.nan
    )
    
    df['momentum_12m'] = np.where(
        df['z_spread_12m_ago'].notna(),
        ((df['z_spread_12m_ago'] - df['z_spread']) / df['z_spread_12m_ago'] * 100),
        np.nan
    )
    
    # Calculate acceleration: is tightening speeding up or slowing down?
    # Positive = accelerating tightening, Negative = decelerating/losing momentum
    df['acceleration'] = df['momentum_3m'] - df['momentum_12m']
    
    # Calculate percentile rank for 12M momentum (only for countries with momentum data)
    df['momentum_percentile'] = df['momentum_12m'].rank(pct=True, method='average') * 100
    
    # Assign momentum signal based on percentile ranking and actual momentum direction
    def get_momentum_signal(row):
        percentile = row['momentum_percentile']
        momentum = row['momentum_12m']
        
        if pd.isna(momentum):
            return '⚪ N/A'
        elif percentile >= 80:
            return '🟢 Positive'
        elif percentile <= 20 and momentum < 0:
            return '🔴 Negative'
        else:
            return '🟡 Neutral'
    
    df['momentum_signal'] = df.apply(get_momentum_signal, axis=1)
    
    # Assign acceleration signal
    def get_acceleration_signal(accel):
        if pd.isna(accel):
            return '⚪ N/A'
        elif accel > 5:
            return '🟢 Accelerating'
        elif accel < -5:
            return '🔴 Decelerating'
        else:
            return '🟡 Steady'
    
    df['acceleration_signal'] = df['acceleration'].apply(get_acceleration_signal)
    
    # Create forward-looking signal combining outlook + momentum
    def get_forward_signal(row):
        outlook = row['avg_outlook']
        momentum_sig = row['momentum_signal']
        accel_sig = row['acceleration_signal']
        
        # Positive Outlook + Positive Momentum = Very Positive
        if outlook == 'Positive' and momentum_sig == '🟢 Positive':
            return '🟢🟢 Very Positive'
        # Negative Outlook + Negative Momentum = Very Negative
        elif outlook == 'Negative' and momentum_sig == '🔴 Negative':
            return '🔴🔴 Very Negative'
        # Negative Outlook + Positive Momentum = Market ahead of agencies (opportunity)
        elif outlook == 'Negative' and momentum_sig == '🟢 Positive':
            return '🟢 Positive (Improving)'
        # Positive Outlook + Negative Momentum = Conflicting signal
        elif outlook == 'Positive' and momentum_sig == '🔴 Negative':
            return '🟡 Mixed (Deteriorating)'
        # Accelerating with any positive outlook
        elif accel_sig == '🟢 Accelerating' and outlook in ['Positive', 'Stable']:
            return '🟢 Positive'
        # Otherwise neutral or stable
        elif momentum_sig == '🟢 Positive':
            return '🟢 Positive'
        elif momentum_sig == '🔴 Negative':
            return '🔴 Negative'
        else:
            return '🟡 Neutral'
    
    df['forward_signal'] = df.apply(get_forward_signal, axis=1)
    
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
        
        # Add rating bucket for peer comparison
        def get_rating_bucket(rating):
            if pd.isna(rating):
                return 'NR'
            elif rating <= 3:
                return 'AAA-AA'
            elif rating <= 5:
                return 'A'
            elif rating <= 9:
                return 'BBB'
            elif rating <= 13:
                return 'BB'
            elif rating <= 17:
                return 'B'
            else:
                return 'CCC+'
        
        df['rating_bucket'] = df['avg_rating'].apply(get_rating_bucket)
        
        # Calculate z-score for carry-to-vol within rating bucket
        # Positive z-score = better risk-adjusted returns than peers
        # Negative z-score = worse risk-adjusted returns than peers
        df['ctv_zscore'] = df.groupby('rating_bucket')['carry_to_vol'].transform(
            lambda x: (x - x.mean()) / x.std() if len(x) > 2 and x.std() > 0 else 0
        )
        
        # Add visual signal for risk-adjusted return quality
        # Positive z-score = better compensation per unit of risk than peers = GOOD
        # Negative z-score = worse compensation per unit of risk than peers = POOR
        def get_ctv_value_signal(z):
            if pd.isna(z):
                return '⚪ N/A'
            elif z > 1.0:
                return '🟢 Excellent'
            elif z > 0.5:
                return '🟢 Good'
            elif z > -0.5:
                return '🟡 Average'
            elif z > -1.0:
                return '🔴 Below Avg'
            else:
                return '🔴 Poor'
        
        df['ctv_value_signal'] = df['ctv_zscore'].apply(get_ctv_value_signal)
        
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
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Sovereign Score", 
    "📉 Carry-to-Vol", 
    "📈 Historical Spread",
    "🎯 Fundamental Risk"
])

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
        'avg_rating', 'rating_bucket', 'z_spread', 'spread_zscore', 'value_signal',
        'momentum_3m', 'momentum_6m', 'momentum_12m', 'acceleration', 
        'momentum_signal', 'acceleration_signal', 'forward_signal',
        'current_yield', 'avg_outlook'
    ]].copy()

    df_display.columns = [
        'Country', 'Code', 'Region', 'Class',
        'Rating (Chart)', 'S&P', "Moody's", 'Fitch',
        'Avg Rating', 'Peer Group', 'Z-Spread (bps)', 'Z-Score vs Peers', 'Value Signal',
        '3M Mom (%)', '6M Mom (%)', '12M Mom (%)', 'Accel', 
        'Momentum', 'Acceleration', 'Forward Signal',
        'Current Yield (%)', 'Outlook'
    ]

    df_display = df_display.sort_values('12M Mom (%)', ascending=False, na_position='last')  # Best momentum first

    # Display with formatting (handle NaN values in avg_rating)
    st.dataframe(
        df_display.style.format({
            'Avg Rating': lambda x: f'{x:.2f}' if pd.notna(x) else 'N/A',
            'Z-Spread (bps)': '{:.2f}',
            'Z-Score vs Peers': lambda x: f'{x:.2f}' if pd.notna(x) else 'N/A',
            '3M Mom (%)': lambda x: f'{x:+.1f}%' if pd.notna(x) else 'N/A',
            '6M Mom (%)': lambda x: f'{x:+.1f}%' if pd.notna(x) else 'N/A',
            '12M Mom (%)': lambda x: f'{x:+.1f}%' if pd.notna(x) else 'N/A',
            'Accel': lambda x: f'{x:+.1f}' if pd.notna(x) else 'N/A',
            'Current Yield (%)': '{:.3f}'
        }).background_gradient(subset=['Z-Score vs Peers'], cmap='RdYlGn_r', vmin=-2, vmax=2)
          .background_gradient(subset=['12M Mom (%)'], cmap='RdYlGn', vmin=-50, vmax=50)
          .background_gradient(subset=['Accel'], cmap='RdYlGn', vmin=-10, vmax=10),
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
    
    # Value signal interpretation
    st.markdown("---")
    st.subheader("📖 Interpretation Guide")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Z-Score vs Peers (Relative Value)**")
        st.markdown("""
        Measures how expensive/cheap a country trades relative to similar-rated sovereigns:
        - **🟢 Very Cheap (z > 1.0)**: Spread >1σ WIDER than peers
        - **🟢 Cheap (0.5 < z < 1.0)**: Spread wider than peers
        - **🟡 Fair (-0.5 < z < 0.5)**: In-line with peers
        - **🔴 Rich (-1.0 < z < -0.5)**: Spread tighter than peers
        - **🔴 Very Rich (z < -1.0)**: Spread >1σ TIGHTER than peers
        
        Wider spread = higher yield = Cheap.
        """)
    
    with col2:
        st.markdown("**12-Month Momentum**")
        st.markdown("""
        Spread change over past 12 months (month-end to month-end):
        - **🟢 Positive (≥80th %ile)**: Top 20% performers - strongest tightening
        - **🟡 Neutral**: Middle performers or relative underperformers still tightening
        - **🔴 Negative (≤20th %ile + widening)**: Bottom 20% + actual spread widening
        
        **Focuses on absolute deterioration, not relative underperformance.**
        """)
    
    st.markdown("---")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("**Acceleration Signal**")
        st.markdown("""
        Compares 3M vs 12M momentum to detect trend changes:
        - **🟢 Accelerating (>+5)**: Tightening is speeding up (3M better than 12M)
        - **🟡 Steady (±5)**: Consistent pace of change
        - **🔴 Decelerating (<-5)**: Tightening is slowing or widening accelerating
        
        **Early warning for momentum shifts.** Positive acceleration = gaining momentum.
        """)
    
    with col4:
        st.markdown("**Forward Signal (Outlook + Momentum)**")
        st.markdown("""
        Combines rating agency outlook with market momentum:
        - **🟢🟢 Very Positive**: Positive outlook + strong momentum (aligned bullish)
        - **🟢 Positive**: Market improving (agencies may follow)
        - **🟡 Mixed**: Conflicting signals between agencies and market
        - **🔴 Negative**: Single warning flag
        - **🔴🔴 Very Negative**: Negative outlook + widening (aligned bearish)
        
        **Best predictor when agencies and market align.**
        """)
    
    st.markdown("""
    ---
    **Investment Strategies:**
    
    | Strategy | Value Signal | Momentum Signal | Acceleration Signal | Forward Signal | Thesis |
    |----------|--------------|-----------------|---------------------|----------------|--------|
    | **High Conviction Buy** | 🟢 Cheap | 🟢 Positive | 🟢 Accelerating | 🟢🟢 Very Positive | Best setup - cheap + gaining momentum + agencies bullish |
    | **Tactical Buy** | 🟢 Cheap | 🟢 Positive | Any | 🟡 Neutral/🟢 Positive | Good value + improving trend |
    | **Watch/Hold** | 🟢 Cheap | 🟡 Neutral | 🟡 Steady | 🟡 Mixed | Value present but no catalyst yet |
    | **Avoid** | 🟢 Cheap | 🔴 Negative | 🔴 Decelerating | 🔴 Negative | Value trap - deteriorating fundamentals |
    | **Sell/Trim** | 🔴 Rich | 🔴 Negative | 🔴 Decelerating | 🔴🔴 Very Negative | Expensive + worsening - worst combination |
    """)

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
                                            'carry_bps', 'vol_bps', 'carry_to_vol', 'rating_bucket',
                                            'ctv_zscore', 'ctv_value_signal',
                                            'sp_rating', 'moodys_rating', 'fit_rating', 'avg_rating',
                                            'z_spread', 'current_yield']].copy()
            
            display_ctv.columns = ['Country', 'Code', 'Region', 'Class', 'Carry (bps)', 'Vol (bps)', 'Carry-to-Vol',
                                   'Peer Group', 'C/V Z-Score', 'Risk-Adj Signal',
                                   'S&P', "Moody's", 'Fitch', 'Avg Rating',
                                   'Z-Spread (bps)', 'Current Yield (%)']
            
            # Sort by C/V Z-Score (best risk-adjusted returns first)
            display_ctv = display_ctv.sort_values('C/V Z-Score', ascending=False)
            
            st.dataframe(
                display_ctv.style.format({
                    'Carry (bps)': '{:.0f}',
                    'Vol (bps)': '{:.0f}',
                    'Carry-to-Vol': '{:.3f}',
                    'C/V Z-Score': lambda x: f'{x:.2f}' if pd.notna(x) else 'N/A',
                    'Avg Rating': lambda x: f'{x:.2f}' if pd.notna(x) else 'N/A',
                    'Z-Spread (bps)': lambda x: f'{x:.1f}' if pd.notna(x) else 'N/A',
                    'Current Yield (%)': lambda x: f'{x:.3f}' if pd.notna(x) else 'N/A'
                }).background_gradient(subset=['C/V Z-Score'], cmap='RdYlGn', vmin=-2, vmax=2),
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
        
        ---
        
        **Risk-Adjusted Signal (C/V Z-Score vs Peers)** shows risk-adjusted return quality relative to similar-rated sovereigns:
        - **🟢 Excellent (z > 1.0)**: Carry-to-Vol >1 std dev HIGHER than peers - **superior risk-adjusted returns**
        - **🟢 Good (0.5 < z < 1.0)**: Better risk-adjusted returns than peers
        - **🟡 Average (-0.5 < z < 0.5)**: In-line with rating peers
        - **🔴 Below Avg (-1.0 < z < -0.5)**: Worse risk-adjusted returns than peers
        - **🔴 Poor (z < -1.0)**: Carry-to-Vol >1 std dev LOWER than peers - **inferior risk-adjusted returns**
        
        Countries are grouped by rating buckets (A, BBB, BB, B) and compared within their peer group.
        **Higher C/V = More carry per unit of volatility = Better risk-adjusted returns**
        
        This metric answers: "Am I getting adequately compensated for the risk I'm taking compared to similar-rated credits?"
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

# ============================================================================
# TAB 4: FUNDAMENTAL RISK (JPMaQS Macro Risk Scoring)
# ============================================================================
with tab4:
    st.markdown("### Fundamental Macro Risk Scoring")
    st.markdown("""
    **Based on JPMaQS macro-quantamental indicators**  
    Positive scores = Higher risk | Negative scores = Lower risk  
    Z-score scale: -3 (very low risk) to +3 (very high risk)
    """)
    
    # Load JPMaQS fundamental risk data
    @st.cache_data(ttl=300)
    def load_jpmaqs_data():
        """Load latest JPMaQS fundamental risk scores with credit class from sovereign score table"""
        conn = get_db_connection()
        try:
            # Build currency to country code mapping for SQL
            currency_to_country_sql = "CASE j.country_code\n"
            for currency, country in CURRENCY_TO_COUNTRY.items():
                currency_to_country_sql += f"                WHEN '{currency}' THEN '{country}'\n"
            currency_to_country_sql += "                ELSE j.country_code\n            END"
            
            query = f"""
            WITH latest_jpmaqs AS (
                SELECT MAX(date) as max_date 
                FROM securitized_research.emd_jpmaqs_fundamental_scoring
            ),
            latest_sovereign AS (
                SELECT MAX(date) as max_date
                FROM securitized_research.emd_sovereign_score
            )
            SELECT 
                j.country_code,
                j.country_name,
                j.date,
                j.govt_finance_score,
                j.external_balance_score,
                j.intl_investment_score,
                j.foreign_debt_score,
                j.governance_score,
                j.growth_risk_score,
                j.inflation_risk_score,
                j.composite_macro_risk,
                j.composite_4factor_risk,
                s.class,
                s.avg_rating
            FROM securitized_research.emd_jpmaqs_fundamental_scoring j
            LEFT JOIN securitized_research.emd_sovereign_score s
                ON {currency_to_country_sql} = s.country_code
                AND s.date = (SELECT max_date FROM latest_sovereign)
            WHERE j.date = (SELECT max_date FROM latest_jpmaqs)
            ORDER BY j.composite_macro_risk DESC
            """
            df = pd.read_sql(query, conn)
            df['date'] = pd.to_datetime(df['date'])
        finally:
            conn.close()
        return df
    
    try:
        df_jpmaqs = load_jpmaqs_data()
        
        if len(df_jpmaqs) == 0:
            st.warning("No JPMaQS fundamental risk data available")
        else:
            # Add region mapping
            df_jpmaqs['region'] = df_jpmaqs['country_code'].map(REGION_MAPPING)
            
            # Apply filters from sidebar
            df_jpmaqs_filtered = df_jpmaqs.copy()
            
            # Filter by region
            if len(regions) > 0 and len(regions) < 3:  # If not all regions selected
                df_jpmaqs_filtered = df_jpmaqs_filtered[df_jpmaqs_filtered['region'].isin(regions)]
            
            # Filter by credit quality (IG/HY) - only if class data is available
            if len(credit_quality) > 0 and len(credit_quality) < 2:  # If not both IG and HY selected
                # Only filter rows where class is not null
                has_class = df_jpmaqs_filtered['class'].notna()
                if has_class.any():
                    # Keep rows that either match the class filter OR have no class data
                    df_jpmaqs_filtered = df_jpmaqs_filtered[
                        (df_jpmaqs_filtered['class'].isin(credit_quality)) | 
                        (~has_class)
                    ]
            
            # Check if any data remains after filtering
            if len(df_jpmaqs_filtered) == 0:
                st.warning("⚠️ No countries match the selected filters. Please adjust the region or credit quality filters in the sidebar.")
                st.stop()
            
            # Count how many countries have class data
            countries_with_class = df_jpmaqs_filtered['class'].notna().sum()
            
            data_date = df_jpmaqs_filtered['date'].iloc[0]
            info_msg = f"📅 **Data as of:** {data_date.strftime('%Y-%m-%d')} | **Countries:** {len(df_jpmaqs_filtered)}"
            if len(df_jpmaqs_filtered) < len(df_jpmaqs):
                info_msg += f" (filtered from {len(df_jpmaqs)} total)"
            if countries_with_class < len(df_jpmaqs_filtered):
                info_msg += f" | ⚠️ {len(df_jpmaqs_filtered) - countries_with_class} countries missing credit class data"
            st.info(info_msg)
            
            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                avg_composite = df_jpmaqs_filtered['composite_macro_risk'].mean()
                st.metric("Avg Composite Risk", f"{avg_composite:+.2f}", 
                         help="Equal-weighted 7-factor composite")
            with col2:
                safest = df_jpmaqs_filtered.nsmallest(1, 'composite_macro_risk').iloc[0]
                # Determine color based on score: negative = green (low risk), positive = orange/red (high risk)
                score = safest['composite_macro_risk']
                if score < -0.5:
                    color_emoji = "🟢"
                elif score < 0.5:
                    color_emoji = "🟡"
                else:
                    color_emoji = "🟠"
                st.metric("Lowest Risk", 
                         f"{color_emoji} {safest['country_name']}", 
                         f"{score:+.2f}",
                         delta_color="off")
            with col3:
                riskiest = df_jpmaqs_filtered.nlargest(1, 'composite_macro_risk').iloc[0]
                # Determine color based on score: positive = red/orange (high risk)
                score = riskiest['composite_macro_risk']
                if score > 1.5:
                    color_emoji = "🔴"
                elif score > 0.5:
                    color_emoji = "🟠"
                else:
                    color_emoji = "🟡"
                st.metric("Highest Risk", 
                         f"{color_emoji} {riskiest['country_name']}", 
                         f"{score:+.2f}",
                         delta_color="off")
            with col4:
                if 'composite_4factor_risk' in df_jpmaqs_filtered.columns:
                    avg_4f = df_jpmaqs_filtered['composite_4factor_risk'].mean()
                    st.metric("Avg 4-Factor Risk", f"{avg_4f:+.2f}",
                             help="Structural factors only (Govt Finance + Ext Balance + Intl Invest + Governance)")
            
            st.markdown("---")
            
            # Filter controls
            col_filter1, col_filter2 = st.columns(2)
            with col_filter1:
                view_mode = st.radio(
                    "View Mode",
                    ["All Factors", "Composite Scores", "Factor Decomposition"],
                    horizontal=True
                )
            with col_filter2:
                sort_by = st.selectbox(
                    "Sort Countries By",
                    ["Composite Risk (High→Low)", "Composite Risk (Low→High)", 
                     "Country Name", "4-Factor Risk"],
                    index=0
                )
            
            # Apply sorting
            if sort_by == "Composite Risk (High→Low)":
                df_display = df_jpmaqs_filtered.sort_values('composite_macro_risk', ascending=False)
            elif sort_by == "Composite Risk (Low→High)":
                df_display = df_jpmaqs_filtered.sort_values('composite_macro_risk', ascending=True)
            elif sort_by == "4-Factor Risk":
                df_display = df_jpmaqs_filtered.sort_values('composite_4factor_risk', ascending=False)
            else:
                df_display = df_jpmaqs_filtered.sort_values('country_name')
            
            # ===== VIEW 1: ALL FACTORS TABLE =====
            if view_mode == "All Factors":
                st.subheader("📋 Factor Scores by Country")
                
                # Format display table
                display_cols = ['country_name', 'region', 'govt_finance_score', 'external_balance_score',
                               'intl_investment_score', 'foreign_debt_score', 'governance_score',
                               'growth_risk_score', 'inflation_risk_score', 'composite_macro_risk']
                
                if 'composite_4factor_risk' in df_display.columns:
                    display_cols.append('composite_4factor_risk')
                
                display_df = df_display[display_cols].copy()
                display_df.columns = ['Country', 'Region', 'Govt Finance', 'Ext Balance', 
                                     'Intl Invest', 'Foreign Debt', 'Governance', 
                                     'Growth', 'Inflation', '7F Composite', '4F Composite'][:len(display_cols)]
                
                # Apply color formatting
                def color_risk_score(val):
                    """Color cells based on risk level"""
                    if pd.isna(val):
                        return 'background-color: #f0f0f0'
                    elif val > 1.5:
                        return 'background-color: #ffcccc; color: #990000; font-weight: bold'
                    elif val > 0.5:
                        return 'background-color: #ffe6cc; color: #cc6600'
                    elif val > -0.5:
                        return 'background-color: #ffffcc; color: #666600'
                    elif val > -1.5:
                        return 'background-color: #e6ffcc; color: #336600'
                    else:
                        return 'background-color: #ccffcc; color: #006600; font-weight: bold'
                
                # Apply styling
                score_cols = [c for c in display_df.columns if c not in ['Country', 'Region']]
                styled_df = display_df.style.map(color_risk_score, subset=score_cols)\
                                           .format({col: '{:+.2f}' for col in score_cols}, na_rep='N/A')
                
                st.dataframe(styled_df, use_container_width=True, height=600)
                
                st.markdown("""
                **Risk Levels:**  
                🟢 Very Low (<-1.5) | 🟢 Low (-1.5 to -0.5) | 🟡 Average (-0.5 to +0.5) | 🟠 Elevated (+0.5 to +1.5) | 🔴 High (+1.5 to +2.5) | 🔴 Very High (>+2.5)
                """)
                
                # Methodology explanation
                with st.expander("📖 **Methodology & Factor Definitions**", expanded=False):
                    st.markdown("""
                    ### 🔬 **Statistical Methodology**
                    
                    **Z-Score Normalization:**
                    - **Sequential (expanding window)**: No look-ahead bias - only uses historical data available at each point
                    - **Minimum observations**: 783 days (~3 years) required for stable z-scores
                    - **Panel-weighted**: Cross-country standardization ensures comparability
                    - **Winsorized at ±3σ**: Extreme outliers capped to prevent distortion
                    
                    **Sign Alignment Convention:**
                    - ✅ **Positive score = HIGHER risk** (for ALL factors)
                    - ✅ **Negative score = LOWER risk** (for ALL factors)
                    - This is achieved by negating indicators where "higher value = lower risk"
                    
                    **What does "negated" mean?**
                    
                    Some economic indicators naturally work backwards - higher values actually mean *lower* risk:
                    - ✅ **Higher government surplus** = Lower fiscal risk (but raw value is positive)
                    - ✅ **Higher current account surplus** = Lower external risk (but raw value is positive)
                    - ✅ **Better governance** = Lower governance risk (but raw score is higher)
                    - ✅ **Higher GDP growth** = Lower growth risk (but growth rate is positive)
                    
                    To maintain the **"positive = higher risk"** convention across ALL factors, we **multiply the z-score by -1** for these indicators. This sign flip ensures consistency:
                    
                    - **Original**: Country with +2.0 z-score for growth = Faster growth (good) → Should indicate *lower* risk
                    - **After negation**: +2.0 × (-1) = **-2.0** → Now correctly shows lower risk ✅
                    
                    **Examples in practice:**
                    - Brazil has strong growth → Growth z-score = -0.81 (negative = good, lower risk)
                    - Brazil has fiscal deficit → Govt finance z-score = +1.62 (positive = bad, higher risk)
                    
                    Both scores now align: **Positive always means higher risk, negative always means lower risk.**
                    
                    ---
                    
                    ### 📊 **Individual Factor Definitions**
                    
                    *Note: Indicators marked "negated" have their signs flipped so positive = higher risk*
                    
                    #### 1️⃣ **Government Finance Risk**
                    - **What it measures**: Fiscal sustainability (balance + debt levels)
                    - **Indicators**: 
                      - Government balance/GDP (current & next year) - *negated* (surplus is positive → flip to show lower risk)
                      - Government debt/GDP (higher debt = higher risk, no negation needed)
                    - **Weighting**: Equal weight (1/3 each)
                    - **Sign logic**: After negation, higher deficit or debt = higher risk
                    - **Example**: Brazil +1.62 = Large fiscal deficit, high debt
                    
                    #### 2️⃣ **External Balance Risk**
                    - **What it measures**: Foreign exchange sustainability
                    - **Indicators**: 
                      - Current account balance/GDP (12M MA) - *negated* (surplus is positive → flip to show lower risk)
                      - Trade balance/GDP (12M MA) - *negated* (surplus is positive → flip to show lower risk)
                    - **Weighting**: Equal weight (0.5 each)
                    - **Sign logic**: After negation, higher deficit = higher risk
                    - **Example**: Egypt often has large current account deficits
                    
                    #### 3️⃣ **International Investment Risk**
                    - **What it measures**: Net foreign asset position & vulnerability
                    - **Indicators**: 
                      - Net investment position/GDP changes (2Y & 5Y MA) - *negated* (improving position → flip to show lower risk)
                      - Foreign liabilities/GDP changes (2Y & 5Y MA) (rising liabilities = higher risk, no negation)
                    - **Weighting**: Equal weight (0.25 each)
                    - **Sign logic**: After negation, worsening position or rising liabilities = higher risk
                    
                    #### 4️⃣ **Foreign Debt Risk**
                    - **What it measures**: FX-denominated debt burden
                    - **Indicators**: 
                      - All FX debt/GDP (higher debt = higher risk, no negation)
                      - Government FX debt/GDP (higher debt = higher risk, no negation)
                    - **Weighting**: Equal weight (0.5 each)
                    - **Sign logic**: Higher FX debt = higher risk (currency mismatch vulnerability)
                    
                    #### 5️⃣ **Governance Risk**
                    - **What it measures**: Institutional quality & political stability
                    - **Indicators**: 
                      - Voice & accountability - *negated* (better governance = higher raw score → flip to show lower risk)
                      - Political stability - *negated* (more stable = higher raw score → flip to show lower risk)
                      - Corruption control - *negated* (less corrupt = higher raw score → flip to show lower risk)
                    - **Weighting**: Equal weight (1/3 each)
                    - **Sign logic**: After negation, weaker governance = higher risk
                    - **Example**: Qatar -1.49 has strong governance (negative = good), Egypt +2.63 faces challenges (positive = bad)
                    
                    #### 6️⃣ **Growth Risk**
                    - **What it measures**: Medium-term GDP growth trends
                    - **Indicators**: 
                      - Real GDP growth QoQ annualized (20Q MA & current) - *negated* (faster growth → flip to show lower risk)
                    - **Weighting**: Equal weight (0.5 each)
                    - **Sign logic**: After negation, lower growth = higher risk (debt sustainability concern)
                    - **Example**: Brazil -0.81 = Strong recent growth (negative = good, lowers overall risk)
                    
                    #### 7️⃣ **Inflation Risk**
                    - **What it measures**: Price stability deviation from target
                    - **Indicators**: 
                      - Headline CPI YoY (transformed, not negated)
                      - Core CPI YoY (transformed, not negated)
                    - **Weighting**: Equal weight (0.5 each)
                    - **Sign logic**: Both HIGH and LOW inflation = higher risk (no negation - transformation handles directionality)
                    - **Non-linear transformation**: `sqrt(|inflation - 2%|)` captures deviation from 2% target
                    - **Example**: Turkey has persistently high inflation = elevated risk
                    
                    ---
                    
                    ### 🎯 **Composite Score Comparison**
                    
                    #### **7-Factor Composite (Equal-Weight)**
                    - **Purpose**: Comprehensive risk assessment & **timing signals**
                    - **Composition**: All 7 factors weighted equally (1/7 each)
                    - **Use case**: 
                      - Overall macro risk snapshot
                      - Directional trading signals (risk-on/risk-off)
                      - Identifying regime changes
                    - **Includes cyclical factors**: Growth, Inflation, Foreign Debt
                    - **Advantage**: Captures full risk picture including near-term dynamics
                    
                    #### **4-Factor Composite (Structural)**
                    - **Purpose**: Structural risk & **cross-country comparison**
                    - **Composition**: 
                      - Govt Finance (25%)
                      - External Balance (25%)
                      - Intl Investment (25%)
                      - Governance (25%)
                    - **Use case**: 
                      - Relative value analysis
                      - Country rankings for allocation
                      - Long-term sovereign credit quality
                    - **Excludes**: Growth, Inflation, Foreign Debt (more volatile/cyclical)
                    - **Advantage**: 
                      - **Higher Sharpe ratio** for predicting sovereign spreads
                      - More stable over time (less noise)
                      - Better discriminator for cross-country relative value
                      - Focuses on fundamental solvency metrics
                    
                    #### **Research Evidence (MacroSynergy)**
                    Based on backtests analyzing EM sovereign spread returns:
                    - 4-factor composite showed **stronger predictive power** for cross-sectional spread differences
                    - Cyclical factors (growth, inflation) add noise to relative value comparisons
                    - Structural factors better capture persistent credit quality differences
                    - **Recommendation**: Use 7F for market timing, 4F for country selection
                    
                    ---
                    
                    ### 💡 **Practical Interpretation**
                    
                    **Example: Brazil (as of latest data)**
                    - Govt Finance: +1.62 🔴 = Large fiscal challenges
                    - External Balance: +0.31 🟡 = Modest current account deficit
                    - Intl Investment: +0.44 🟡 = Manageable foreign position
                    - Foreign Debt: +0.23 🟡 = Moderate FX debt
                    - Governance: +0.71 🟠 = Institutional concerns
                    - Growth: -0.81 🟢 = Strong growth offsets risk
                    - Inflation: +0.78 🟠 = Above-target inflation
                    - **7F Composite: +1.09 🟠** = Elevated overall risk
                    - **4F Composite: +1.54 🔴** = High structural risk
                    
                    **Takeaway**: Brazil's growth momentum helps the 7F score, but structural fundamentals (4F) remain challenged by fiscal issues and governance.
                    
                    ---
                    
                    **Data Source**: [JPMaQS](https://macrosynergy.com/jpmaqs/) (JP Morgan Macrosynergy Quantamental System)  
                    **Update Frequency**: Daily (automated via Task Scheduler)  
                    **Historical Coverage**: 2020-01-01 to present (6-month lag for Dataquery tier)
                    """)
            
            
            # ===== VIEW 2: COMPOSITE SCORES =====
            elif view_mode == "Composite Scores":
                st.subheader("📊 Composite Risk Scores")
                
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    st.markdown("**7-Factor Equal-Weight Composite**")
                    st.markdown("*Govt Finance + Ext Balance + Intl Invest + Foreign Debt + Governance + Growth + Inflation*")
                    
                    # Create horizontal bar chart for 7-factor
                    fig_7f = go.Figure()
                    
                    df_plot = df_display.copy()
                    colors_7f = df_plot['composite_macro_risk'].apply(
                        lambda x: '#990000' if x > 1.5 else '#cc6600' if x > 0.5 else '#666600' if x > -0.5 else '#336600' if x > -1.5 else '#006600'
                    )
                    
                    fig_7f.add_trace(go.Bar(
                        y=df_plot['country_name'],
                        x=df_plot['composite_macro_risk'],
                        orientation='h',
                        marker=dict(color=colors_7f),
                        text=df_plot['composite_macro_risk'].apply(lambda x: f'{x:+.2f}'),
                        textposition='outside',
                        hovertemplate='<b>%{y}</b><br>Risk Score: %{x:+.2f}<extra></extra>'
                    ))
                    
                    fig_7f.update_layout(
                        xaxis_title="Risk Score",
                        yaxis_title="",
                        height=max(400, len(df_plot) * 20),
                        showlegend=False,
                        margin=dict(l=0, r=50, t=20, b=40)
                    )
                    
                    # Add vertical lines for risk zones
                    fig_7f.add_vline(x=0, line_dash="dash", line_color="gray", line_width=1)
                    fig_7f.add_vline(x=0.5, line_dash="dot", line_color="orange", line_width=1, opacity=0.5)
                    fig_7f.add_vline(x=-0.5, line_dash="dot", line_color="green", line_width=1, opacity=0.5)
                    
                    st.plotly_chart(fig_7f, use_container_width=True)
                
                with col_chart2:
                    if 'composite_4factor_risk' in df_display.columns:
                        st.markdown("**4-Factor Structural Composite**")
                        st.markdown("*Govt Finance + Ext Balance + Intl Invest + Governance*")
                        
                        # Create horizontal bar chart for 4-factor
                        fig_4f = go.Figure()
                        
                        df_plot_4f = df_display.dropna(subset=['composite_4factor_risk']).copy()
                        colors_4f = df_plot_4f['composite_4factor_risk'].apply(
                            lambda x: '#990000' if x > 1.5 else '#cc6600' if x > 0.5 else '#666600' if x > -0.5 else '#336600' if x > -1.5 else '#006600'
                        )
                        
                        fig_4f.add_trace(go.Bar(
                            y=df_plot_4f['country_name'],
                            x=df_plot_4f['composite_4factor_risk'],
                            orientation='h',
                            marker=dict(color=colors_4f),
                            text=df_plot_4f['composite_4factor_risk'].apply(lambda x: f'{x:+.2f}'),
                            textposition='outside',
                            hovertemplate='<b>%{y}</b><br>Risk Score: %{x:+.2f}<extra></extra>'
                        ))
                        
                        fig_4f.update_layout(
                            xaxis_title="Risk Score",
                            yaxis_title="",
                            height=max(400, len(df_plot_4f) * 20),
                            showlegend=False,
                            margin=dict(l=0, r=50, t=20, b=40)
                        )
                        
                        # Add vertical lines
                        fig_4f.add_vline(x=0, line_dash="dash", line_color="gray", line_width=1)
                        fig_4f.add_vline(x=0.5, line_dash="dot", line_color="orange", line_width=1, opacity=0.5)
                        fig_4f.add_vline(x=-0.5, line_dash="dot", line_color="green", line_width=1, opacity=0.5)
                        
                        st.plotly_chart(fig_4f, use_container_width=True)
            
            # ===== VIEW 3: FACTOR DECOMPOSITION =====
            elif view_mode == "Factor Decomposition":
                st.subheader("🔍 Individual Factor Breakdown")
                
                # Country selector for detailed view
                selected_countries_jpmaqs = st.multiselect(
                    "Select Countries for Comparison (max 10)",
                    options=df_display['country_name'].tolist(),
                    default=df_display['country_name'].head(5).tolist(),
                    max_selections=10
                )
                
                if len(selected_countries_jpmaqs) > 0:
                    df_selected = df_display[df_display['country_name'].isin(selected_countries_jpmaqs)]
                    
                    # Prepare data for stacked bar chart
                    factor_cols = ['govt_finance_score', 'external_balance_score', 'intl_investment_score',
                                  'foreign_debt_score', 'governance_score', 'growth_risk_score', 'inflation_risk_score']
                    factor_names = ['Govt Finance', 'Ext Balance', 'Intl Invest', 'Foreign Debt', 
                                   'Governance', 'Growth', 'Inflation']
                    
                    # Create grouped bar chart
                    fig_decomp = go.Figure()
                    
                    colors = ['#e74c3c', '#e67e22', '#f39c12', '#3498db', '#9b59b6', '#1abc9c', '#34495e']
                    
                    for i, (col, name) in enumerate(zip(factor_cols, factor_names)):
                        fig_decomp.add_trace(go.Bar(
                            name=name,
                            x=df_selected['country_name'],
                            y=df_selected[col],
                            marker_color=colors[i],
                            hovertemplate=f'<b>{name}</b><br>%{{y:+.2f}}<extra></extra>'
                        ))
                    
                    fig_decomp.update_layout(
                        barmode='group',
                        title="Factor Risk Decomposition by Country",
                        xaxis_title="",
                        yaxis_title="Risk Score (Z-Score)",
                        height=500,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        ),
                        hovermode='closest'
                    )
                    
                    # Add zero line
                    fig_decomp.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
                    
                    st.plotly_chart(fig_decomp, use_container_width=True)
                    
                    # Show data table for selected countries
                    st.markdown("#### 📋 Detailed Factor Scores")
                    detail_df = df_selected[['country_name', 'region'] + factor_cols + ['composite_macro_risk']].copy()
                    detail_df.columns = ['Country', 'Region'] + factor_names + ['7F Composite']
                    
                    # Format and style
                    def color_risk(val):
                        if pd.isna(val):
                            return ''
                        elif val > 1.0:
                            return 'background-color: #ffcccc'
                        elif val > 0:
                            return 'background-color: #ffe6cc'
                        elif val > -1.0:
                            return 'background-color: #e6ffcc'
                        else:
                            return 'background-color: #ccffcc'
                    
                    styled_detail = detail_df.style.map(color_risk, subset=factor_names + ['7F Composite'])\
                                                  .format({col: '{:+.2f}' for col in factor_names + ['7F Composite']}, na_rep='N/A')
                    
                    st.dataframe(styled_detail, use_container_width=True)
                    
                    st.markdown("""
                    **Factor Interpretation:**
                    - **Govt Finance**: Fiscal balance and debt levels (surplus = lower risk, deficit = higher risk)
                    - **Ext Balance**: Current account and trade balance (surplus = lower risk)
                    - **Intl Investment**: Net investment position and foreign liabilities
                    - **Foreign Debt**: FX-denominated debt burden
                    - **Governance**: Political stability, accountability, corruption control
                    - **Growth**: Medium-term GDP growth trends (higher growth = lower risk)
                    - **Inflation**: Deviation from 2% target (both high and low = higher risk)
                    """)
                else:
                    st.info("Please select at least one country to view factor decomposition")
            
            st.markdown("---")
            st.markdown("""
            **Data Source:** JPMaQS (Macro-Quantamental Signals) via MacroSynergy  
            **Methodology:** Sequential z-score normalization, panel-weighted, winsorized at ±3σ  
            **Interpretation:** Positive scores indicate higher fundamental risk; negative scores indicate lower risk
            """)
    
    except Exception as e:
        st.error(f"Error loading JPMaQS data: {e}")
        st.info("Make sure the fundamental risk scoring data has been uploaded to the database.")
