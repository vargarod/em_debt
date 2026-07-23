# JPMaQS Fundamental Risk Integration - Summary

## 🎯 Completed Enhancements

### 1. **4-Factor Composite Added** ✅
   - **Purpose**: Structural risk scoring for country ranking
   - **Factors**: 
     - Government Finance Risk
     - External Balance Risk
     - International Investment Risk  
     - Governance Risk
   - **Why 4 Factors?**: Excludes more cyclical/volatile factors (Growth, Inflation, Foreign Debt) to focus on structural fundamentals
   - **Location**: `macro_risk_calculator.py` → `calculate_4factor_composite()`

### 2. **Database Schema Updated** ✅
   - Added column: `composite_4factor_risk NUMERIC(10, 6)`
   - Table: `securitized_research.emd_jpmaqs_fundamental_scoring`
   - Successfully uploaded 23 countries with both 7-factor and 4-factor composites

### 3. **New Streamlit Tab: "🎯 Fundamental Risk"** ✅
   - **Location**: [app.py](app.py) (Tab 4)
   - **Three View Modes**:
     
     #### a) **All Factors** (Table View)
     - Shows all 7 individual factor scores + both composites
     - Color-coded by risk level:
       - 🔴 High Risk (>+1.5)
       - 🟠 Elevated (+0.5 to +1.5)
       - 🟡 Average (-0.5 to +0.5)
       - 🟢 Low (<-0.5)
     - Sortable by composite risk, country name, or 4-factor score
     
     #### b) **Composite Scores** (Bar Charts)
     - Side-by-side comparison:
       - **Left**: 7-Factor Equal-Weight Composite (for timing/signals)
       - **Right**: 4-Factor Structural Composite (for country ranking)
     - Horizontal bars with risk zone markers
     - Color-coded by risk level
     
     #### c) **Factor Decomposition** (Grouped Bar Chart)
     - Select up to 10 countries for comparison
     - Shows all 7 factors side-by-side
     - Helps identify **what's driving the risk** for each country
     - Detailed data table with color-coded cells

### 4. **Daily Automated Refresh** ✅
   - **Script**: [run_daily_update.ps1](run_daily_update.ps1)
   - **Added Step 3**: JPMaQS fundamental scores update
   - **Execution Order**:
     1. Fetch sovereign ratings from Bloomberg
     2. Upload ratings to PostgreSQL
     3. **NEW**: Update JPMaQS fundamental risk scores
   - **Frequency**: Runs daily via Windows Task Scheduler

---

## 📊 Data Overview (Latest Upload)

### **Coverage**
- **Countries**: 23 EM sovereigns
- **Date**: 2026-07-23
- **Score Types**: 9 (7 factors + 2 composites)
- **Historical Data**: 2020-01-01 to 2026-01-23

### **7-Factor Composite Risk Distribution**
```
Mean:    +0.716
Median:  +0.551
Std Dev:  0.746
Range:   -1.490 (Qatar) to +2.625 (Egypt)
```

### **4-Factor Composite Risk Distribution**
```
Mean:    +0.733
Median:  +1.040
Range:   -1.924 (Qatar) to +3.000 (Egypt)
```

### **Risk Breakdown**
- Very Low Risk (<-1.5):       0 countries
- Low Risk (-1.5 to -0.5):     1 country (Qatar)
- Average Risk (-0.5 to +0.5): 9 countries
- Elevated Risk (+0.5 to +1.5): 11 countries
- High Risk (+1.5 to +2.5):    1 country (Nigeria)
- Very High Risk (>+2.5):      1 country (Egypt)

### **Top 5 Safest Countries (7F Composite)**
1. 🟢 **Qatar**       -1.490 (strong fiscal, oil wealth)
2. 🟢 **Peru**        +0.026 (well-managed macro)
3. 🟢 **Uruguay**     +0.245 (stable governance)
4. 🟢 **Indonesia**   +0.268 (strong fundamentals)
5. 🟢 **Hungary**     +0.339 (EU member)

### **Top 5 Highest Risk (7F Composite)**
1. 🔴 **Egypt**            +2.625 (fiscal/external pressures)
2. 🔴 **Nigeria**          +1.549 (oil dependence, governance)
3. 🔴 **Turkey**           +1.377 (high inflation, policy uncertainty)
4. 🔴 **Serbia**           +1.312 (elevated vulnerabilities)
5. 🔴 **Dominican Rep**    +1.222 (external balance issues)

