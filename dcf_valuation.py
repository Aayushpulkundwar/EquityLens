'''dcf_valuation.py

Utility module for discounted cash flow (DCF) valuation with robust handling of currency, growth rates, and sanity checks.

The module provides:
- `get_currency(ticker_symbol)`: Detects currency using yfinance and ticker suffix rules.
- `normalize_growth(growth)`: Caps growth between 5% and 12%.
- `compute_dcf(fcf, growth_rate, discount_rate, terminal_growth, years, shares)`: Core DCF calculation.
- `validate_dcf(intrinsic_value, market_price)`: Flags unrealistic valuations.
- `valuation_engine(ticker_symbol, fcf, market_price, shares, discount_rate=0.09, terminal_growth=0.025, years=5)`: End‑to‑end workflow.

All monetary values are assumed to be in the same currency as the ticker. A mismatch raises a `ValueError`.
''' 
import logging
from typing import Tuple
import yfinance as yf

# Configure logger – inherit the global logger configuration if desired
logger = logging.getLogger(__name__)


def get_currency(ticker_symbol: str) -> str:
    """Return the currency for a ticker.

    Rules:
    - If the ticker ends with ``.NS`` or ``.NSE`` or ``NS`` or ``NSE`` → ``"USD"``
    - If the ticker ends with ``.BO`` → ``"INR"``
    - Otherwise, fetch ``info["currency"]`` from yfinance.
    """
    ticker_symbol = ticker_symbol.strip().upper()
    if ticker_symbol.endswith('.NS') or ticker_symbol.endswith('.NSE') or ticker_symbol.endswith('NS') or ticker_symbol.endswith('NSE'):
        return 'USD'
    if ticker_symbol.endswith('.BO'):
        return 'INR'
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info or {}
        currency = info.get('currency')
        if not currency:
            raise ValueError(f"Currency not found for ticker {ticker_symbol}")
        return currency.upper()
    except Exception as exc:
        logger.error(f"Failed to retrieve currency for {ticker_symbol}: {exc}")
        raise


def normalize_growth(growth: float) -> float:
    """Clamp ``growth`` to a realistic range.

    The function enforces a minimum of 5 % and a maximum of 12 %.
    """
    return max(0.05, min(growth, 0.12))


def compute_dcf(
    fcf: float,
    growth_rate: float,
    discount_rate: float,
    terminal_growth: float,
    years: int,
    shares: int,
) -> float:
    """Calculate the intrinsic per‑share value using a standard DCF model.

    Parameters
    ----------
    fcf: float
        Current free cash flow (in the ticker's currency).
    growth_rate: float
        Expected annual growth rate (already normalised).
    discount_rate: float
        Discount rate (WACC), e.g., 0.08‑0.10.
    terminal_growth: float
        Long‑term terminal growth rate, e.g., 0.02‑0.03.
    years: int
        Projection horizon (commonly 5‑10 years).
    shares: int
        Number of outstanding shares.
    """
    if shares <= 0:
        raise ValueError("Shares must be a positive integer")
    # Project future free cash flows
    future_fcfs = [fcf * ((1 + growth_rate) ** t) for t in range(1, years + 1)]
    # Discount each projected cash flow
    discounted_fcfs = [future_fcfs[t - 1] / ((1 + discount_rate) ** t) for t in range(1, years + 1)]
    # Terminal value based on the last projected cash flow
    terminal_value = (future_fcfs[-1] * (1 + terminal_growth)) / (discount_rate - terminal_growth)
    discounted_terminal = terminal_value / ((1 + discount_rate) ** years)
    total_value = sum(discounted_fcfs) + discounted_terminal
    intrinsic_per_share = total_value / shares
    return intrinsic_per_share


def validate_dcf(intrinsic_value: float, market_price: float) -> Tuple[bool, str]:
    """Sanity‑check the DCF output.

    Returns a tuple ``(is_valid, flag)`` where ``flag`` describes the issue
    (if any). ``is_valid`` is ``False`` when the intrinsic value is negative.
    """
    if intrinsic_value < 0:
        raise ValueError("Invalid DCF output: intrinsic value is negative")
    if intrinsic_value > 5 * market_price:
        return False, "DCF too high"
    if intrinsic_value < 0.3 * market_price:
        return False, "DCF too low"
    return True, "DCF within reasonable bounds"


def valuation_engine(
    ticker_symbol: str,
    fcf: float,
    market_price: float,
    shares: int,
    growth_rate: float,
    discount_rate: float = 0.09,
    terminal_growth: float = 0.025,
    years: int = 5,
) -> dict:
    """End‑to‑end DCF valuation for a given ticker.

    This function wires together currency detection, growth normalisation,
    DCF computation and sanity checks. All monetary values must be expressed
    in the ticker's native currency – the function validates this.
    """
    # Detect currency and ensure all inputs are consistent (user must provide values in that currency)
    currency = get_currency(ticker_symbol)
    logger.info(f"Ticker {ticker_symbol} detected currency: {currency}")

    # Normalise growth
    growth = normalize_growth(growth_rate)
    logger.info(f"Normalized growth rate: {growth:.2%}")

    # Compute intrinsic value
    intrinsic = compute_dcf(
        fcf=fcf,
        growth_rate=growth,
        discount_rate=discount_rate,
        terminal_growth=terminal_growth,
        years=years,
        shares=shares,
    )
    logger.info(f"Intrinsic value per share ({currency}): {intrinsic:,.2f}")

    # Sanity check against market price
    is_valid, flag = validate_dcf(intrinsic, market_price)
    logger.info(f"DCF sanity check – valid: {is_valid}, flag: {flag}")

    return {
        "ticker": ticker_symbol,
        "currency": currency,
        "intrinsic_value": intrinsic,
        "market_price": market_price,
        "sanity_flag": flag,
        "is_valid": is_valid,
    }

# Example usage (remove or guard with if __name__ == "__main__" in production)
if __name__ == "__main__":
    # Dummy values for demonstration – replace with real data.
    example = valuation_engine(
        ticker_symbol="CIPLA.NS",
        fcf=8_607_100_000,  # example free cash flow (INR)
        market_price=1_200,   # example market price per share (INR)
        shares=1_500_000_000,  # outstanding shares
        growth_rate=0.08,  # raw growth estimate
    )
    print(example)
