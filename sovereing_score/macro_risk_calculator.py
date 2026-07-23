"""
Macro Risk Calculator for EM Sovereign Debt
============================================

Calculates fundamental risk scores for emerging market sovereigns using
macro-quantamental indicators from JPMaQS. 

Based on MacroSynergy's research methodology:
https://macrosynergy.com/research/estimating-emerging-markets-sovereign-risk-premia/

Seven Risk Factor Categories:
1. Government Finance Risk - fiscal balance, debt/GDP
2. External Balance Risk - current account, trade balance
3. International Investment Risk - net investment position, liabilities
4. Foreign Debt Risk - FX-denominated debt levels
5. Governance Risk - political stability, corruption, accountability
6. Growth Risk - medium-term GDP growth trends
7. Inflation Risk - CPI deviation from target (non-linear)

Author: Securitized Research Team
Date: 2026-07-23
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from macrosynergy.download import JPMaQSDownload
import macrosynergy.panel as msp


class MacroRiskCalculator:
    """
    Calculate fundamental sovereign risk scores for EM countries
    """
    
    # EM Foreign Currency Sovereign Debt Countries (24 from EMBI)
    COUNTRIES = {
        'LatAM': ['BRL', 'CLP', 'COP', 'DOP', 'MXN', 'PEN', 'UYU'],
        'EMEA': ['HUF', 'PLN', 'ROM', 'RUB', 'RSD', 'TRY', 
                 'AED', 'EGP', 'NGN', 'OMR', 'QAR', 'ZAR', 'SAR'],
        'Asia': ['CNY', 'IDR', 'INR', 'PHP']
    }
    
    # Macro indicators by category (from JPMaQS)
    # Format: indicator_name: [negate_flag, weight]
    # negate_flag: True if higher value = lower risk (needs sign flip)
    INDICATORS = {
        'govt_finance': {
            'GGOBGDPRATIO_NSA': [True, 1/3],      # Govt balance (higher surplus = lower risk)
            'GGOBGDPRATIONY_NSA': [True, 1/3],    # Govt balance next year
            'GGDGDPRATIO_NSA': [False, 1/3],      # Govt debt (higher debt = higher risk)
        },
        'external_balance': {
            'CABGDPRATIO_NSA_12MMA': [True, 0.5],  # Current account (higher surplus = lower risk)
            'MTBGDPRATIO_NSA_12MMA': [True, 0.5],  # Trade balance (higher surplus = lower risk)
        },
        'intl_investment': {
            'NIIPGDP_NSA_D1Mv2YMA': [True, 0.25],   # Net position improving = lower risk
            'NIIPGDP_NSA_D1Mv5YMA': [True, 0.25],   # Net position improving = lower risk
            'IIPLIABGDP_NSA_D1Mv2YMA': [False, 0.25], # Rising liabilities = higher risk
            'IIPLIABGDP_NSA_D1Mv5YMA': [False, 0.25], # Rising liabilities = higher risk
        },
        'foreign_debt': {
            'ALLIFCDSGDP_NSA': [False, 0.5],  # Higher FX debt = higher risk
            'GGIFCDSGDP_NSA': [False, 0.5],   # Higher govt FX debt = higher risk
        },
        'governance': {
            'ACCOUNTABILITY_NSA': [True, 1/3],  # Better accountability = lower risk
            'POLSTAB_NSA': [True, 1/3],         # Better stability = lower risk
            'CORRCONTROL_NSA': [True, 1/3],     # Better corruption control = lower risk
        },
        'growth': {
            'RGDP_SA_P1Q1QL4_20QMA': [True, 0.5],  # Higher growth = lower risk
            'RGDP_SA_P1Q1QL4': [True, 0.5],        # Higher growth = lower risk
        },
        'inflation': {
            'CPIH_SA_P1M1ML12': [False, 0.5],  # Already transformed with sqrt
            'CPIC_SA_P1M1ML12': [False, 0.5],  # Already transformed with sqrt
        }
    }
    
    # Country code to full name mapping
    COUNTRY_NAMES = {
        'BRL': 'Brazil', 'CLP': 'Chile', 'COP': 'Colombia', 'DOP': 'Dominican Rep',
        'MXN': 'Mexico', 'PEN': 'Peru', 'UYU': 'Uruguay',
        'HUF': 'Hungary', 'PLN': 'Poland', 'ROM': 'Romania', 'RUB': 'Russia',
        'RSD': 'Serbia', 'TRY': 'Turkey',
        'AED': 'UAE', 'EGP': 'Egypt', 'NGN': 'Nigeria', 'OMR': 'Oman',
        'QAR': 'Qatar', 'ZAR': 'South Africa', 'SAR': 'Saudi Arabia',
        'CNY': 'China', 'IDR': 'Indonesia', 'INR': 'India', 'PHP': 'Philippines'
    }
    
    def __init__(self, credentials_path: Optional[str] = None, 
                 client_id: Optional[str] = None, 
                 client_secret: Optional[str] = None):
        """
        Initialize calculator with JPMaQS credentials
        
        Args:
            credentials_path: Path to JSON file with credentials
            client_id: Direct client ID (alternative to credentials_path)
            client_secret: Direct client secret (alternative to credentials_path)
        """
        if credentials_path:
            self.client_id, self.client_secret = self._load_credentials(credentials_path)
        elif client_id and client_secret:
            self.client_id = client_id
            self.client_secret = client_secret
        else:
            raise ValueError("Must provide either credentials_path or both client_id and client_secret")
        
        self.all_countries = [c for region in self.COUNTRIES.values() for c in region]
        self.raw_data = None
        self.processed_data = None
        
    def _load_credentials(self, path: str) -> Tuple[str, str]:
        """Load credentials from JSON file"""
        with open(path, 'r') as f:
            creds = json.load(f)
        return creds['client_id'], creds['client_secret']
    
    def download_data(self, start_date: str = "2000-01-01", 
                     countries: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Download macro indicators from JPMaQS
        
        Args:
            start_date: Start date for data download (YYYY-MM-DD)
            countries: List of country codes (default: all 24 EMBI countries)
            
        Returns:
            DataFrame with raw indicator data
        """
        if countries is None:
            countries = self.all_countries
        
        # Build ticker list - extract indicator names from dict
        all_indicators = [ind for cat in self.INDICATORS.values() for ind in cat.keys()]
        tickers = [f"{cid}_{xcat}" for cid in countries for xcat in all_indicators]
        
        print(f"Downloading data for {len(countries)} countries and {len(all_indicators)} indicators...")
        print(f"Total tickers: {len(tickers)}")
        
        with JPMaQSDownload(
            client_id=self.client_id,
            client_secret=self.client_secret,
            proxy={}
        ) as downloader:
            df = downloader.download(
                tickers=tickers,
                start_date=start_date,
                metrics=["value"],
                suppress_warning=True,
                show_progress=True,
                report_time_taken=True,
            )
        
        self.raw_data = df
        print(f"\n[OK] Downloaded {len(df):,} rows of data")
        print(f"  Date range: {df['real_date'].min()} to {df['real_date'].max()}")
        print(f"  Countries: {df['cid'].nunique()}")
        
        return df
    
    def calculate_inflation_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform inflation data using non-linear function
        Risk increases with deviation from 2% target (both high and low inflation)
        
        Formula: sqrt(|inflation - 2%|)
        """
        inflation_xcats = ['CPIH_SA_P1M1ML12', 'CPIC_SA_P1M1ML12']
        
        result_dfs = []
        for xcat in inflation_xcats:
            df_infl = df[df['xcat'] == xcat].copy()
            if len(df_infl) > 0:
                # Apply non-linear transformation: sqrt(|x - 2|)
                df_infl['value'] = np.power(np.abs(df_infl['value'] - 2), 0.5)
                df_infl['xcat'] = xcat.replace('_SA_P1M1ML12', '_IE')  # Inflation Effect
                result_dfs.append(df_infl)
        
        if result_dfs:
            return pd.concat(result_dfs, ignore_index=True)
        return pd.DataFrame()
    
    def calculate_zscores(self, df: pd.DataFrame, xcat: str,
                         sequential: bool = True,
                         min_obs: int = 261 * 3) -> pd.DataFrame:
        """
        Calculate sequential z-scores for an indicator
        
        Args:
            df: DataFrame with indicator data
            xcat: Cross-sectional category (indicator name)
            sequential: Use expanding window (avoids look-ahead bias)
            min_obs: Minimum observations required (3 years daily = 783)
            
        Returns:
            DataFrame with z-scores
        """
        # Only use countries that have data for this indicator
        df_xcat = df[df['xcat'] == xcat]
        available_cids = df_xcat['cid'].unique().tolist()
        
        if len(available_cids) == 0:
            return pd.DataFrame()
        
        return msp.make_zn_scores(
            df,
            xcat=xcat,
            cids=available_cids,  # Use only countries with data
            sequential=sequential,
            min_obs=min_obs,
            neutral="zero",
            pan_weight=1,  # Panel normalization
            thresh=3,      # Winsorize at 3 std devs
            postfix="_ZN",
            est_freq="m",  # Monthly estimation frequency
        )
    
    def calculate_factor_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate risk scores for each of the 7 factor categories
        Applies sign adjustment so positive ALWAYS means higher risk
        
        Returns:
            DataFrame with factor-level z-scores
        """
        print("\nCalculating factor risk scores...")
        
        all_scores = []
        
        # Process each factor category
        for factor_name, indicators_dict in self.INDICATORS.items():
            print(f"  Processing {factor_name}...")
            
            # Special handling for inflation (non-linear transformation)
            if factor_name == 'inflation':
                df_transformed = self.calculate_inflation_risk(df)
                if len(df_transformed) > 0:
                    # Add transformed indicators to main df
                    df = pd.concat([df, df_transformed], ignore_index=True)
                    # Update indicators to use transformed versions
                    indicators_to_use = {
                        ind.replace('_SA_P1M1ML12', '_IE'): [negate, weight]
                        for ind, (negate, weight) in indicators_dict.items()
                    }
                else:
                    indicators_to_use = indicators_dict
            else:
                indicators_to_use = indicators_dict
            
            # Calculate z-scores for each indicator in this category
            category_scores = []
            for ind, (negate_flag, weight) in indicators_to_use.items():
                df_ind = df[df['xcat'] == ind].copy()
                if len(df_ind) > 0:
                    try:
                        df_zscore = self.calculate_zscores(df, ind)
                        if df_zscore is not None and len(df_zscore) > 0:
                            # CRITICAL: Apply sign adjustment
                            # If negate_flag=True, multiply by -1 so positive = higher risk
                            if negate_flag:
                                df_zscore['value'] = df_zscore['value'] * -1
                                print(f"    [OK] Z-score calculated for {ind} (negated)")
                            else:
                                print(f"    [OK] Z-score calculated for {ind}")
                            
                            category_scores.append(df_zscore)
                    except Exception as e:
                        print(f"    Warning: Could not calculate z-score for {ind}: {e}")
            
            print(f"    Total z-scores for {factor_name}: {len(category_scores)}")
            
            if category_scores:
                # Combine scores for this category
                category_df = pd.concat(category_scores, ignore_index=True)
                print(f"    Combined category data shape: {category_df.shape}")
                print(f"    Available xcats: {category_df['xcat'].unique().tolist()}")
                
                # Calculate WEIGHTED average score across indicators in this category
                indicators_in_cat = [ind + '_ZN' for ind in indicators_to_use.keys()]
                
                # Filter to only indicators that exist in the data
                available_indicators = [ind for ind in indicators_in_cat if ind in category_df['xcat'].unique()]
                print(f"    Available indicators for composite: {available_indicators}")
                
                if available_indicators:
                    try:
                        # Get countries that have data for this category
                        available_cids = category_df['cid'].unique().tolist()
                        
                        # Extract weights for available indicators (order matters!)
                        weights_list = []
                        for ind_zn in available_indicators:
                            ind_base = ind_zn.replace('_ZN', '')
                            weights_list.append(indicators_to_use[ind_base][1])
                        
                        composite = msp.linear_composite(
                            category_df,
                            xcats=available_indicators,
                            cids=available_cids,
                            weights=weights_list,
                            normalize_weights=True,  # Normalize weights to sum to 1
                            new_xcat=f"{factor_name.upper()}RISK",
                            complete_xcats=False,
                        )
                        
                        # Ensure composite has the right structure
                        if not isinstance(composite, pd.DataFrame):
                            composite = pd.DataFrame(composite)
                        
                        print(f"    Composite shape: {composite.shape}")
                        all_scores.append(composite)
                        print(f"    [OK] Created {factor_name.upper()}RISK score ({len(available_indicators)} indicators)")
                    except Exception as e:
                        print(f"    Error creating composite for {factor_name}: {e}")
        
        if all_scores:
            result = pd.concat(all_scores, ignore_index=True)
            print(f"\n[OK] Calculated {len(all_scores)} factor risk scores")
            print(f"  Total rows: {len(result)}")
            print(f"  Unique xcats: {result['xcat'].unique().tolist()}")
            print(f"\n  IMPORTANT: Positive scores = HIGHER RISK for all factors")
            return result
        
        print(f"\n[ERROR] No factor scores could be generated")
        return pd.DataFrame()
    
    def calculate_composite_score(self, factor_scores: pd.DataFrame,
                                  weights: Optional[Dict[str, float]] = None) -> pd.DataFrame:
        """
        Calculate composite macro risk score from factor scores
        
        Args:
            factor_scores: DataFrame with individual factor scores
            weights: Optional dict of weights per factor (default: equal weights)
            
        Returns:
            DataFrame with composite MACRORISK score
        """
        print("\nCalculating composite macro risk score...")
        
        if factor_scores is None or len(factor_scores) == 0:
            print("  Warning: No factor scores available to create composite")
            return pd.DataFrame()
        
        # Get list of factor score names
        factor_names = factor_scores['xcat'].unique().tolist()
        
        if len(factor_names) == 0:
            print("  Warning: No factor scores found in data")
            return pd.DataFrame()
        
        print(f"  Using {len(factor_names)} factors: {', '.join(factor_names)}")
        
        if weights is None:
            # Equal weights
            weights_list = [1.0 / len(factor_names)] * len(factor_names)
        else:
            weights_list = [weights.get(fname, 1.0) for fname in factor_names]
        
        # Get countries that have data
        available_cids = factor_scores['cid'].unique().tolist()
        
        # Calculate weighted composite
        composite = msp.linear_composite(
            factor_scores,
            xcats=factor_names,
            cids=available_cids,  # Use only countries with data
            weights=weights_list,
            normalize_weights=True,
            complete_xcats=False,
            new_xcat="MACRORISK_COMPOSITE",
        )
        
        # Re-normalize the composite score
        composite_normalized = self.calculate_zscores(composite, "MACRORISK_COMPOSITE")
        
        print(f"  [OK] Created MACRORISK_COMPOSITE_ZN score")
        
        return composite_normalized
    
    def calculate_4factor_composite(self, factor_scores: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate 4-factor macro risk composite for country ranking
        Uses: Govt Finance + External Balance + Intl Investment + Governance
        Excludes: Growth, Inflation, Foreign Debt (more cyclical/volatile)
        
        Args:
            factor_scores: DataFrame with individual factor scores
            
        Returns:
            DataFrame with 4-factor MACRORISK composite
        """
        print("\nCalculating 4-factor composite macro risk score...")
        
        if factor_scores is None or len(factor_scores) == 0:
            print("  Warning: No factor scores available to create composite")
            return pd.DataFrame()
        
        # Select 4 structural factors
        selected_factors = [
            'GOVT_FINANCERISK',
            'EXTERNAL_BALANCERISK', 
            'INTL_INVESTMENTRISK',
            'GOVERNANCERISK'
        ]
        
        # Filter to only selected factors
        factor_data = factor_scores[factor_scores['xcat'].isin(selected_factors)].copy()
        
        if len(factor_data) == 0:
            print("  Warning: No selected factors found in data")
            return pd.DataFrame()
        
        available_factors = factor_data['xcat'].unique().tolist()
        print(f"  Using {len(available_factors)} factors: {', '.join(available_factors)}")
        
        # Equal weights for available factors
        weights_list = [1.0 / len(available_factors)] * len(available_factors)
        
        # Get countries that have data
        available_cids = factor_data['cid'].unique().tolist()
        
        # Calculate weighted composite
        composite = msp.linear_composite(
            factor_data,
            xcats=available_factors,
            cids=available_cids,
            weights=weights_list,
            normalize_weights=True,
            complete_xcats=False,
            new_xcat="MACRORISK_4FACTOR",
        )
        
        # Re-normalize the composite score
        composite_normalized = self.calculate_zscores(composite, "MACRORISK_4FACTOR")
        
        print(f"  [OK] Created MACRORISK_4FACTOR_ZN score")
        
        return composite_normalized
    
    def process_all_scores(self, start_date: str = "2000-01-01",
                          countries: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Complete end-to-end processing pipeline
        
        Args:
            start_date: Start date for data
            countries: List of country codes (default: all 24)
            
        Returns:
            DataFrame with all factor scores and composite score
        """
        print("="*60)
        print("EM Sovereign Macro Risk Scoring Pipeline")
        print("="*60)
        
        # Step 1: Download data
        raw_data = self.download_data(start_date, countries)
        
        # Step 2: Calculate factor scores
        factor_scores = self.calculate_factor_scores(raw_data)
        
        if len(factor_scores) == 0:
            print("\n[ERROR] No factor scores could be calculated")
            return pd.DataFrame()
        
        # Step 3: Calculate composite scores (both equal-weight and 4-factor)
        composite_score = self.calculate_composite_score(factor_scores)
        composite_4factor = self.calculate_4factor_composite(factor_scores)
        
        # Combine all scores
        score_components = [factor_scores]
        if len(composite_score) > 0:
            score_components.append(composite_score)
        if len(composite_4factor) > 0:
            score_components.append(composite_4factor)
        
        all_scores = pd.concat(score_components, ignore_index=True)
        
        self.processed_data = all_scores
        
        print("\n" + "="*60)
        print("[OK] Processing complete!")
        print(f"  Total scores generated: {len(all_scores):,} rows")
        print(f"  Score types: {all_scores['xcat'].nunique()}")
        print(f"  Countries with data: {all_scores['cid'].nunique()}")
        print("="*60)
        
        return all_scores
    
    def get_latest_scores(self, as_of_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get latest available scores for all countries
        
        Args:
            as_of_date: Specific date (YYYY-MM-DD), or None for most recent
            
        Returns:
            DataFrame with latest scores per country
        """
        if self.processed_data is None:
            raise ValueError("No processed data available. Run process_all_scores() first.")
        
        df = self.processed_data.copy()
        
        if as_of_date:
            df = df[df['real_date'] <= pd.to_datetime(as_of_date)]
        
        # Get latest date for each country-indicator combination
        latest = df.sort_values('real_date').groupby(['cid', 'xcat']).tail(1)
        
        # Pivot to wide format for easy viewing
        pivot = latest.pivot_table(
            index='cid',
            columns='xcat',
            values='value',
            aggfunc='first'
        )
        
        # Add country names
        pivot['country_name'] = pivot.index.map(self.COUNTRY_NAMES)
        
        return pivot
    
    def format_for_database(self, as_of_date: Optional[str] = None) -> pd.DataFrame:
        """
        Format scores for database insertion
        
        Returns:
            DataFrame ready for PostgreSQL insertion
        """
        latest_scores = self.get_latest_scores(as_of_date)
        
        # Prepare for database format
        db_df = latest_scores.reset_index()
        
        # Rename columns for database
        rename_map = {
            'cid': 'country_code',
            'GOVT_FINANCERISK': 'govt_finance_score',
            'EXTERNAL_BALANCERISK': 'external_balance_score',
            'INTL_INVESTMENTRISK': 'intl_investment_score',
            'FOREIGN_DEBTRISK': 'foreign_debt_score',
            'GOVERNANCERISK': 'governance_score',
            'GROWTHRISK': 'growth_risk_score',
            'INFLATIONRISK': 'inflation_risk_score',
            'MACRORISK_COMPOSITE_ZN': 'composite_macro_risk',
            'MACRORISK_4FACTOR_ZN': 'composite_4factor_risk',
        }
        
        db_df = db_df.rename(columns=rename_map)
        
        # Add date column
        if as_of_date:
            db_df['date'] = pd.to_datetime(as_of_date)
        else:
            db_df['date'] = datetime.now().date()
        
        return db_df


def main():
    """Example usage"""
    
    # Initialize calculator
    calc = MacroRiskCalculator(
        credentials_path=r"C:\Users\vargaro\Downloads\client_credentials.json"
    )
    
    # Process all scores (use recent data for speed)
    scores = calc.process_all_scores(start_date="2020-01-01")
    
    # Get latest scores
    latest = calc.get_latest_scores()
    print("\n" + "="*60)
    print("Latest Macro Risk Scores by Country")
    print("="*60)
    print(latest.to_string())
    
    # Format for database
    db_ready = calc.format_for_database()
    print("\n" + "="*60)
    print("Database-Ready Format (first 5 rows)")
    print("="*60)
    print(db_ready.head().to_string())
    
    return calc, scores, latest


if __name__ == "__main__":
    calculator, all_scores, latest_scores = main()
