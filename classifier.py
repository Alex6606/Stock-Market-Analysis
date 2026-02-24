"""
classifier.py
-------------
Determina qué versión del Z-Score aplicar según el campo 'industry'
de yfinance (el SIC code no está disponible en yfinance 0.2.66).

Versiones del Z-Score según Altman:
  Z   — Manufactureras públicas        (industry contiene keywords de manufactura)
  Z'' — No manufactureras / financiero (resto)
  Z'  — Empresas privadas              (no aplica, todos los tickers son públicos)
"""


class CompanyClassifier:

    # Keywords que identifican industrias manufactureras
    MANUFACTURING_KEYWORDS = [
        "manufactur", "auto", "aerospace", "defense", "steel", "chemical",
        "semiconductor", "electronic", "machinery", "equipment", "textile",
        "paper", "packaging", "rubber", "plastic", "metal", "mining",
        "oil", "gas", "energy", "pharmaceutical", "drug", "food", "beverage",
        "tobacco", "furniture", "appliance", "vehicle", "aircraft", "ship",
    ]

    # Keywords que identifican sector financiero
    FINANCIAL_KEYWORDS = [
        "bank", "insurance", "financial", "asset management", "investment",
        "credit", "mortgage", "reit", "fund", "brokerage", "capital markets",
    ]

    def __init__(self, industry: str, total_liabilities: float = 0.0):
        self.industry          = (industry or "").lower()
        self.total_liabilities = total_liabilities
        self.company_type      = ""
        self.model_version     = ""

    def classify(self) -> str:
        if not self.industry:
            print("  [INFO] Industry no disponible. Usando Z'' por defecto.")
            self.company_type  = "non_manufacturing"
            self.model_version = "Z_double_prime"

        elif self._is_financial():
            self.company_type  = "financial"
            self.model_version = "Z_double_prime"
            print(
                f"  [AVISO] Sector financiero ('{self.industry}'). "
                f"Z-Score tiene interpretabilidad limitada. Se usará Z''."
            )

        elif self._is_manufacturing():
            self.company_type  = "manufacturing"
            self.model_version = "Z"

        else:
            self.company_type  = "non_manufacturing"
            self.model_version = "Z_double_prime"

        return self.company_type

    def get_model_version(self) -> str:
        return self.model_version

    def get_merton_applicability(self) -> bool:
        if self.total_liabilities <= 0:
            print("  [AVISO] Sin pasivos reportados. Merton no aplicable.")
            return False
        return True

    def _is_manufacturing(self) -> bool:
        return any(kw in self.industry for kw in self.MANUFACTURING_KEYWORDS)

    def _is_financial(self) -> bool:
        return any(kw in self.industry for kw in self.FINANCIAL_KEYWORDS)