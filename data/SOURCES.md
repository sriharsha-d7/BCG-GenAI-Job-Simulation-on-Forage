# Data sources and corrections

All values are USD millions, taken from each company's annual Form 10-K via the SEC XBRL API
(`https://data.sec.gov/api/xbrl/companyconcept/CIK<cik>/us-gaap/<concept>.json`):

| Column | XBRL concept(s) |
|---|---|
| revenue | `RevenueFromContractWithCustomerExcludingAssessedTax` (Apple, Microsoft), `Revenues` (Tesla) |
| net_income | `NetIncomeLoss` (attributable to common stockholders) |
| total_assets | `Assets` |
| total_liabilities | `Liabilities` |
| operating_cash_flow | `NetCashProvidedByUsedInOperatingActivities` |

CIKs: Apple 0000320193, Microsoft 0000789019, Tesla 0001318605. Fiscal years end in September (Apple), June (Microsoft)
and December (Tesla), so "2024" is **not the same calendar window** across companies; `period_end` records the exact date.

## Corrections to the Forage-supplied file (`archive/financial_data_2_original.csv`)

1. **Fiscal-year labels were wrong for every company.** Each company's three rows were labelled 2022, 2023, 2023.
   Matching the values to the filings shows they are FY2023, FY2024 and FY2022. For example the "Apple 2022" row
   (revenue 383,285) is FY2023, and the second "2023" row (394,328) is FY2022.
2. **Tesla net income** differed from the filings in two years: file 14,974 vs filed 14,997 (2023), file 7,153 vs
   filed 7,091 (2024). The 2022 value (12,587) in the file includes non-controlling interests; the filed
   `NetIncomeLoss` is 12,556. All three now use `NetIncomeLoss`.

Apple and Microsoft's other columns and Tesla's remaining columns matched the filings once years were relabelled.
Verified on 2026-10-05; XBRL values can be restated by later filings.
