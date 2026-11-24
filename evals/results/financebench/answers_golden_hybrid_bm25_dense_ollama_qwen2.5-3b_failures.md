# Failure analysis: qwen2.5:3b, retrieval `+hybrid_bm25_dense`, 50 golden questions

| Bucket | Count | Share | What would fix it |
|---|---|---|---|
| correct | 17 | 34% |  |
| wrong_filing | 2 | 4% | routing: company / year / quarter detection, or ask the user which filing |
| evidence_page_missed | 9 | 18% | ranking: better embeddings or reranker, table-aware chunks |
| partial_evidence | 6 | 12% | multi-page retrieval: one search per statement (income statement AND balance sheet) |
| refused_with_evidence | 8 | 16% | prompt / model: the context had the numbers; a bigger model or a 'find the line items first' step |
| wrong_number | 5 | 10% | reading tables: line-item extraction before arithmetic, use a calculator tool |
| wrong_conclusion | 3 | 6% | reasoning: bigger model, or domain hints (e.g. 'gross margin does not apply to banks') |

Retrieval failures: 17. Generation failures: 16.

| Bucket | calculation | judgment | lookup |
|---|---|---|---|
| correct | 6 | 1 | 10 |
| wrong_filing | 1 | 1 | 0 |
| evidence_page_missed | 4 | 1 | 4 |
| partial_evidence | 6 | 0 | 0 |
| refused_with_evidence | 0 | 3 | 5 |
| wrong_number | 3 | 0 | 2 |
| wrong_conclusion | 0 | 0 | 3 |

## wrong_filing

- **financebench_id_00206**: Are JPM's gross margins historically consistent (not fluctuating more than roughly 2% each year)? If gross margins are not a relevant metric for a company like this, then please state that and explain why.
  - expert: Since JPM is a financial institution, gross margin is not a relevant metric.
  - model: Not enough information in the provided filings. The gross margins are not a relevant metric for a company like JPMorgan Chase, which operates in various financial services sectors including investment banking, asset management, and commercial banking. The provided financial statements and disclosure
- **financebench_id_00283**: How much does Pfizer expect to pay to spin off Upjohn in the future in USD million?
  - expert: About $70 million (roughly 10% of the expected $700 million is still to come).
  - model: Not enough information in the provided filings.

## evidence_page_missed

- **financebench_id_00080**: Does Paypal have positive working capital based on FY2022 data? If working capital is not a useful or relevant metric for this company, then please state that and explain why.
  - expert: Yes. Paypal has a positive working capital of $ 1.6Bn as of FY2022 end.
  - model: Not enough information in the provided filings. The provided sources do not contain specific information about Paypal's working capital for the fiscal year 2022. The sources focus on the company's merchant finance products, credit products, and financial instruments, but do not provide a direct calc
- **financebench_id_00302**: Did Pfizer grow its PPNE between FY20 and FY21?
  - expert: Yes, change in PPNE was positive year over year
  - model: Not enough information in the provided filings.
- **financebench_id_00723**: Does AMEX have an improving operating margin profile as of 2022? If operating margin is not a useful metric for a company like this, then state that and explain why.
  - expert: Performance is not measured through operating margin
  - model: Not enough information in the provided filings. The operating margin is not a useful metric for a company like American Express, which has significant investments in strategic investments and variable expenses related to card member rewards and business development. The provided sources do not conta

## partial_evidence

- **financebench_id_06272**: What is Coca Cola's FY2022 dividend payout ratio (using total cash dividends paid and net income attributable to shareholders)? Round answer to two decimal places. Answer the question asked by assuming you only have acce
  - expert: 0.8
  - model: Not enough information in the provided filings.
- **financebench_id_06741**: What is the FY2018 - FY2020 3 year average unadjusted EBITDA % margin for Walmart? Define unadjusted EBITDA as unadjusted operating income + depreciation and amortization from the cash flow statement. Answer in units of 
  - expert: 6.2%
  - model: Not enough information in the provided filings.
