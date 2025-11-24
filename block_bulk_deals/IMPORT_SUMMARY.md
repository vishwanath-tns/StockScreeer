# 🎉 NSE Block & Bulk Deals - 1 Year Import Complete

**Import Date:** November 23, 2025  
**Data Period:** Nov 23, 2024 to Nov 21, 2025 (1 year)

---

## 📊 Import Statistics

### **Block Deals**
- **Total Deals:** 2,057
- **Date Range:** Dec 2, 2024 to Nov 21, 2025
- **Unique Symbols:** 253
- **Unique Clients:** 707
- **Total Value:** ₹233,850 Cr

### **Bulk Deals**
- **Total Deals:** 18,755
- **Date Range:** Nov 25, 2024 to Nov 21, 2025
- **Unique Symbols:** 1,562
- **Unique Clients:** 3,175
- **Total Value:** ₹703,268 Cr

---

## 📈 Monthly Distribution

### Block Deals by Month
| Month    | Deals | Symbols | Value (₹ Cr) |
|----------|------:|--------:|-------------:|
| 2025-11  | 157   | 35      | 28,926       |
| 2025-10  | 248   | 82      | 13,390       |
| 2025-09  | 666   | 75      | 51,407       |
| 2025-08  | 137   | 28      | 9,155        |
| 2025-07  | 115   | 56      | 3,558        |
| 2025-06  | 261   | 28      | 71,993       |
| 2025-05  | 93    | 15      | 8,005        |
| 2025-04  | 16    | 2       | 426          |
| 2025-03  | 63    | 20      | 7,079        |
| 2025-02  | 101   | 9       | 18,698       |
| 2025-01  | 58    | 29      | 3,875        |
| 2024-12  | 142   | 15      | 15,339       |

### Bulk Deals by Month
| Month    | Deals | Symbols | Value (₹ Cr) |
|----------|------:|--------:|-------------:|
| 2025-11  | 1,053 | 226     | 43,333       |
| 2025-10  | 1,873 | 294     | 52,131       |
| 2025-09  | 2,648 | 370     | 85,789       |
| 2025-08  | 1,634 | 272     | 72,377       |
| 2025-07  | 2,122 | 295     | 46,923       |
| 2025-06  | 1,414 | 272     | 109,965      |
| 2025-05  | 1,127 | 214     | 77,887       |
| 2025-04  | 776   | 182     | 20,460       |
| 2025-03  | 1,337 | 322     | 43,750       |
| 2025-02  | 890   | 208     | 28,714       |
| 2025-01  | 1,472 | 231     | 44,371       |
| 2024-12  | 2,144 | 326     | 77,567       |

---

## 🏆 Top Clients by Deal Value

### Block Deals - Top 10 Clients
| Client Name                                      | Deals | Total Qty      | Value (₹ Cr) |
|--------------------------------------------------|------:|---------------:|-------------:|
| GOLDMAN SACHS BANK EUROPE SE - ODI               | 205   | 284,335,950    | 12,518       |
| GOLDMAN SACHS (SINGAPORE) PTE - ODI              | 189   | 253,963,057    | 11,246       |
| SBI MUTUAL FUND                                  | 7     | 46,957,896     | 9,926        |
| AZIM PREMJI TRUST                                | 2     | 382,800,000    | 9,732        |
| SIDDHANT COMMERCIALS PRIVATE LIMITED             | 2     | 43,500,000     | 9,579        |
| INDIAN CONTINENT INVESTMENT LIMITED              | 1     | 51,115,092     | 8,485        |
| RELIANCE TRUST INSTITUTIONAL RETIREMENT TRUST... | 11    | 131,983,051    | 6,702        |
| GQG PARTNERS INTERNATIONAL EQUITY CIT            | 10    | 130,839,353    | 6,512        |
| SUMITOMO MITSUI BANKING CORPORATION              | 2     | 32,234,820     | 6,256        |
| ICICI PRUDENTIAL MUTUAL FUND                     | 16    | 57,347,982     | 5,277        |

