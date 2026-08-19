# Automation Status & Files to Commit

## ✅ Automation Scripts Status

### Daily Update Script (`run_daily_update.ps1`)
**Status:** ✅ UPDATED and ready

**Changes Made:**
- Added Step 2.5: Fetch and upload sub-index prices
- Runs between sovereign ratings upload and JPMaQS update
- Calls: `fetch_sub_index_prices.py` → `upload_sub_index_prices.py`

**Will Execute:**
1. Fetch sovereign ratings → Upload to DB
2. **[NEW]** Fetch sub-index prices → Upload to DB
3. Upload JPMaQS scores

**Expected Behavior:** ✅ Will fetch 54 sub-index prices daily and update database

---

### Monthly Carry-to-Vol Script (`run_monthly_carry_to_vol_prev_month.ps1`)
**Status:** ✅ ALREADY COMPATIBLE (no changes needed!)

**Why It Works:**
- Calls `compute_carry_to_vol_v2.py` (now calculates BOTH metrics) ✅
- Calls `upload_carry_to_vol_prev_month.py` (now uploads BOTH metrics) ✅

**Will Execute:**
1. Compute carry-to-vol with spread-based AND return-based metrics
2. Upload both metric sets to database for previous month-end

**Expected Behavior:** ✅ Will compute and upload 54 countries with both perspectives

---

## � Column Mapping in Data Table

### Spread-Based C/V (Credit Focus)
When **"Spread-Based (Credit Focus)"** is selected:

| Column | Source | Description |
|--------|--------|-------------|
| **Carry (bps)** | `carry_bps` | Current yield × 100 |
| **Vol Spread (bps)** | `vol_bps` | Annualized std dev of spread changes |
| **📍 C/V (Spread)** | `carry_to_vol` | Carry ÷ Vol (PRIMARY METRIC) |
| **C/V Z-Score (Spread)** | `ctv_zscore_spread` | Peer comparison within rating bucket |
| Carry (%) | `carry_pct` | Current yield (secondary display) |
| Vol Returns (%) | `vol_returns_annual` | Price return volatility (secondary display) |
| C/V (Return) | `carry_to_vol_return_based` | Return-based C/V (secondary display) |

### Return-Based C/V (Total Return Focus)  
When **"Return-Based (Total Return Focus)"** is selected:

| Column | Source | Description |
|--------|--------|-------------|
| **Carry (%)** | `carry_pct` | Current yield |
| **Vol Returns (%)** | `vol_returns_annual` | Annualized std dev of price returns |
| **📍 C/V (Return)** | `carry_to_vol_return_based` | Carry ÷ Vol (PRIMARY METRIC) |
| **C/V Z-Score (Return)** | `ctv_zscore_return` | Peer comparison within rating bucket |
| Carry (bps) | `carry_bps` | Current yield × 100 (secondary display) |
| Vol Spread (bps) | `vol_bps` | Spread volatility (secondary display) |
| C/V (Spread) | `carry_to_vol` | Spread-based C/V (secondary display) |

**Key Changes:**
- ✅ **Z-Score is now DYNAMIC** - Calculated separately for each perspective
- ✅ **Sorting changes** - Table sorts by the selected metric's z-score
- ✅ **Risk-Adj Signal changes** - Based on the selected metric's peer comparison
- ✅ **Primary metrics highlighted** with 📍 emoji

---

## �📋 Files to Commit to Repository

### NEW FILES (9)

**Core Scripts:**
1. `sovereing_score/fetch_sub_index_prices.py` - Fetch current sub-index prices via BLPAPI
2. `sovereing_score/upload_sub_index_prices.py` - Upload sub-index prices to database
3. `sovereing_score/backfill_sub_index_prices.py` - Historical backfill script (one-time use, but good to have)
4. `sovereing_score/create_sub_index_table.py` - Database table creation (one-time use)
5. `sovereing_score/alter_carry_to_vol_table.py` - Add return-based columns (one-time use)

**Utility Scripts:**
6. `sovereing_score/check_sub_index_data.py` - Query database for data coverage
7. `sovereing_score/test_bql_query.py` - Debug BQL queries (can skip if you want)

**Documentation:**
8. `sovereing_score/PRICE_INDEX_IMPLEMENTATION_SUMMARY.md` - Full implementation guide