- **financebench_id_03856**: What is the FY2017 operating cash flow ratio for Adobe? Operating cash flow ratio is defined as: cash from operations / total current liabilities. Round your answer to two decimal places. Please utilize information provi
  - expert: 0.83
  - model: First, we need to find the operating cash flow for fiscal 2017 from the cash flow statement [S1], which is $2,912,853 thousand or $2,912.9 million. Next, we need to find total current liabilities from the balance sheet [S2], which is $3,720.4 million. Operating cash flow ratio for FY2017 = $2,912

## refused_with_evidence

- **financebench_id_00394**: In 2022 Q2, which of JPM's business segments had the highest net income?
  - expert: Corporate & Investment Bank. Its net income was $3725 million.
  - model: To determine which of JPM's business segments had the highest net income in 2022 Q2, we need to look at the net income for each segment. [S3] provides the ROE (Return on Equity) for each segment, but not the net income. [S2] provides the net income for the Firmwide overview, but not by segment. [S4]
- **financebench_id_00746**: Which debt securities are registered to trade on a national securities exchange under Ulta Beauty's name as of FY2023?
  - expert: There are none
  - model: Not enough information in the provided filings.
- **financebench_id_01091**: Has Boeing reported any materially important ongoing legal battles from FY2022?
  - expert: Yes. Multiple lawsuits have been filed against Boeing resulting from a 2018 Lion Air crash and a 2019 Ethiopian Airlines crash.
  - model: Not enough information in the provided filings.

## wrong_number

- **financebench_id_04254**: Basing your judgments off of the cash flow statement and the income statement, what is American Water Works's FY2021 unadjusted operating income + depreciation and amortization from the cash flow statement (unadjusted EB
  - expert: $1832.00
  - model: To find American Water Works's FY2021 unadjusted operating income + depreciation and amortization from the cash flow statement (unadjusted EBITDA), we need to use the information from the Consolidated Statements of Cash Flows (S2) and the Consolidated Results of Operations (S5). From S2, we see the
- **financebench_id_00566**: Has Verizon increased its debt on balance sheet between 2022 and the 2021 fiscal period?
  - expert: No. Verizon's debt decreased by $229 million.
  - model: To determine if Verizon increased its debt on balance sheet between 2022 and 2021, we need to compare the total debt outstanding at the end of these two fiscal periods. From [S2], we see that at December 31, 2021, Verizon's total debt was $150.9 billion. From [S1], we see that at December 31, 2022
- **financebench_id_07507**: What is Adobe's year-over-year change in unadjusted operating income from FY2015 to FY2016 (in units of percents and round to one decimal place)? Give a solution to the question by using the income statement.
  - expert: 65.4%
  - model: [Q] To find the year-over-year change in unadjusted operating income from fiscal year 2015 to fiscal year 2016, we need to calculate the percentage change between the two years using the operating income figures provided in the 10K filings. [1] For fiscal year 2016, the operating income is $1,435,1

## wrong_conclusion

- **financebench_id_00724**: For Pfizer, which geographic region had the biggest drop in Q22023 year over year revenues (on a percentage basis)?
  - expert: Developed Rest of the World
  - model: To determine which geographic region had the biggest drop in Q22023 year over year revenues, we need to compare the percentage changes in revenues for each region. The relevant information is provided in [S1] and [S2]. From [S1]: - Worldwide: -54% - U.S.: -45% - Developed Europe: -56% - Developed R
- **financebench_id_01346**: How much has the effective tax rate of Corning changed between FY2021 and FY2022?
  - expert: The effective tax rate of Corning has changed from 20% in FY2021 to 23% in FY 2022.
  - model: To calculate the change in effective tax rate between FY2021 and FY2022, we use the information provided in [S2] and [S3]. From [S2]: - Effective tax rate for 2022: 22.9% - Effective tax rate for 2021: 20.2% From [S3]: - Effective tax rate for 2022: 19.3% The change in effective tax rate between
- **financebench_id_01163**: Among operations, investing, and financing activities, which brought in the most (or lost the least) cash flow for Nike in FY2023?
  - expert: Among the three, cash flow from operations was the highest for Nike in FY2023.
  - model: To determine which activity brought in the most (or lost the least) cash flow for Nike in FY2023, we need to compare the cash flows from operations, investing, and financing activities. From the provided sources: - [S1] provides the cash flow from operations for FY2023, which is $5,841 million. - [