### Bulk Deals - Top 10 Clients
| Client Name                            | Deals | Value (₹ Cr) |
|----------------------------------------|------:|-------------:|
| GRAVITON RESEARCH CAPITAL LLP          | 2,088 | 155,838      |
| HRTI PRIVATE LIMITED                   | 1,560 | 60,587       |
| AAKRAYA RESEARCH LLP                   | 590   | 33,347       |
| PASTEL LIMITED                         | 2     | 23,235       |
| INDIAN CONTINENT INVESTMENT LIMITED    | 3     | 19,712       |
| QE SECURITIES LLP                      | 784   | 18,625       |
| JUNOMONETA FINSOL PRIVATE LIMITED      | 484   | 17,077       |
| NK SECURITIES RESEARCH PRIVATE LIMITED | 582   | 15,551       |
| SBI MUTUAL FUND                        | 16    | 14,097       |
| THE CHINKERPOO FAMILY TRUST            | 5     | 13,341       |

---

## 📁 Files Imported

1. **Block-Deals-23-11-2024-to-23-11-2025.csv**
   - 2,057 records
   - Successfully imported to `nse_block_deals` table

2. **Bulk-Deals-23-11-2024-to-23-11-2025.csv**
   - 18,755 records
   - Successfully imported to `nse_bulk_deals` table

---

## 🔍 Key Insights

### Block Deals
- **Highest Activity:** September 2025 (666 deals, ₹51,407 Cr)
- **Largest Single Month Value:** June 2025 (₹71,993 Cr)
- **Top Foreign Investors:** Goldman Sachs entities dominate
- **Domestic Giants:** SBI MF, Azim Premji Trust, ICICI Prudential MF

### Bulk Deals
- **Most Active Clients:** Proprietary trading firms (Graviton, HRTI, Aakraya)
- **Highest Activity:** September 2025 (2,648 deals)
- **Largest Month Value:** June 2025 (₹109,965 Cr)
- **Average Deal Size:** ₹3.75 Cr per deal

---

## 🎯 Database Tables

All data is stored in the `marketdata` database:

1. **nse_block_deals** - Block deals (5 lakh+ shares)
2. **nse_bulk_deals** - Bulk deals (≥0.5% equity)
3. **block_bulk_deals_import_log** - Import tracking

---

## 📊 Sample Queries

### Recent Block Deals
```sql
SELECT * FROM nse_block_deals 
ORDER BY trade_date DESC, quantity DESC 
LIMIT 20;
```

### Symbol-wise Analysis
```sql
SELECT 
    symbol,
    COUNT(*) as deals,
    SUM(CASE WHEN deal_type = 'BUY' THEN 1 ELSE 0 END) as buys,
    SUM(CASE WHEN deal_type = 'SELL' THEN 1 ELSE 0 END) as sells,
    SUM(quantity * trade_price) / 10000000 as value_cr
FROM nse_block_deals
GROUP BY symbol
ORDER BY value_cr DESC
LIMIT 20;
```

### Client Activity
```sql
SELECT 
    client_name,
    trade_date,
    symbol,
    deal_type,
    quantity,
    trade_price,
    quantity * trade_price / 10000000 as value_cr
FROM nse_bulk_deals
WHERE client_name LIKE '%SBI MUTUAL FUND%'
ORDER BY trade_date DESC;
```

### Daily Summary
```sql
SELECT 
    trade_date,
    COUNT(*) as deals,
    COUNT(DISTINCT symbol) as symbols,
    COUNT(DISTINCT client_name) as clients,
    SUM(quantity * trade_price) / 10000000 as total_value_cr
FROM nse_bulk_deals
GROUP BY trade_date
ORDER BY trade_date DESC
LIMIT 30;
```

---

## ✅ Next Steps

1. **Analysis:** Use the sample queries to analyze patterns
2. **Integration:** Connect with main stock screener for symbol analysis
3. **Alerts:** Set up monitoring for specific clients/symbols
4. **Updates:** Download and import weekly CSV files from NSE

---

## 📖 Documentation

- **QUICKSTART.md** - Complete usage guide
- **README.md** - Full module documentation
- **SETUP_STATUS.md** - Technical implementation details

---

**Status:** ✅ **COMPLETE & OPERATIONAL**

The NSE Block & Bulk Deals module is now fully functional with 1 year of historical data imported and ready for analysis! 🎉
