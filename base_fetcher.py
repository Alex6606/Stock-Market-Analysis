"""
base_fetcher.py
---------------
Clase base abstracta para todos los fetchers de datos financieros.
"""


class BaseDataFetcher:

    def __init__(self, ticker: str):
        self.ticker       = ticker.upper().strip()
        self.company_name = ""
        self.sic_code     = -1

    def fetch_all(self) -> dict:
        raise NotImplementedError("Las subclases deben implementar fetch_all().")

    def _validate_data(self, data: dict, required_fields: list) -> None:
        missing = [f for f in required_fields if data.get(f) is None]
        if missing:
            raise ValueError(
                f"[{self.ticker}] Campos faltantes: {missing}. "
                f"Verifique que el ticker sea correcto y tenga estados financieros disponibles."
            )