import pandas as pd
import valuation_engine
fcf = pd.Series([100, 110, 120, 130, 140])
print('DCF result:', valuation_engine.dcf_valuation(fcf))
