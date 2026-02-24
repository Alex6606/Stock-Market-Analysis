"""
merton_fetcher.py
-----------------
Descarga datos para el modelo de Merton usando enfoque balance sheet.

V_A = Total Assets (valor actual, año más reciente)
D   = Total Liabilities (año más reciente)
μ   = media(ΔV_A/V_A) sobre serie histórica — drift real de activos
σ_A = std(ΔV_A/V_A) sobre serie histórica — volatilidad real de activos
r   = 10Y Treasury yield
T   = 1 año
"""

import warnings
import numpy as np
import yfinance as yf
from base_fetcher import BaseDataFetcher


class MertonDataFetcher(BaseDataFetcher):

    MIN_YEARS_WARNING = 3
    MIN_YEARS_ERROR   = 2

    def __init__(self, ticker: str):
        super().__init__(ticker)
        self.V_A              = 0.0
        self.D                = 0.0
        self.mu               = 0.0
        self.sigma            = 0.0
        self.risk_free_rate   = 0.0
        self.T                = 1.0
        self.n_years_used     = 0
        self.assets_history   = []

    def fetch_all(self) -> dict:
        stock = yf.Ticker(self.ticker)
        self._fetch_company_info(stock)
        self._fetch_historical_balance(stock)
        self._calculate_mu_and_sigma()
        self._fetch_risk_free_rate()

        data = {
            "V_A":            self.V_A,
            "D":              self.D,
            "mu":             self.mu,
            "sigma":          self.sigma,
            "risk_free_rate": self.risk_free_rate,
            "T":              self.T,
        }
        self._validate_data(data, list(data.keys()))
        return data

    def _fetch_company_info(self, stock):
        info = stock.info
        self.company_name = info.get("longName", self.ticker)
        self.sic_code     = int(info.get("sic", -1)) if info.get("sic") else -1

    def _fetch_historical_balance(self, stock):
        bs = stock.balance_sheet
        if bs is None or bs.empty:
            raise ValueError(f"[{self.ticker}] No se encontró balance sheet.")

        assets_series = bs.loc["Total Assets"].dropna().sort_index()
        liab_series   = bs.loc["Total Liabilities Net Minority Interest"].dropna().sort_index()

        self.assets_history = [float(v) for v in assets_series.values]
        self.n_years_used   = len(self.assets_history)

        if self.n_years_used < self.MIN_YEARS_ERROR:
            raise ValueError(
                f"[{self.ticker}] Solo {self.n_years_used} años disponibles. "
                f"Mínimo requerido: {self.MIN_YEARS_ERROR}."
            )

        if self.n_years_used < self.MIN_YEARS_WARNING:
            warnings.warn(
                f"[{self.ticker}] Solo {self.n_years_used} años. "
                f"Estimación de μ y σ puede no ser robusta.",
                UserWarning
            )

        self.V_A = self.assets_history[-1]
        self.D   = float(liab_series.values[-1])

    def _calculate_mu_and_sigma(self):
        """
        Calcula drift (μ) y volatilidad (σ) de los activos.
        ΔV_A/V_A = (V_t - V_t-1) / V_t-1
        μ = media de las variaciones anuales
        σ = desviación estándar de las variaciones anuales
        """
        assets      = self.assets_history
        pct_changes = []

        for i in range(1, len(assets)):
            prev = assets[i - 1]
            curr = assets[i]
            if prev == 0:
                continue
            pct_changes.append((curr - prev) / abs(prev))

        if len(pct_changes) < 1:
            raise ValueError("No hay suficientes variaciones para calcular μ y σ.")

        self.mu    = float(np.mean(pct_changes))
        self.sigma = float(np.std(pct_changes, ddof=1)) if len(pct_changes) > 1 else abs(pct_changes[0])

    def _fetch_risk_free_rate(self):
        try:
            tnx  = yf.Ticker("^TNX")
            info = tnx.info
            rate = info.get("regularMarketPrice") or info.get("previousClose")
            if rate:
                self.risk_free_rate = float(rate) / 100.0
            else:
                raise ValueError("^TNX no retornó precio.")
        except Exception:
            warnings.warn(
                "No se pudo obtener tasa libre de riesgo de ^TNX. Usando r = 4.0%.",
                UserWarning
            )
            self.risk_free_rate = 0.04