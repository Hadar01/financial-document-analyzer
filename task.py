## Importing libraries and files
from crewai import Task

from agents import financial_analyst, verifier, investment_advisor, risk_assessor
from tools import search_tool

## Creating a task to analyze financial documents
analyze_financial_document = Task(
    description="""Analyze the following financial document content for the query: {query}

=== DOCUMENT CONTENT START ===
{document_content}
=== DOCUMENT CONTENT END ===

Based on the document above:
- Extract key financial metrics including revenue, expenses, profitability ratios, liquidity ratios, and solvency indicators.
- Analyze financial trends over time and identify significant changes in financial position.
- Provide context on industry benchmarks and comparative analysis where relevant.
- Identify strengths and weaknesses in the company's financial performance.""",

    expected_output="""A detailed financial analysis report including:
- Executive summary of key financial metrics and trends
- Comprehensive breakdown of financial statements (Income Statement, Balance Sheet, Cash Flow)
- Calculation and interpretation of critical financial ratios
- Trend analysis identifying financial trajectory and changes
- Industry comparison and competitive positioning
- Key insights and observations with supporting data
- Specific citations from the financial document for all claims""",

    agent=financial_analyst,
    tools=[search_tool],
    async_execution=False,
)

## Creating a comprehensive investment analysis task
investment_analysis = Task(
    description="""Based on the following financial document content and the user's query ({query}), develop comprehensive investment recommendations.

=== DOCUMENT CONTENT START ===
{document_content}
=== DOCUMENT CONTENT END ===

Based on the document above:
- Evaluate the company's financial health, growth prospects, and competitive positioning.
- Assess the quality of earnings and sustainability of profitability.
- Consider the company's capital allocation, dividend policy, and cash flow generation.
- Identify key risk factors and catalysts affecting future performance.
- Provide specific, data-backed investment recommendations.""",

    expected_output="""A professional investment recommendation report including:
- Investment thesis with clear rationale backed by financial data
- Valuation assessment using multiple methodologies (P/E, DCF, comparables)
- Risks and opportunities specific to the investment
- Industry and macroeconomic considerations
- Specific investment recommendations (Buy/Hold/Sell) with price targets if applicable
- Portfolio allocation recommendations based on risk profile
- Timeline for investment review and reassessment
- Clear disclaimers about investment risk and suitability""",

    agent=investment_advisor,
    tools=[search_tool],
    async_execution=False,
)

## Creating a comprehensive risk assessment task
risk_assessment = Task(
    description="""Conduct a thorough risk assessment based on the following financial document for: {query}

=== DOCUMENT CONTENT START ===
{document_content}
=== DOCUMENT CONTENT END ===

Based on the document above:
- Identify financial risks including liquidity risk, credit risk, and solvency risk.
- Evaluate operational risks inherent in the business model and industry.
- Assess market and strategic risks affecting the company's position.
- Analyze regulatory and compliance risks relevant to the industry.
- Develop risk mitigation strategies and monitoring frameworks.""",

    expected_output="""A comprehensive risk assessment report including:
- Detailed identification and quantification of key financial risks
- Assessment of cash flow adequacy and liquidity position
- Credit risk evaluation and default probability assessment
- Operational risk factors affecting business stability
- Market and industry-specific risk analysis
- Geopolitical and macroeconomic risk considerations
- Risk mitigation strategies and contingency plans
- Risk monitoring metrics and reporting framework
- Risk prioritization matrix with severity and likelihood assessment""",

    agent=risk_assessor,
    tools=[search_tool],
    async_execution=False,
)

## Creating a document verification task
verification = Task(
    description="""Verify the authenticity and validity of the following financial document for the query: {query}

=== DOCUMENT CONTENT START ===
{document_content}
=== DOCUMENT CONTENT END ===

Based on the document above:
- Confirm that the document contains legitimate financial statements and data.
- Validate the document completeness and identify any missing critical components.
- Verify the time period and currency of the financial data.
- Check for signs of data integrity and proper financial statement structure.
- Assess whether the document is suitable for the analysis requested.""",

    expected_output="""A verification report confirming:
- Authenticity of the financial document with specific evidence
- Completeness assessment of financial statements (Income Statement, Balance Sheet, Cash Flow)
- Identification of the reporting period and currency
- Document quality and readability assessment
- Any data quality issues or concerns identified
- Confirmation of whether the document is suitable for requested analysis
- Recommendations for additional information or documents if needed""",

    agent=verifier,
    async_execution=False
)