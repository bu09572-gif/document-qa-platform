# Failure analysis: qwen2.5:7b, retrieval `+hybrid_bm25_dense`, 50 golden questions

| Bucket | Count | Share | What would fix it |
|---|---|---|---|
| correct | 19 | 38% |  |
| wrong_filing | 2 | 4% | routing: company / year / quarter detection, or ask the user which filing |
| evidence_page_missed | 12 | 24% | ranking: better embeddings or reranker, table-aware chunks |
| partial_evidence | 5 | 10% | multi-page retrieval: one search per statement (income statement AND balance sheet) |
| refused_with_evidence | 8 | 16% | prompt / model: the context had the numbers; a bigger model or a 'find the line items first' step |
| wrong_number | 3 | 6% | reading tables: line-item extraction before arithmetic, use a calculator tool |
| wrong_conclusion | 1 | 2% | reasoning: bigger model, or domain hints (e.g. 'gross margin does not apply to banks') |

Retrieval failures: 19. Generation failures: 12.

| Bucket | calculation | judgment | lookup |
|---|---|---|---|
| correct | 7 | 1 | 11 |
| wrong_filing | 1 | 1 | 0 |
| evidence_page_missed | 5 | 1 | 6 |
| partial_evidence | 5 | 0 | 0 |
| refused_with_evidence | 1 | 3 | 4 |
| wrong_number | 1 | 0 | 2 |
| wrong_conclusion | 0 | 0 | 1 |

## wrong_filing

- **financebench_id_00206**: Are JPM's gross margins historically consistent (not fluctuating more than roughly 2% each year)? If gross margins are not a relevant metric for a company like this, then please state that and explain why.
  - expert: Since JPM is a financial institution, gross margin is not a relevant metric.
  - model: Not enough information in the provided filings. The sources do not provide any direct information about JPMorgan's gross margins or their historical consistency. The filings mainly discuss asset and liability metrics, charge-offs, and other financial data, but do not include information on gross ma
- **financebench_id_00283**: How much does Pfizer expect to pay to spin off Upjohn in the future in USD million?
  - expert: About $70 million (roughly 10% of the expected $700 million is still to come).
  - model: Pfizer expects to incur costs of approximately $700 million in connection with separating Upjohn [S2]. This is the total expected cost for the spin-off, with approximately 75% of the costs already incurred as of December 31, 2021.

## evidence_page_missed

- **financebench_id_00080**: Does Paypal have positive working capital based on FY2022 data? If working capital is not a useful or relevant metric for this company, then please state that and explain why.
  - expert: Yes. Paypal has a positive working capital of $ 1.6Bn as of FY2022 end.
  - model: Not enough information in the provided filings. The sources do not provide specific financial statements or metrics such as current assets, current liabilities, or working capital for PayPal in FY2022. Therefore, it is not possible to determine if PayPal has positive working capital based on the gi
- **financebench_id_00302**: Did Pfizer grow its PPNE between FY20 and FY21?
  - expert: Yes, change in PPNE was positive year over year
  - model: Not enough information in the provided filings. The sources list various subsidiaries and do not provide financial data comparing Pfizer's PPNE (Pharmaceutical Product Net Earnings) between FY20 and FY21.
- **financebench_id_00723**: Does AMEX have an improving operating margin profile as of 2022? If operating margin is not a useful metric for a company like this, then state that and explain why.
  - expert: Performance is not measured through operating margin
  - model: Not enough information in the provided filings. The sources do not provide specific financial metrics such as operating margins for American Express in 2022 or comparative years. While the filings discuss pretax losses, operating expenses, and net income, they do not directly address operating marg

## partial_evidence

- **financebench_id_06741**: What is the FY2018 - FY2020 3 year average unadjusted EBITDA % margin for Walmart? Define unadjusted EBITDA as unadjusted operating income + depreciation and amortization from the cash flow statement. Answer in units of 
  - expert: 6.2%
  - model: Not enough information in the provided filings. The sources provided do not contain the necessary information to calculate the unadjusted EBITDA margin for Walmart for the fiscal years 2018-2020. Specifically, the operating income and depreciation and amortization values are not provided in the giv
