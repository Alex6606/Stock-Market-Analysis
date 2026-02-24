"""
calculators.py
--------------
BaseCalculator, ZScoreCalculator y MertonCalculator.
Toda la aritmética de los modelos vive aquí.
"""

from math import log, sqrt, erf


class BaseCalculator:

    def __init__(self, data: dict):
        self.data   = data
        self.result = {}

    def calculate(self) -> dict:
        raise NotImplementedError

    def get_results(self) -> dict:
        if not self.result:
            raise RuntimeError("Debe llamar a calculate() primero.")
        return self.result


# ══════════════════════════════════════════════════════════════════════
# Z-Score Calculator
# ══════════════════════════════════════════════════════════════════════

class ZScoreCalculator(BaseCalculator):
    """
    Altman Z-Score en dos versiones:

    Z  (manufactureras públicas):
        Z = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5

    Z'' (no manufactureras):
        Z'' = 6.56·X1 + 3.26·X2 + 6.72·X3 + 1.05·X4

    X1 = Working Capital / Total Assets
    X2 = Retained Earnings / Total Assets
    X3 = EBIT / Total Assets
    X4 = Market Cap / Total Liabilities
    X5 = Sales / Total Assets  (solo en Z)
    """

    COEFFICIENTS = {
        "Z": {
            "x1": 1.2, "x2": 1.4, "x3": 3.3, "x4": 0.6, "x5": 1.0
        },
        "Z_double_prime": {
            "x1": 6.56, "x2": 3.26, "x3": 6.72, "x4": 1.05, "x5": 0.0
        },
    }

    def __init__(self, data: dict, model_version: str):
        super().__init__(data)
        if model_version not in self.COEFFICIENTS:
            raise ValueError(f"Versión inválida: '{model_version}'.")
        self.model_version = model_version
        self.coefficients  = self.COEFFICIENTS[model_version]
        self.x1 = self.x2 = self.x3 = self.x4 = self.x5 = 0.0
        self.z_score = 0.0

    def calculate(self) -> dict:
        ta = self.data["total_assets"]
        tl = self.data["total_liabilities"]

        if ta == 0:
            raise ZeroDivisionError("Total Assets es 0.")
        if tl == 0:
            raise ZeroDivisionError("Total Liabilities es 0.")

        self.x1 = self.data["working_capital"]   / ta
        self.x2 = self.data["retained_earnings"] / ta
        self.x3 = self.data["ebit"]              / ta
        self.x4 = self.data["market_cap"]        / tl
        self.x5 = self.data["sales"] / ta if self.model_version == "Z" else 0.0

        c = self.coefficients
        self.z_score = (
            c["x1"] * self.x1 +
            c["x2"] * self.x2 +
            c["x3"] * self.x3 +
            c["x4"] * self.x4 +
            c["x5"] * self.x5
        )

        self.result = {
            "model_version": self.model_version,
            "x1": round(self.x1, 4),
            "x2": round(self.x2, 4),
            "x3": round(self.x3, 4),
            "x4": round(self.x4, 4),
            "x5": round(self.x5, 4),
            "z_score": round(self.z_score, 4),
        }
        return self.result


# ══════════════════════════════════════════════════════════════════════
# Merton Calculator
# ══════════════════════════════════════════════════════════════════════

class MertonCalculator(BaseCalculator):
    """
    Modelo de Merton — versión balance sheet:

    DD = [ln(V_A/D) + (μ - σ²/2)·T] / (σ·√T)
    PD = 1 - N(DD)

    V_A = Total Assets (más reciente)
    D   = Total Liabilities (más reciente)
    μ   = drift real de activos (media variaciones anuales)
    σ   = volatilidad real de activos (std variaciones anuales)
    T   = 1 año
    """

    def __init__(self, data: dict):
        super().__init__(data)
        self.DD = 0.0
        self.PD = 0.0

    def calculate(self) -> dict:
        V_A   = self.data["V_A"]
        D     = self.data["D"]
        mu    = self.data["mu"]
        sigma = self.data["sigma"]
        T     = self.data["T"]

        if D <= 0:
            raise ValueError("D (pasivos) debe ser mayor que 0.")
        if V_A <= 0:
            raise ValueError("V_A (activos) debe ser mayor que 0.")
        if sigma <= 0:
            raise ValueError("σ debe ser mayor que 0.")

        self.DD = (log(V_A / D) + (mu - (sigma ** 2) / 2) * T) / (sigma * sqrt(T))
        self.PD = 1.0 - self._normal_cdf(self.DD)

        self.result = {
            "V_A":    round(V_A, 2),
            "D":      round(D, 2),
            "mu":     round(mu, 4),
            "sigma":  round(sigma, 4),
            "T":      T,
            "DD":     round(self.DD, 4),
            "PD":     round(self.PD, 6),
            "PD_pct": round(self.PD * 100, 4),
        }
        return self.result

    @staticmethod
    def _normal_cdf(x: float) -> float:
        """CDF normal estándar usando erf de math (sin scipy)."""
        return (1.0 + erf(x / sqrt(2.0))) / 2.0