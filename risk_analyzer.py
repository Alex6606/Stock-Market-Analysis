"""
risk_analyzer.py
----------------
Orquestador del sistema. Único punto de entrada para el usuario.
Coordina fetchers, classifier, calculators y decisions.
"""

from zscore_fetcher  import ZScoreDataFetcher
from merton_fetcher  import MertonDataFetcher
from classifier      import CompanyClassifier
from calculators     import ZScoreCalculator, MertonCalculator
from decisions       import ZScoreDecision, MertonDecision


class RiskAnalyzer:

    def __init__(self, ticker: str):
        self.ticker  = ticker.upper().strip()
        self.results = {}

    def run(self) -> dict:
        print(f"\n{'='*60}")
        print(f"  Analizando: {self.ticker}")
        print(f"{'='*60}")

        # ── PASO 1: Datos Z-Score ─────────────────────────────────────
        print("\n[1/5] Descargando datos financieros (Z-Score)...")
        z_fetcher = ZScoreDataFetcher(self.ticker)
        z_data    = z_fetcher.fetch_all()
        print(f"      Empresa : {z_fetcher.company_name}")
        print(f"      Industry: {z_fetcher.industry}")

        # ── PASO 2: Clasificación ─────────────────────────────────────
        print("\n[2/5] Clasificando empresa...")
        classifier = CompanyClassifier(
            industry          = z_fetcher.industry,
            total_liabilities = z_data["total_liabilities"],
        )
        company_type  = classifier.classify()
        model_version = classifier.get_model_version()
        print(f"      Tipo    : {company_type}")
        print(f"      Modelo  : {model_version}")

        # ── PASO 3: Z-Score ───────────────────────────────────────────
        print("\n[3/5] Calculando Z-Score...")
        z_calc    = ZScoreCalculator(z_data, model_version)
        z_results = z_calc.calculate()
        print(f"      Z-Score : {z_results['z_score']}")

        z_dec_obj = ZScoreDecision(z_results["z_score"], model_version)
        z_dec     = z_dec_obj.evaluate()
        print(f"      Decisión: {z_dec['decision']} ({z_dec['zone']})")

        # ── PASO 4: Datos Merton ──────────────────────────────────────
        merton_applicable = classifier.get_merton_applicability()
        merton_results    = None
        merton_dec        = None

        if merton_applicable:
            print("\n[4/5] Descargando datos financieros (Merton)...")
            m_fetcher = MertonDataFetcher(self.ticker)
            m_data    = m_fetcher.fetch_all()
            print(f"      Años usados : {m_fetcher.n_years_used}")
            print(f"      μ  (drift)  : {m_data['mu']:.4f}")
            print(f"      σ  (volat.) : {m_data['sigma']:.4f}")
            print(f"      r           : {m_data['risk_free_rate']:.4f}")

            # ── PASO 5: Merton ────────────────────────────────────────
            print("\n[5/5] Calculando modelo de Merton...")
            m_calc         = MertonCalculator(m_data)
            merton_results = m_calc.calculate()
            print(f"      DD          : {merton_results['DD']:.4f}")
            print(f"      PD          : {merton_results['PD_pct']:.4f}%")

            m_dec_obj  = MertonDecision(merton_results["PD"], merton_results["DD"])
            merton_dec = m_dec_obj.evaluate()
            print(f"      Decisión    : {merton_dec['decision']} ({merton_dec['zone']})")
        else:
            print("\n[4/5] Merton no aplicable.")
            print("[5/5] Saltando cálculo de Merton.")

        # ── CONSOLIDAR ────────────────────────────────────────────────
        self.results = {
            "ticker":       self.ticker,
            "company_name": z_fetcher.company_name,
            "industry":     z_fetcher.industry,
            "company_type": company_type,
            "zscore": {
                "model_version": model_version,
                "ratios":        z_results,
                "decision":      z_dec,
            },
            "merton": {
                "applicable": merton_applicable,
                "results":    merton_results,
                "decision":   merton_dec,
            },
            "final_decision": self._combine_decisions(z_dec, merton_dec),
        }
        return self.results

    def get_results(self) -> dict:
        if not self.results:
            raise RuntimeError("Debe llamar a run() primero.")
        return self.results

    @staticmethod
    def analyze_multiple(tickers: list) -> list:
        """Analiza varios tickers en secuencia. Captura errores individuales."""
        all_results = []
        for ticker in tickers:
            try:
                analyzer = RiskAnalyzer(ticker)
                all_results.append(analyzer.run())
            except Exception as e:
                print(f"\n  [ERROR] No se pudo analizar {ticker}: {e}")
                all_results.append({"ticker": ticker, "error": str(e)})
        return all_results

    def _combine_decisions(self, z_dec: dict, merton_dec: dict) -> dict:
        """
        Decisión final conservadora:
        - Cualquier DENIED → DENIED
        - Ambos APPROVED   → APPROVED
        - Resto            → APPROVED WITH WARNING
        """
        if merton_dec is None:
            return {
                "decision": z_dec["decision"],
                "basis":    "Z-Score únicamente (Merton no aplicable)",
            }

        decisions = {z_dec["decision"], merton_dec["decision"]}

        if "DENIED" in decisions:
            final = "DENIED"
        elif decisions == {"APPROVED"}:
            final = "APPROVED"
        else:
            final = "APPROVED WITH WARNING"

        return {
            "decision": final,
            "basis":    f"Z-Score: {z_dec['decision']} | Merton: {merton_dec['decision']}",
        }