---

## 🔄 How to Use

### **For Analysis**
1. Open Streamlit app: `streamlit run app.py`
2. Navigate to **"🎯 Fundamental Risk"** tab
3. Choose view mode:
   - **All Factors**: For comprehensive overview
   - **Composite Scores**: For quick risk assessment
   - **Factor Decomposition**: To understand drivers

### **For Daily Updates**
```powershell
# Manual run
cd C:\code\em_debt\sovereing_score
.\run_daily_update.ps1

# Check logs
Get-Content .\logs\daily_update_YYYYMMDD.log
```

### **Key Interpretations**

#### **Positive Score = Higher Risk**
All factors follow this convention:
- Govt Finance: Deficit = higher risk
- External Balance: Deficit = higher risk
- Growth: Low growth = higher risk (negated)
- Governance: Poor governance = higher risk (negated)
- etc.

#### **7-Factor vs 4-Factor**
- **7-Factor**: Use for **timing/directional signals** (includes cyclical factors)
- **4-Factor**: Use for **country ranking/relative value** (structural factors only)

#### **Factor Correlations**
- Governance correlates with inflation (+0.505)
- Governance negatively correlates with foreign debt (-0.527)
- Growth risk moves inversely with governance (-0.220)

---

## 📁 Modified Files

1. **[macro_risk_calculator.py](macro_risk_calculator.py)**
   - Added `calculate_4factor_composite()` method
   - Updated `process_all_scores()` to calculate both composites
   - Updated `format_for_database()` to include new column

2. **[upload_jpmaqs_scores.py](upload_jpmaqs_scores.py)**
   - Updated table schema with `composite_4factor_risk` column
   - Updated insert statement to include 4-factor composite
   - Added 4-factor statistics to data exploration

3. **[app.py](app.py)**
   - Added Tab 4: "🎯 Fundamental Risk"
   - Three view modes with interactive visualizations
   - Color-coded risk levels throughout

4. **[run_daily_update.ps1](run_daily_update.ps1)**
   - Added Step 3: JPMaQS fundamental scores update
   - Integrated error handling for new step

5. **Database Schema**
   - Added column: `composite_4factor_risk` to `emd_jpmaqs_fundamental_scoring` table

---

## ✅ What You Requested vs What Was Delivered

| Request | Delivered | Notes |
|---------|-----------|-------|
| New tab in app with fundamental metrics | ✅ Tab 4 created | Three interactive view modes |
| Visuals based on scores | ✅ Implemented | Bar charts, grouped bars, color-coded tables |
| Show individual factors to know drivers | ✅ Factor Decomposition view | Compare up to 10 countries side-by-side |
| Confirm equal weighted | ✅ Yes | 1/7 weight per factor for 7F composite |
| Create 4-factor composite | ✅ Implemented | Structural factors: Govt + Ext Bal + Intl Inv + Gov |
| Add to daily refresh script | ✅ Added Step 3 | Runs after ratings upload |
| Not complicated? | ✅ Simple | One line in PowerShell: `python upload_jpmaqs_scores.py` |

---

## 🚀 Next Steps (Optional Enhancements)

1. **Historical Time Series Upload**
   - Currently only uploads latest date
   - Could backfill full history for time-series analysis in app

2. **Alert Thresholds**
   - Email/notification when country risk crosses threshold
   - Monitor rapid changes in composite scores

3. **Peer Comparison**
   - Show country's rank within its region
   - Z-score vs regional average

4. **Integration with Market Data**
   - Overlay fundamental risk on z-spread charts (Tab 1)
   - Correlation analysis: fundamental risk vs market pricing

---

## 📞 Support

**Data Source**: JPMaQS via MacroSynergy  
**Credentials**: `C:\Users\vargaro\Downloads\client_credentials.json`  
**Database**: Azure PostgreSQL - `gwamdlquantapps-prod-postgresql-server`  
**Schema**: `securitized_research`  
**Table**: `emd_jpmaqs_fundamental_scoring`

For questions or issues, check:
- Script logs: `C:\code\em_debt\sovereing_score\logs\`
- Database connection: `$env:DB_PASSWORD` must be set
- JPMaQS access: Limited to Dataquery (6-month lag on data)

---

**Last Updated**: 2026-07-23  
**Integration Status**: ✅ Complete and Operational