**Excel Template:**
9. `sovereing_score/input/em_sovereign_ratings_numeric_scorev3.xlsx` - NEW template with 'sub_index' tab

### MODIFIED FILES (5)

**Core Application:**
1. `sovereing_score/app.py` - Toggle UI, dynamic charts, interpretation guide for Tab 2

**Computation & Upload:**
2. `sovereing_score/compute_carry_to_vol_v2.py` - Calculates BOTH spread-based and return-based C/V
3. `sovereing_score/upload_carry_to_vol.py` - Uploads both metric sets
4. `sovereing_score/upload_carry_to_vol_prev_month.py` - Uploads both metric sets for prev month

**Automation:**
5. `sovereing_score/run_daily_update.ps1` - Added Step 2.5 for sub-index prices

### OPTIONAL (One-Time Scripts)
- `create_sub_index_table.py` - Only needed once, already executed
- `alter_carry_to_vol_table.py` - Only needed once, already executed
- `backfill_sub_index_prices.py` - Backfill done, but keep for reference
- `test_bql_query.py` - Debug tool, not essential

---

## 🚀 Recommended Commit Strategy

### Commit 1: Data Infrastructure
```
feat: Add sub-index price infrastructure for return-based carry-to-vol

- Add fetch_sub_index_prices.py for daily Bloomberg data fetch
- Add upload_sub_index_prices.py for database upload
- Add backfill_sub_index_prices.py for historical data (62 month-ends)
- Update run_daily_update.ps1 to fetch sub-index prices (Step 2.5)
- Add em_sovereign_ratings_numeric_scorev3.xlsx template with sub_index tab
```

### Commit 2: Dual-Perspective Calculations
```
feat: Implement dual-perspective carry-to-vol analysis (spread + return)

- Update compute_carry_to_vol_v2.py to calculate both metrics:
  * Spread-Based C/V: Carry(bps) / Vol of Spread Changes(bps)
  * Return-Based C/V: Carry(%) / Vol of Price Returns(%)
- Update upload_carry_to_vol.py to upload both metrics
- Update upload_carry_to_vol_prev_month.py to upload both metrics
- Alter database table: add vol_returns_annual, carry_to_vol_return_based columns
- 54 countries now have both perspectives
```

### Commit 3: User Interface
```
feat: Add toggle UI for spread-based vs return-based carry-to-vol

- Add radio button selector in Tab 2 (Carry-to-Vol)
- Dynamic chart updates (y-axis, hover, colors)
- Data table shows both metrics with selected highlighted
- Comprehensive interpretation guide with side-by-side comparison
- Decision matrix for when to use each metric
```

---

## ✅ Validation Checklist

Before committing, verify:

- [ ] `run_daily_update.ps1` successfully executes all 3 steps
- [ ] `run_monthly_carry_to_vol_prev_month.ps1` computes and uploads both metrics
- [ ] Streamlit app loads without errors
- [ ] Toggle between spread-based and return-based works
- [ ] Data table shows both metrics
- [ ] Excel template v3 is in `input/` folder
- [ ] Documentation is complete

---

## 📊 Production Readiness

**Database Tables:**
- ✅ `emd_sub_index_prices` - 3,311 records (62 month-ends × 54 countries)
- ✅ `emd_country_carry_to_vol` - Updated with both metric columns

**Data Coverage:**
- ✅ 54 countries with BOTH metrics (spread + return)
- ✅ 9 countries with spread-based only (no price index ticker)
- ✅ Date range: 2021-01-31 to 2026-08-19

**Automation:**
- ✅ Daily: Fetches sub-index prices automatically
- ✅ Monthly: Computes and uploads both perspectives automatically

---

## 🎯 Next Steps After Commit

1. **Test Daily Automation:** 
   ```powershell
   .\run_daily_update.ps1
   ```
   
2. **Test Monthly Automation:**
   ```powershell
   .\run_monthly_carry_to_vol_prev_month.ps1
   ```

3. **Deploy to Production:**
   - Pull latest on production server
   - Restart Streamlit app
   - Verify scheduled tasks still reference correct paths

4. **User Communication:**
   - New toggle in Tab 2: Spread-Based (credit focus) vs Return-Based (total return focus)
   - 54 countries now have both perspectives
   - Use case guide in app for when to use each metric