- **financebench_id_03856**: What is the FY2017 operating cash flow ratio for Adobe? Operating cash flow ratio is defined as: cash from operations / total current liabilities. Round your answer to two decimal places. Please utilize information provi
  - expert: 0.83
  - model: The operating cash flow ratio for Adobe in FY2017 is calculated as follows: 1. Cash from operations (net cash provided by operating activities) for FY2017: $2,912,853,000 [S2] 2. Total current liabilities for FY2016: $3,028,100,000 [S2] Operating cash flow ratio = $2,912,853,000 / $3,028,100,000 =
- **financebench_id_04735**: You are an investment banker and your only resource(s) to answer the following question is (are): the statement of financial position and the cash flow statement. Here's the question: what is the FY2015 operating cash fl
  - expert: 0.66
  - model: The operating cash flow ratio for Adobe in FY2015 is 1.75, calculated as $1,469.5 million (cash from operations from [S2]) divided by $837.1 million (total current liabilities, derived from working capital of $2,608.3 million minus current assets excluding cash and cash equivalents of $2,131.2 milli

## refused_with_evidence

- **financebench_id_00566**: Has Verizon increased its debt on balance sheet between 2022 and the 2021 fiscal period?
  - expert: No. Verizon's debt decreased by $229 million.
  - model: Not enough information in the provided filings. The sources do not directly compare the total debt levels of Verizon between the 2022 and 2021 fiscal periods. [S2] mentions the total debt at December 31, 2021, but does not provide the 2022 figure.
- **financebench_id_01346**: How much has the effective tax rate of Corning changed between FY2021 and FY2022?
  - expert: The effective tax rate of Corning has changed from 20% in FY2021 to 23% in FY 2022.
  - model: The effective tax rate for Corning changed from 20.2% in 2021 [S2] to 22.9% in 2022 [S2]. Therefore, the effective tax rate increased by 2.7 percentage points between FY2021 and FY2022. Not enough information in the provided filings.
- **financebench_id_00394**: In 2022 Q2, which of JPM's business segments had the highest net income?
  - expert: Corporate & Investment Bank. Its net income was $3725 million.
  - model: To determine which of JPM's business segments had the highest net income in 2022 Q2, we need to look at the net income for each segment. From [S3], we can see the ROE (Return on Equity) for each segment: - CCB (Consumer and Community Banking) ROE: 24% - CIB (Commercial and Investment Banking) ROE:

## wrong_number

- **financebench_id_04254**: Basing your judgments off of the cash flow statement and the income statement, what is American Water Works's FY2021 unadjusted operating income + depreciation and amortization from the cash flow statement (unadjusted EB
  - expert: $1832.00
  - model: American Water Works's FY2021 unadjusted operating income + depreciation and amortization from the cash flow statement (unadjusted EBITDA) is $1,879 million. This is calculated by adding the operating income from the income statement ($1,196 million) to the depreciation and amortization from the cas
- **financebench_id_00299**: Which of JPM's business segments had the lowest net revenue in 2021 Q1?
  - expert: Corporate. Its net revenue was -$473 million.
  - model: The Asset & Wealth Management segment had the lowest net revenue in 2021 Q1, with $4,077 million [S1, S2].
- **financebench_id_03029**: What is the FY2018 capital expenditure amount (in USD millions) for 3M? Give a response to the question by relying on the details shown in the cash flow statement.
  - expert: $1577.00
  - model: The FY2018 capital expenditure amount for 3M is $994 million. This can be derived from the capital spending details provided in [S2], where it states "Capital Spending as of December 31, 2018 $ 994".

## wrong_conclusion

- **financebench_id_00724**: For Pfizer, which geographic region had the biggest drop in Q22023 year over year revenues (on a percentage basis)?
  - expert: Developed Rest of the World
  - model: The geographic region with the biggest drop in Q22023 year over year revenues (on a percentage basis) was Emerging Markets, with a 53% decrease, as reported in [S2].
