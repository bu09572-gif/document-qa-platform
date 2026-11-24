# Failure analysis: qwen2.5:3b, retrieval `+query_expansion`, 50 golden questions

| Bucket | Count | Share | What would fix it |
|---|---|---|---|
| correct | 10 | 20% |  |
| wrong_filing | 14 | 28% | routing: company / year / quarter detection, or ask the user which filing |
| evidence_page_missed | 19 | 38% | ranking: better embeddings or reranker, table-aware chunks |
| partial_evidence | 2 | 4% | multi-page retrieval: one search per statement (income statement AND balance sheet) |
| refused_with_evidence | 2 | 4% | prompt / model: the context had the numbers; a bigger model or a 'find the line items first' step |
| wrong_number | 2 | 4% | reading tables: line-item extraction before arithmetic, use a calculator tool |
| wrong_conclusion | 1 | 2% | reasoning: bigger model, or domain hints (e.g. 'gross margin does not apply to banks') |

Retrieval failures: 35. Generation failures: 5.

| Bucket | calculation | judgment | lookup |
|---|---|---|---|
| correct | 4 | 1 | 5 |
| wrong_filing | 5 | 4 | 5 |
| evidence_page_missed | 8 | 1 | 10 |
| partial_evidence | 2 | 0 | 0 |
| refused_with_evidence | 0 | 0 | 2 |
| wrong_number | 1 | 0 | 1 |
| wrong_conclusion | 0 | 0 | 1 |

## wrong_filing

- **financebench_id_00723**: Does AMEX have an improving operating margin profile as of 2022? If operating margin is not a useful metric for a company like this, then state that and explain why.
  - expert: Performance is not measured through operating margin
  - model: Not enough information in the provided filings. The sources provided do not include any information about AES Corporation or AMEX.
- **financebench_id_07507**: What is Adobe's year-over-year change in unadjusted operating income from FY2015 to FY2016 (in units of percents and round to one decimal place)? Give a solution to the question by using the income statement.
  - expert: 65.4%
  - model: Not enough information in the provided filings.
- **financebench_id_00702**: Were there any potential events that are not in Pfizer's standard business operations that substantially increased net income in 2019?
  - expert: Yes, the gain on completion of Consumer Healthcare JV Transaction
  - model: Not enough information in the provided filings.

## evidence_page_missed

- **financebench_id_03029**: What is the FY2018 capital expenditure amount (in USD millions) for 3M? Give a response to the question by relying on the details shown in the cash flow statement.
  - expert: $1577.00
  - model: To find the FY2018 capital expenditure amount for 3M, we need to look at the investing activities section of the cash flow statement provided in [S2]. From [S2], we see: - Net cash provided by (used in) investing activities for 2018 is $222 million. The investing activities section also includes d
- **financebench_id_00517**: Are there any product categories / service categories that represent more than 20% of Boeing's revenue for FY2022?
  - expert: Yes. Boeing has product and service categories that represent more than 20% of Boeing's revenue for FY2022. These categories are Commercial Airplanes which comprises 39% of total revenue, Defence which comprises 35% of total revenue and Services which comprises 26% of total revenue.
  - model: Not enough information in the provided filings.
- **financebench_id_04700**: What is the FY2016 COGS for Microsoft? Please state answer in USD millions. Provide a response to the question by primarily using the statement of income.
  - expert: $32780.00
  - model: To calculate the FY2016 COGS for Microsoft, we need to look at the statement of income for the year. From [S1], we see that the cost of revenue increased $5.1 billion or 28%, driven by higher phones cost of revenue, as well as higher Xbox Live and search infrastructure costs, offset in part by a red

## partial_evidence

- **financebench_id_04735**: You are an investment banker and your only resource(s) to answer the following question is (are): the statement of financial position and the cash flow statement. Here's the question: what is the FY2015 operating cash fl
  - expert: 0.66
  - model: To calculate the FY2015 operating cash flow ratio for Adobe, we need to use the cash flows from operating activities provided in the 10K filing. [S2] provides the cash flows from operating activities for the fiscal years 2015, 2014, and 2013. The cash from operations for fiscal 2015 is $1,469,502,
- **financebench_id_03856**: What is the FY2017 operating cash flow ratio for Adobe? Operating cash flow ratio is defined as: cash from operations / total current liabilities. Round your answer to two decimal places. Please utilize information provi
  - expert: 0.83
  - model: To calculate the FY2017 operating cash flow ratio for Adobe, we need to determine the operating cash flow and the total current liabilities from the provided sources. From [S1] and [S2], we can find the operating cash flow for fiscal 2017: [Adobe | 10K 2017 | page 48] shows net cash provided by ope

## refused_with_evidence

- **financebench_id_01482**: At the Pepsico AGM held on May 3, 2023, what was the outcome of the shareholder vote on the shareholder proposal for a congruency report by Pepsico on net-zero emissions policies?
  - expert: The shareholder proposal for a congruency report by Pepsico on net-zero emissions policies was defeated.
  - model: [Not enough information in the provided filings.]
- **financebench_id_00746**: Which debt securities are registered to trade on a national securities exchange under Ulta Beauty's name as of FY2023?
  - expert: There are none
  - model: Not enough information in the provided filings.

## wrong_number

- **financebench_id_00460**: Was there any change in the number of Best Buy stores between Q2 of FY2024 and FY2023?
  - expert: Yes, there is decline in number stores by 1.32% from 982 stores in Q2 FY 2023 to 969 by the end of Q2 FY2024.
  - model: To determine if there was any change in the number of Best Buy stores between Q2 of FY2024 and FY2023, we need to look at the number of stores at the beginning and end of the second quarter for both fiscal years. From [S1], we see that at the end of the second quarter of fiscal 2024, the total numb
- **financebench_id_00566**: Has Verizon increased its debt on balance sheet between 2022 and the 2021 fiscal period?
  - expert: No. Verizon's debt decreased by $229 million.
  - model: To determine if Verizon increased its debt on balance sheet between 2022 and 2021, we need to compare the total debt outstanding at the end of each year. [S2] provides the total debt outstanding at the end of 2021 as $150.9 billion. [S3] provides the total debt outstanding at the end of 2022 as $178

## wrong_conclusion

- **financebench_id_01279**: Among operations, investing, and financing activities, which brought in the most (or lost the least) cash flow for AMD in FY22?
  - expert: In 2022, AMD brought in the most cashflow from Operations
  - model: For the fiscal year 2022, the cash flows from financing activities brought in the most cash, with a net cash provided of $2,300 million [S5]. The cash flows from investing activities lost the least cash, with a net cash provided of $1,999 million [S1]. Therefore, the answer is financing activities.
