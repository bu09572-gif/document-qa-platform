# Failure analysis: qwen2.5:3b, retrieval `+query_expansion`, 50 golden questions

| Bucket | Count | Share | What would fix it |
|---|---|---|---|
| correct | 10 | 20% |  |
| wrong_filing | 14 | 28% | routing: company / year / quarter detection, or ask the user which filing |
| evidence_page_missed | 18 | 36% | ranking: better embeddings or reranker, table-aware chunks |
| partial_evidence | 2 | 4% | multi-page retrieval: one search per statement (income statement AND balance sheet) |
| refused_with_evidence | 2 | 4% | prompt / model: the context had the numbers; a bigger model or a 'find the line items first' step |
| wrong_number | 2 | 4% | reading tables: line-item extraction before arithmetic, use a calculator tool |
| wrong_conclusion | 2 | 4% | reasoning: bigger model, or domain hints (e.g. 'gross margin does not apply to banks') |

Retrieval failures: 34. Generation failures: 6.

| Bucket | calculation | judgment | lookup |
|---|---|---|---|
| correct | 5 | 1 | 4 |
| wrong_filing | 5 | 4 | 5 |
| evidence_page_missed | 7 | 1 | 10 |
| partial_evidence | 2 | 0 | 0 |
| refused_with_evidence | 0 | 0 | 2 |
| wrong_number | 1 | 0 | 1 |
| wrong_conclusion | 0 | 0 | 2 |

## wrong_filing

- **financebench_id_00723**: Does AMEX have an improving operating margin profile as of 2022? If operating margin is not a useful metric for a company like this, then state that and explain why.
  - expert: Performance is not measured through operating margin
  - model: Not enough information in the provided filings. The sources do not include any information about AMEX or its financial metrics such as operating margin.
- **financebench_id_06272**: What is Coca Cola's FY2022 dividend payout ratio (using total cash dividends paid and net income attributable to shareholders)? Round answer to two decimal places. Answer the question asked by assuming you only have acce
  - expert: 0.8
  - model: Not enough information in the provided filings.
- **financebench_id_00206**: Are JPM's gross margins historically consistent (not fluctuating more than roughly 2% each year)? If gross margins are not a relevant metric for a company like this, then please state that and explain why.
  - expert: Since JPM is a financial institution, gross margin is not a relevant metric.
  - model: Not enough information in the provided filings. The sources provided do not include any information about JPMorgan's gross margins or if they are consistent over time. The sources are related to Walmart's financial performance and not JPMorgan's.

## evidence_page_missed

- **financebench_id_00080**: Does Paypal have positive working capital based on FY2022 data? If working capital is not a useful or relevant metric for this company, then please state that and explain why.
  - expert: Yes. Paypal has a positive working capital of $ 1.6Bn as of FY2022 end.
  - model: Not enough information in the provided filings. The sources do not contain specific information about PayPal's working capital for the fiscal year 2022. Working capital is not directly calculated from the provided sources, and the sources focus on various financial aspects such as deferred tax asset
- **financebench_id_00302**: Did Pfizer grow its PPNE between FY20 and FY21?
  - expert: Yes, change in PPNE was positive year over year
  - model: Not enough information in the provided filings.
- **financebench_id_00517**: Are there any product categories / service categories that represent more than 20% of Boeing's revenue for FY2022?
  - expert: Yes. Boeing has product and service categories that represent more than 20% of Boeing's revenue for FY2022. These categories are Commercial Airplanes which comprises 39% of total revenue, Defence which comprises 35% of total revenue and Services which comprises 26% of total revenue.
  - model: Not enough information in the provided filings.

## partial_evidence

- **financebench_id_03856**: What is the FY2017 operating cash flow ratio for Adobe? Operating cash flow ratio is defined as: cash from operations / total current liabilities. Round your answer to two decimal places. Please utilize information provi
  - expert: 0.83
  - model: To calculate the FY2017 operating cash flow ratio for Adobe, we need to determine the operating cash flow and the total current liabilities from the provided sources. From [S1] and [S2], we can find the operating cash flow for fiscal 2017: [Adobe | 10K 2017 | page 48] states: "Net cash provided by
- **financebench_id_04735**: You are an investment banker and your only resource(s) to answer the following question is (are): the statement of financial position and the cash flow statement. Here's the question: what is the FY2015 operating cash fl
  - expert: 0.66
  - model: To calculate the operating cash flow ratio for Adobe in fiscal year 2015, we need to use the information provided in the cash flow statement (S2). From S2, we find the net cash provided by operating activities for fiscal 2015 is $1,469,502,000. Next, we need to find total current liabilities. Thi

## refused_with_evidence

- **financebench_id_00746**: Which debt securities are registered to trade on a national securities exchange under Ulta Beauty's name as of FY2023?
  - expert: There are none
  - model: Not enough information in the provided filings.
- **financebench_id_01482**: At the Pepsico AGM held on May 3, 2023, what was the outcome of the shareholder vote on the shareholder proposal for a congruency report by Pepsico on net-zero emissions policies?
  - expert: The shareholder proposal for a congruency report by Pepsico on net-zero emissions policies was defeated.
  - model: [Not enough information in the provided filings.]

## wrong_number

- **financebench_id_04254**: Basing your judgments off of the cash flow statement and the income statement, what is American Water Works's FY2021 unadjusted operating income + depreciation and amortization from the cash flow statement (unadjusted EB
  - expert: $1832.00
  - model: To find American Water Works' FY2021 unadjusted operating income + depreciation and amortization from the cash flow statement (unadjusted EBITDA), we need to use the information from the provided sources. From [S1], we see the operating income and depreciation and amortization for the year 2021: Op
- **financebench_id_00460**: Was there any change in the number of Best Buy stores between Q2 of FY2024 and FY2023?
  - expert: Yes, there is decline in number stores by 1.32% from 982 stores in Q2 FY 2023 to 969 by the end of Q2 FY2024.
  - model: [Best Buy | 10Q 2024 | page 18] International segment stores open at the beginning and end of the second quarters of fiscal 2024 and fiscal 2023 were as follows: Fiscal 2024 Fiscal 2023 Total Stores at Beginning of Second Quarter Stores Opened Stores Closed Total Stores at End of Second Quarter Tota

## wrong_conclusion

- **financebench_id_01279**: Among operations, investing, and financing activities, which brought in the most (or lost the least) cash flow for AMD in FY22?
  - expert: In 2022, AMD brought in the most cashflow from Operations
  - model: To determine which of operations, investing, and financing activities brought in the most (or lost the least) cash flow for AMD in FY22, we need to analyze the cash flow statements provided in the sources. From [S1], we see that the cash flows for 2022 were: - Net cash provided by operating activit
- **financebench_id_01163**: Among operations, investing, and financing activities, which brought in the most (or lost the least) cash flow for Nike in FY2023?
  - expert: Among the three, cash flow from operations was the highest for Nike in FY2023.
  - model: To determine which operations brought in the most (or lost the least) cash flow for Nike in FY2023, we need to analyze the cash flow from investing, financing, and operations activities. From the provided sources: - [S1] provides the cash flow from investing and financing activities for FY2023. - [
