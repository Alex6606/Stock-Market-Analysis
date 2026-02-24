"""
report_generator.py
-------------------
Genera reportes en consola y visualizaciones con matplotlib.
"""
import matplotlib.pyplot as plt
from datetime import datetime


# Colores ANSI para consola
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"

DECISION_COLORS = {
    "APPROVED":              GREEN,
    "APPROVED WITH WARNING": YELLOW,
    "DENIED":                RED,
}


class ReportGenerator:

    def __init__(self, results: dict):
        self.results = results

    def generate_console(self) -> None:
        """Imprime el reporte completo en consola con colores."""
        r   = self.results
        sep = "─" * 60

        if "error" in r:
            print(f"\n{'!'*60}")
            print(f"  ERROR en {r['ticker']}: {r['error']}")
            print(f"{'!'*60}\n")
            return

        # Encabezado
        print(f"\n{'═'*60}")
        print(f"  REPORTE DE RIESGO CREDITICIO")
        print(f"  {r['company_name']} ({r['ticker']})")
        print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'═'*60}")
        print(f"\n  Tipo de empresa : {r['company_type']}")
        print(f"  Industry        : {r['industry']}")

        # Z-Score
        print(f"\n{sep}")
        print(f"  ALTMAN Z-SCORE  [{r['zscore']['model_version']}]")
        print(sep)
        rt = r["zscore"]["ratios"]
        print(f"  X1 (WC/TA)     : {rt['x1']:>10.4f}")
        print(f"  X2 (RE/TA)     : {rt['x2']:>10.4f}")
        print(f"  X3 (EBIT/TA)   : {rt['x3']:>10.4f}")
        print(f"  X4 (MVE/TL)    : {rt['x4']:>10.4f}")
        if rt["x5"] != 0.0:
            print(f"  X5 (S/TA)      : {rt['x5']:>10.4f}")
        print(f"  {'─'*35}")
        print(f"  Z-Score        : {rt['z_score']:>10.4f}")
        z_dec = r["zscore"]["decision"]
        color = DECISION_COLORS.get(z_dec["decision"], "")
        print(f"  Zona           : {z_dec['zone']}")
        print(f"  Decisión       : {color}{z_dec['decision']}{RESET}")
        print(f"  Detalle        : {z_dec['reasoning']}")

        # Merton
        print(f"\n{sep}")
        print(f"  MODELO DE MERTON")
        print(sep)
        if not r["merton"]["applicable"]:
            print("  No aplicable para esta empresa.")
        else:
            m = r["merton"]["results"]
            print(f"  V_A (activos)  : ${m['V_A']:>20,.0f}")
            print(f"  D   (pasivos)  : ${m['D']:>20,.0f}")
            print(f"  μ   (drift)    : {m['mu']:>10.4f}")
            print(f"  σ   (volat.)   : {m['sigma']:>10.4f}")
            print(f"  T   (años)     : {m['T']:>10.1f}")
            print(f"  {'─'*35}")
            print(f"  DD             : {m['DD']:>10.4f}")
            print(f"  PD             : {m['PD_pct']:>10.4f}%")
            m_dec = r["merton"]["decision"]
            color = DECISION_COLORS.get(m_dec["decision"], "")
            print(f"  Zona           : {m_dec['zone']}")
            print(f"  Decisión       : {color}{m_dec['decision']}{RESET}")
            print(f"  Detalle        : {m_dec['reasoning']}")

        # Decisión final
        print(f"\n{'═'*60}")
        print(f"  DECISIÓN FINAL DE CRÉDITO")
        print(f"{'═'*60}")
        fd    = r["final_decision"]
        color = DECISION_COLORS.get(fd["decision"], "")
        print(f"  Decisión : {color}{fd['decision']}{RESET}")
        print(f"  Basado en: {fd['basis']}")
        print(f"{'═'*60}\n")

    def generate_charts(self, save_path: str = None) -> None:
        """
        Genera visualizaciones con matplotlib:
        1. Gauge del Z-Score
        2. Tabla de ratios X1-X5
        3. Visualización de DD y PD (si Merton aplica)
        4. Panel de decisión final
        """
        try:
            import matplotlib.pyplot  as plt
            import matplotlib.patches as mpatches
            import numpy as np
        except ImportError:
            print("[CHARTS] matplotlib no instalado. Ejecuta: pip install matplotlib")
            return

        r = self.results
        if "error" in r:
            print(f"[CHARTS] No se pueden generar gráficas para {r['ticker']} (error en análisis).")
            return

        merton_ok = r["merton"]["applicable"] and r["merton"]["results"] is not None
        n_cols    = 2
        n_rows    = 3 if merton_ok else 2

        fig = plt.figure(figsize=(14, 5 * n_rows))
        fig.suptitle(
            f"Análisis de Riesgo Crediticio — {r['company_name']} ({r['ticker']})\n"
            f"{datetime.now().strftime('%Y-%m-%d')}",
            fontsize=14, fontweight="bold", y=0.98
        )

        # ── 1. Gauge Z-Score ──────────────────────────────────────────
        ax1 = fig.add_subplot(n_rows, n_cols, 1)
        self._plot_zscore_gauge(ax1, r)

        # ── 2. Tabla de ratios ────────────────────────────────────────
        ax2 = fig.add_subplot(n_rows, n_cols, 2)
        self._plot_ratios_table(ax2, r)

        if merton_ok:
            # ── 3. Visualización DD / PD ──────────────────────────────
            ax3 = fig.add_subplot(n_rows, n_cols, 3)
            self._plot_merton_normal(ax3, r)

            # ── 4. Tabla Merton ───────────────────────────────────────
            ax4 = fig.add_subplot(n_rows, n_cols, 4)
            self._plot_merton_table(ax4, r)

        # ── 5. Panel decisión final ───────────────────────────────────
        ax5 = fig.add_subplot(n_rows, n_cols, (n_cols * (n_rows - 1) + 1, n_cols * n_rows))
        self._plot_final_decision(ax5, r)

        plt.tight_layout(rect=[0, 0, 1, 0.96])

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"[CHARTS] Gráfica guardada: {save_path}")
        else:
            plt.show()

    # ── Subplots ───────────────────────────────────────────────────────

    def _plot_zscore_gauge(self, ax, r: dict) -> None:
        """Barra horizontal que muestra el Z-Score en su zona correspondiente."""
        import numpy as np
        import matplotlib.patches as mpatches

        mv     = r["zscore"]["model_version"]
        z      = r["zscore"]["ratios"]["z_score"]
        thresholds = {"Z": (1.81, 2.99), "Z_double_prime": (1.10, 2.60)}
        t_low, t_high = thresholds.get(mv, (1.10, 2.60))

        z_max  = max(z * 1.2, t_high * 1.5, 4.0)
        z_plot = min(z, z_max)

        # Zonas de color
        ax.barh(0, t_low,            left=0,       height=0.4, color="#e74c3c", alpha=0.3)
        ax.barh(0, t_high - t_low,   left=t_low,   height=0.4, color="#f39c12", alpha=0.3)
        ax.barh(0, z_max - t_high,   left=t_high,  height=0.4, color="#27ae60", alpha=0.3)

        # Marcador del Z-Score
        ax.barh(0, z_plot, left=0, height=0.15, color="#2c3e50", alpha=0.9)
        ax.axvline(x=z_plot, color="#2c3e50", linewidth=2)

        # Líneas de umbral
        ax.axvline(x=t_low,  color="#e74c3c", linewidth=1.5, linestyle="--", alpha=0.7)
        ax.axvline(x=t_high, color="#27ae60", linewidth=1.5, linestyle="--", alpha=0.7)

        ax.set_xlim(0, z_max)
        ax.set_yticks([])
        ax.set_xlabel("Z-Score")
        label = "Z-Score" if mv == "Z" else "Z''-Score"
        ax.set_title(f"{label} = {z:.4f}", fontweight="bold")

        # Leyenda
        patches = [
            mpatches.Patch(color="#e74c3c", alpha=0.5, label=f"Distress (<{t_low})"),
            mpatches.Patch(color="#f39c12", alpha=0.5, label=f"Zona gris"),
            mpatches.Patch(color="#27ae60", alpha=0.5, label=f"Seguro (>{t_high})"),
        ]
        ax.legend(handles=patches, loc="upper right", fontsize=8)
        ax.annotate(f"Z = {z:.2f}", xy=(z_plot, 0.08), fontsize=9,
                    ha="center", color="white", fontweight="bold")

    def _plot_ratios_table(self, ax, r: dict) -> None:
        """Tabla con los valores de X1-X5."""
        ax.axis("off")
        mv  = r["zscore"]["model_version"]
        rt  = r["zscore"]["ratios"]

        rows = [
            ["X1", "Working Capital / Total Assets",    f"{rt['x1']:.4f}"],
            ["X2", "Retained Earnings / Total Assets",  f"{rt['x2']:.4f}"],
            ["X3", "EBIT / Total Assets",               f"{rt['x3']:.4f}"],
            ["X4", "Market Cap / Total Liabilities",    f"{rt['x4']:.4f}"],
        ]
        if mv == "Z":
            rows.append(["X5", "Sales / Total Assets", f"{rt['x5']:.4f}"])

        col_labels = ["Variable", "Descripción", "Valor"]
        table = ax.table(
            cellText    = rows,
            colLabels   = col_labels,
            loc         = "center",
            cellLoc     = "left",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.6)

        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor("#2c3e50")
                cell.set_text_props(color="white", fontweight="bold")
            elif row % 2 == 0:
                cell.set_facecolor("#f5f5f5")

        ax.set_title("Ratios del Z-Score", fontweight="bold")

    def _plot_merton_normal(self, ax, r: dict) -> None:
        """Distribución normal estándar con DD marcado y área PD sombreada."""
        import numpy as np
        from math import erf, sqrt as msqrt

        m  = r["merton"]["results"]
        DD = m["DD"]
        PD = m["PD_pct"]

        x  = np.linspace(-4, 4, 400)
        y  = np.exp(-0.5 * x**2) / np.sqrt(2 * np.pi)

        ax.plot(x, y, color="#2c3e50", linewidth=2)

        # Área de default (izquierda de -DD)
        x_fill = np.linspace(-4, -DD, 200)
        y_fill = np.exp(-0.5 * x_fill**2) / np.sqrt(2 * np.pi)
        ax.fill_between(x_fill, y_fill, alpha=0.4,
                        color="#e74c3c", label=f"PD = {PD:.4f}%")

        ax.axvline(x=-DD, color="#e74c3c", linewidth=2,
                   linestyle="--", label=f"DD = {DD:.4f}")

        ax.set_xlabel("Desviaciones estándar")
        ax.set_ylabel("Densidad")
        ax.set_title("Distribución Normal — Merton", fontweight="bold")
        ax.legend(fontsize=8)
        ax.set_xlim(-4, 4)

    def _plot_merton_table(self, ax, r: dict) -> None:
        """Tabla con los parámetros del modelo de Merton."""
        ax.axis("off")
        m = r["merton"]["results"]

        rows = [
            ["V_A", f"${m['V_A']:,.0f}"],
            ["D",   f"${m['D']:,.0f}"],
            ["μ",   f"{m['mu']:.4f}"],
            ["σ",   f"{m['sigma']:.4f}"],
            ["T",   f"{m['T']:.1f} año"],
            ["DD",  f"{m['DD']:.4f}"],
            ["PD",  f"{m['PD_pct']:.4f}%"],
        ]
        table = ax.table(
            cellText  = rows,
            colLabels = ["Variable", "Valor"],
            loc       = "center",
            cellLoc   = "center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.6)

        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor("#16213e")
                cell.set_text_props(color="white", fontweight="bold")
            elif row % 2 == 0:
                cell.set_facecolor("#f5f5f5")

        ax.set_title("Parámetros Merton", fontweight="bold")

    def _plot_final_decision(self, ax, r: dict) -> None:
        """Panel central con la decisión final destacada."""
        ax.axis("off")
        fd       = r["final_decision"]
        decision = fd["decision"]

        color_map = {
            "APPROVED":              "#27ae60",
            "APPROVED WITH WARNING": "#f39c12",
            "DENIED":                "#e74c3c",
        }
        bg_color = color_map.get(decision, "#7f8c8d")

        ax.set_facecolor(bg_color)
        fig = ax.get_figure()
        fig_color = bg_color

        ax.text(
            0.5, 0.6, decision,
            transform=ax.transAxes,
            fontsize=22, fontweight="bold",
            ha="center", va="center", color="white"
        )
        ax.text(
            0.5, 0.35, f"Basado en: {fd['basis']}",
            transform=ax.transAxes,
            fontsize=9, ha="center", va="center", color="white"
        )
        ax.text(
            0.5, 0.15,
            f"Z-Score: {r['zscore']['ratios']['z_score']:.4f}  |  "
            f"Zona: {r['zscore']['decision']['zone']}",
            transform=ax.transAxes,
            fontsize=9, ha="center", va="center", color="white", alpha=0.85
        )

        rect = plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                              color=bg_color, zorder=-1)
        ax.add_patch(rect)
        ax.set_title("DECISIÓN FINAL DE CRÉDITO", fontweight="bold", fontsize=12)