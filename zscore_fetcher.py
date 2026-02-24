"""
zscore_fetcher.py
-----------------
Descarga datos financieros para el modelo Altman Z-Score.
Maneja campos faltantes en sectores financieros (bancos, aseguradoras).
"""

import yfinance as yf
from base_fetcher import BaseDataFetcher


class ZScoreDataFetcher(BaseDataFetcher):

    REQUIRED_FIELDS = [
        "total_assets", "ebit", "market_cap", "total_liabilities", "sales",
    ]

    def __init__(self, ticker: str):
        super().__init__(ticker)
        self.industry          = ""
        self.working_capital   = 0.0
        self.total_assets      = None
        self.retained_earnings = 0.0
        self.ebit              = None
        self.market_cap        = None
        self.total_liabilities = None
        self.sales             = None

    def fetch_all(self) -> dict:
        stock = yf.Ticker(self.ticker)
        self._fetch_company_info(stock)
        self._fetch_balance_sheet(stock)
        self._fetch_income_statement(stock)
        self._fetch_market_data(stock)

        data = {
            "working_capital":   self.working_capital,
            "total_assets":      self.total_assets,
            "retained_earnings": self.retained_earnings,
            "ebit":              self.ebit,
            "market_cap":        self.market_cap,
            "total_liabilities": self.total_liabilities,
            "sales":             self.sales,
        }
        self._validate_data(data, self.REQUIRED_FIELDS)
        return data

    def _fetch_company_info(self, stock):
        info = stock.info
        self.company_name = info.get("longName", self.ticker)
        self.industry     = info.get("industry", "")

    def _fetch_balance_sheet(self, stock):
        bs = stock.balance_sheet
        if bs is None or bs.empty:
            raise ValueError(f"[{self.ticker}] No se encontró balance sheet.")
        latest = bs.iloc[:, 0]

        self.total_assets      = float(latest["Total Assets"])
        self.total_liabilities = float(latest["Total Liabilities Net Minority Interest"])

        # Working Capital — no existe en bancos
        if "Working Capital" in latest.index:
            self.working_capital = float(latest["Working Capital"])
        elif "Current Assets" in latest.index and "Current Liabilities" in latest.index:
            self.working_capital = float(latest["Current Assets"]) - float(latest["Current Liabilities"])
            print(f"  [INFO] Working Capital aproximado (CA-CL): {self.working_capital:,.0f}")
        else:
            self.working_capital = 0.0
            print(f"  [AVISO] Working Capital no disponible para {self.ticker}. Usando 0.")

        # Retained Earnings — puede no existir en algunos sectores
        if "Retained Earnings" in latest.index:
            self.retained_earnings = float(latest["Retained Earnings"])
        else:
            self.retained_earnings = 0.0
            print(f"  [AVISO] Retained Earnings no disponible para {self.ticker}. Usando 0.")

    def _fetch_income_statement(self, stock):
        inc = stock.income_stmt
        if inc is None or inc.empty:
            raise ValueError(f"[{self.ticker}] No se encontró income statement.")
        latest = inc.iloc[:, 0]

        # EBIT — bancos no lo reportan, se usa Pretax Income como aproximación
        if "EBIT" in latest.index:
            self.ebit = float(latest["EBIT"])
        elif "Operating Income" in latest.index:
            self.ebit = float(latest["Operating Income"])
            print(f"  [INFO] EBIT aproximado con Operating Income.")
        elif "Pretax Income" in latest.index:
            self.ebit = float(latest["Pretax Income"])
            print(f"  [AVISO] EBIT no disponible. Usando Pretax Income como aproximación.")
        else:
            raise ValueError(f"[{self.ticker}] No se encontró EBIT ni alternativa válida.")

        # Sales
        if "Total Revenue" in latest.index:
            self.sales = float(latest["Total Revenue"])
        elif "Operating Revenue" in latest.index:
            self.sales = float(latest["Operating Revenue"])
            print(f"  [INFO] Sales tomado de Operating Revenue.")
        else:
            raise ValueError(f"[{self.ticker}] No se encontró Total Revenue.")

    def _fetch_market_data(self, stock):
        info = stock.info
        self.market_cap = float(info.get("marketCap"))