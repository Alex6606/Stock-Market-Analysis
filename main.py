"""
main.py
-------
Punto de entrada del sistema de análisis de riesgo crediticio.

Uso:
    python main.py   #Interactivo, permite poner tickers manualmente, pero no da visualizaciones
    python main.py --tickers AAPL MSFT F  #Poner tickers directo en terminal, no da visualizaciones
    python main.py --tickers AAPL --charts #Lo anterior pero ahora si da visualizaciones
"""

import argparse
from risk_analyzer    import RiskAnalyzer
from report_generator import ReportGenerator


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sistema de Análisis de Riesgo Crediticio — Z-Score + Merton"
    )
    parser.add_argument(
        "--tickers", nargs="+", default=None,
        help="Ticker symbols a analizar (ej: AAPL MSFT F)"
    )
    parser.add_argument(
        "--charts", action="store_true",
        help="Generar visualizaciones con matplotlib"
    )
    parser.add_argument(
        "--save", action="store_true",
        help="Guardar gráficas como PNG en lugar de mostrarlas"
    )
    return parser.parse_args()


def get_tickers_interactively() -> list:
    print("\n" + "="*60)
    print("  SISTEMA DE ANÁLISIS DE RIESGO CREDITICIO")
    print("  Altman Z-Score + Modelo de Merton")
    print("="*60)
    print("\nIngresa los tickers a analizar (separados por espacios o comas).")
    print("Ejemplos: AAPL   |   AAPL, MSFT, F\n")
    raw = input("Tickers: ").strip()
    if not raw:
        raise ValueError("Debes ingresar al menos un ticker.")
    return [t.strip().upper() for t in raw.replace(",", " ").split() if t.strip()]


def main():
    args    = parse_args()
    tickers = args.tickers if args.tickers else get_tickers_interactively()

    print(f"\nAnalizando {len(tickers)} empresa(s): {', '.join(tickers)}")

    # Análisis
    results_list = (
        [RiskAnalyzer(tickers[0]).run()]
        if len(tickers) == 1
        else RiskAnalyzer.analyze_multiple(tickers)
    )

    # Reportes
    for result in results_list:
        report = ReportGenerator(result)
        report.generate_console()

        if args.charts:
            ticker    = result.get("ticker", "report")
            save_path = f"risk_chart_{ticker}.png" if args.save else None
            report.generate_charts(save_path=save_path)

    # Resumen comparativo (solo si hay más de una empresa)
    if len(results_list) > 1:
        print("\n" + "="*60)
        print("  RESUMEN COMPARATIVO")
        print("="*60)
        print(f"  {'Ticker':<10} {'Z-Score':<12} {'PD %':<12} {'Decisión Final'}")
        print(f"  {'─'*10} {'─'*12} {'─'*12} {'─'*22}")
        for r in results_list:
            if "error" in r:
                print(f"  {r['ticker']:<10} {'ERROR':<12} {'—':<12} {r['error'][:25]}")
                continue
            z   = r["zscore"]["ratios"]["z_score"]
            pd_ = r["merton"]["results"]["PD_pct"] if r["merton"]["applicable"] else "N/A"
            dec = r["final_decision"]["decision"]
            pd_str = f"{pd_:.4f}%" if isinstance(pd_, float) else pd_
            print(f"  {r['ticker']:<10} {z:<12.4f} {pd_str:<12} {dec}")
        print("="*60 + "\n")


if __name__ == "__main__":
    main()