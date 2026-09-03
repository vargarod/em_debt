"""
EM Economic Data Tab
Displays economic metrics and CPI time series data from PostgreSQL
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import psycopg2
import os


CATEGORY_ORDER = [
    "Summary Data",
    "Economic Activity",
    "Prices, Money & Credit",
    "Balance of Payments, US$ bn",
    "Public Finances, % of GDP",
    "Foreign Assets & Liabilities, US$ bn",
    "Quarterly Economic Indicators",
]


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


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_countries():
    """Get list of all available countries"""
    conn = get_db_connection()
    try:
        query = """
        SELECT DISTINCT country_code, country_name
        FROM securitized_research.em_countries
        ORDER BY country_name
        """
        df = pd.read_sql(query, conn)
        return df
    finally:
        conn.close()


@st.cache_data(ttl=3600)
def get_economic_metrics(country_code):
    """Get all economic metrics for a country across all years, grouped by category"""
    conn = get_db_connection()
    try:
        query = """
        SELECT 
            m.year,
            m.is_forecast,
            m.metric_name,
            m.metric_value,
            COALESCE(d.metric_category, 'General') as category,
            CASE WHEN m.is_forecast THEN 'Forecast' ELSE 'Actual' END as data_type
        FROM securitized_research.em_economic_metrics m
        LEFT JOIN securitized_research.em_metric_definitions d ON m.metric_name = d.metric_name
        WHERE m.country_code = %s
        ORDER BY d.metric_category, m.metric_name, m.year
        """
        df = pd.read_sql(query, conn, params=(country_code,))
        return df
    finally:
        conn.close()


@st.cache_data(ttl=3600)
def get_cpi_time_series(country_code):
    """Get CPI time series for a country"""
    conn = get_db_connection()
    try:
        query = """
        SELECT 
            date,
            EXTRACT(YEAR FROM date)::INTEGER as year,
            EXTRACT(MONTH FROM date)::INTEGER as month,
            cpi_yoy,
            core_cpi_yoy
        FROM securitized_research.em_cpi_time_series
        WHERE country_code = %s
        ORDER BY date
        """
        df = pd.read_sql(query, conn, params=(country_code,))
        return df
    finally:
        conn.close()


@st.cache_data(ttl=3600)
def get_latest_year_metrics(country_codes):
    """Get latest year metrics for multiple countries"""
    conn = get_db_connection()
    try:
        placeholders = ','.join(['%s'] * len(country_codes))
        query = f"""
        SELECT 
            m.country_code,
            m.country_name,
            m.metric_name,
            m.metric_value,
            m.year,
            COALESCE(d.metric_category, 'General') as category
        FROM securitized_research.em_economic_metrics m
        LEFT JOIN securitized_research.em_metric_definitions d
            ON m.metric_name = d.metric_name
        WHERE m.country_code IN ({placeholders})
        AND m.year = (
            SELECT MAX(year)
            FROM securitized_research.em_economic_metrics 
            WHERE is_forecast = FALSE
        )
        ORDER BY d.metric_category, m.metric_name, m.country_code
        """
        df = pd.read_sql(query, conn, params=country_codes)
        return df
    finally:
        conn.close()


@st.cache_data(ttl=3600)
def get_cpi_latest_month(country_codes):
    """Get CPI data for the latest completed month across selected countries."""
    conn = get_db_connection()
    try:
        placeholders = ','.join(['%s'] * len(country_codes))
        query = f"""
        SELECT 
            country_code,
            country_name,
            date,
            cpi_yoy,
            core_cpi_yoy
        FROM securitized_research.em_cpi_time_series
        WHERE country_code IN ({placeholders})
        AND date = (
            SELECT MAX(date)
            FROM securitized_research.em_cpi_time_series
            WHERE date < date_trunc('month', CURRENT_DATE)
        )
        ORDER BY country_name
        """
        df = pd.read_sql(query, conn, params=country_codes)
        return df
    finally:
        conn.close()


def create_metrics_pivot(df, year_col='year'):
    """Create pivot table for metrics display"""
    pivot = df.pivot_table(
        index='metric_name',
        columns=year_col,
        values='metric_value',
        aggfunc='first'
    )
    return pivot


def display_metrics_by_category(df):
    """Display metrics organized by category with section headers"""
    if df.empty:
        st.warning("No economic metrics available for this country")
        return
    
    categories = ordered_categories(df)
    
    for category in categories:
        category_df = df[df['category'] == category]
        
        # Section header
        st.subheader(f"📋 {category}")
        
        # Create pivot for this category
        metrics_pivot = category_df.pivot_table(
            index='metric_name',
            columns='year',
            values='metric_value',
            aggfunc='first'
        )
        
        # Remove category column from display
        metrics_pivot = metrics_pivot[[col for col in metrics_pivot.columns]]
        
        # Style the dataframe
        def highlight_forecast(col):
            """Highlight forecast years"""
            if col.name and col.name >= 2026:
                return ['background-color: #FFF3CD'] * len(col)
            return [''] * len(col)
        
        styled_df = metrics_pivot.style.apply(highlight_forecast)
        styled_df = styled_df.format("{:,.2f}", na_rep='-')
        
        st.dataframe(styled_df, use_container_width=True)
        st.markdown("")  # Add spacing between sections


def ordered_categories(df):
    """Return known categories in workbook order, followed by any new ones."""
    present = set(df['category'].dropna())
    quarterly_category = "Quarterly Economic Indicators"
    known = [
        category for category in CATEGORY_ORDER
        if category != quarterly_category and category in present
    ]
    additional = sorted(present.difference(CATEGORY_ORDER))
    quarterly = [quarterly_category] if quarterly_category in present else []
    return known + additional + quarterly


def display_comparison_metrics_by_category(df, country_codes):
    """Display latest-year country comparison tables grouped by category."""
    if df.empty:
        st.warning("No economic metrics available for selected countries")
        return

    for category in ordered_categories(df):
        category_df = df[df['category'] == category]
        comparison_pivot = category_df.pivot_table(
            index='metric_name',
            columns='country_code',
            values='metric_value',
            aggfunc='first'
        )
        available_cols = [code for code in country_codes if code in comparison_pivot.columns]
        st.subheader(f"📋 {category}")
        st.dataframe(
            comparison_pivot[available_cols].style.format("{:,.2f}", na_rep='-'),
            use_container_width=True
        )


def render_em_economic_tab():
    """Render the EM Economic Data tab"""
    
    st.markdown("""
    ### Economic Metrics & Inflation Analysis
    Explore comprehensive EM economic indicators and CPI time series data
    """)
    
    # Load countries
    countries_df = get_countries()
    countries_list = countries_df.set_index('country_code')['country_name'].to_dict()
    country_codes = sorted(countries_list.keys())
    
    # Country selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_countries = st.multiselect(
            "Select Countries",
            options=country_codes,
            format_func=lambda x: f"{x} - {countries_list[x]}",
            default=[country_codes[0]] if country_codes else []
        )
    
    with col2:
        view_type = st.radio(
            "View",
            ["Metrics", "CPI Series", "Comparison"],
            horizontal=True
        )
    
    if not selected_countries:
        st.info("Please select at least one country")
        return
    
    # =========================================================================
    # VIEW 1: ECONOMIC METRICS TABLE
    # =========================================================================
    if view_type == "Metrics":
        st.subheader("📊 Economic Metrics by Year")
        
        if len(selected_countries) == 1:
            # Single country: show all years and metrics organized by category
            country_code = selected_countries[0]
            country_name = countries_list[country_code]
            
            st.markdown(f"**{country_code} - {country_name}**")
            
            metrics_df = get_economic_metrics(country_code)

            if not metrics_df.empty:
                display_metrics_by_category(metrics_df)
                st.caption("⚠️ Yellow columns indicate forecast years (2026F and beyond)")
            else:
                st.warning("No economic metrics available for this country")
        
        else:
            st.markdown("**Latest Year Data - Side-by-Side Comparison**")
            metrics_df = get_latest_year_metrics(selected_countries)
            
            if not metrics_df.empty:
                display_comparison_metrics_by_category(metrics_df, selected_countries)
                
                # Show year info
                year_info = metrics_df[['year']].drop_duplicates()
                if not year_info.empty:
                    st.caption(f"Data year: {int(year_info['year'].iloc[0])}")
            else:
                st.warning("No economic metrics available for selected countries")
    
    # =========================================================================
    # VIEW 2: CPI TIME SERIES
    # =========================================================================
    elif view_type == "CPI Series":
        st.subheader("📈 CPI Inflation Time Series (Year-over-Year)")
        
        # Display latest CPI values
        latest_cpi_df = get_cpi_latest_month(selected_countries)
        
        if not latest_cpi_df.empty:
            st.markdown("**Latest CPI Values**")
            
            cpi_display = latest_cpi_df[['country_code', 'country_name', 'date', 'cpi_yoy', 'core_cpi_yoy']].copy()
            cpi_display.columns = ['Code', 'Country', 'Latest Date', 'CPI YoY %', 'Core CPI YoY %']
            cpi_display = cpi_display.sort_values('Country')
            
            st.dataframe(
                cpi_display.style.format({
                    'CPI YoY %': '{:.2f}',
                    'Core CPI YoY %': '{:.2f}'
                }),
                use_container_width=True
            )
        
        # Plot CPI time series
        st.markdown("**CPI Trend**")
        
        fig = go.Figure()
        
        for country_code in selected_countries:
            cpi_df = get_cpi_time_series(country_code)
            country_name = countries_list[country_code]
            
            if not cpi_df.empty:
                fig.add_trace(go.Scatter(
                    x=cpi_df['date'],
                    y=cpi_df['cpi_yoy'],
                    name=f"{country_code} - CPI",
                    mode='lines',
                    hovertemplate='%{x|%Y-%m-%d}<br>CPI YoY: %{y:.2f}%<extra></extra>'
                ))
        
        fig.update_layout(
            title="CPI Year-over-Year (%)",
            xaxis_title="Date",
            yaxis_title="CPI YoY (%)",
            hovermode='x unified',
            height=500,
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # =========================================================================
    # VIEW 3: COMPARISON DASHBOARD
    # =========================================================================
    elif view_type == "Comparison":
        st.subheader("📋 Economic Comparison Dashboard")
        
        if len(selected_countries) == 1:
            # Single country - show comprehensive view
            country_code = selected_countries[0]
            country_name = countries_list[country_code]
            
            st.markdown(f"**{country_code} - {country_name}**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Economic Metrics")
                metrics_df = get_economic_metrics(country_code)
                
                if not metrics_df.empty:
                    display_metrics_by_category(metrics_df)
            
            with col2:
                st.markdown("#### CPI Inflation Trend")
                cpi_df = get_cpi_time_series(country_code)
                
                if not cpi_df.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=cpi_df['date'],
                        y=cpi_df['cpi_yoy'],
                        name='CPI YoY',
                        mode='lines',
                        line=dict(color='#1f77b4', width=2),
                        fill='tozeroy'
                    ))
                    fig.update_layout(
                        title="CPI Year-over-Year (%)",
                        xaxis_title="Date",
                        yaxis_title="CPI YoY (%)",
                        height=400,
                        template='plotly_white',
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        else:
            # Multiple countries - show side-by-side metrics and latest CPI
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Economic Metrics (Latest Actual Year)")
                metrics_df = get_latest_year_metrics(selected_countries)
                
                if not metrics_df.empty:
                    display_comparison_metrics_by_category(metrics_df, selected_countries)
            
            with col2:
                st.markdown("#### Latest CPI Values")
                latest_cpi_df = get_cpi_latest_month(selected_countries)
                
                if not latest_cpi_df.empty:
                    cpi_display = latest_cpi_df[['country_code', 'cpi_yoy', 'core_cpi_yoy']].copy()
                    cpi_display.columns = ['Country', 'CPI YoY %', 'Core CPI YoY %']
                    cpi_display = cpi_display.sort_values('Country')
                    
                    st.dataframe(
                        cpi_display.style.format({
                            'CPI YoY %': '{:.2f}',
                            'Core CPI YoY %': '{:.2f}'
                        }),
                        use_container_width=True
                    )
            
            # CPI comparison chart
            st.markdown("#### CPI Trend Comparison")
            
            fig = go.Figure()
            
            for country_code in selected_countries:
                cpi_df = get_cpi_time_series(country_code)
                
                if not cpi_df.empty:
                    fig.add_trace(go.Scatter(
                        x=cpi_df['date'],
                        y=cpi_df['cpi_yoy'],
                        name=country_code,
                        mode='lines',
                        hovertemplate='%{x|%Y-%m-%d}<br>CPI YoY: %{y:.2f}%<extra></extra>'
                    ))
            
            fig.update_layout(
                title="CPI Year-over-Year (%) - Comparison",
                xaxis_title="Date",
                yaxis_title="CPI YoY (%)",
                hovermode='x unified',
                height=500,
                template='plotly_white'
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Add footer credit
    st.markdown("---")
    st.markdown("""
    <small style="color: #888; font-size: 0.85em;">
    📊 **Data Source:** Citi Economic Team  
    Economic metrics compiled from Citi's comprehensive EM economic database, providing detailed annual forecasts and historical data.
    </small>
    """, unsafe_allow_html=True)
