import pandas as pd
from pdf_report import generate_llm_output

# Mock data
valuations = {'valuation_status': 'Undervalued', 'free_cash_flow': 5000000}
risks = ['High debt load', 'Regulatory uncertainty']
comparison = {
    'target': 'TEST',
    'annual': pd.DataFrame({
        'TEST': [0.12, 0.15, 0.08],
        'Peer1': [0.10, 0.14, 0.09],
        'Peer2': [0.11, 0.13, 0.07]
    }, index=['revenue_growth_yoy', 'ebit_margin', 'roe'])
}

print(generate_llm_output(valuations, risks, 'BUY', comparison))
