"""
decisions.py
------------
BaseCreditDecision, ZScoreDecision y MertonDecision.
Interpreta puntajes y emite decisiones crediticias.
"""


class BaseCreditDecision:

    APPROVED         = "APPROVED"
    APPROVED_WARNING = "APPROVED WITH WARNING"
    DENIED           = "DENIED"

    ZONE_SAFE     = "SAFE"
    ZONE_GREY     = "GREY ZONE"
    ZONE_DISTRESS = "DISTRESS"

    def __init__(self):
        self.zone      = ""
        self.decision  = ""
        self.reasoning = ""

    def evaluate(self) -> dict:
        raise NotImplementedError

    def get_summary(self) -> dict:
        if not self.decision:
            raise RuntimeError("Debe llamar a evaluate() primero.")
        return {
            "zone":      self.zone,
            "decision":  self.decision,
            "reasoning": self.reasoning,
        }


class ZScoreDecision(BaseCreditDecision):
    """
    Umbrales según Altman:
    Z  (manufactureras):     safe >2.99 | distress <1.81
    Z'' (no manufactureras): safe >2.60 | distress <1.10
    """

    THRESHOLDS = {
        "Z":             {"safe": 2.99, "distress": 1.81},
        "Z_double_prime":{"safe": 2.60, "distress": 1.10},
    }

    def __init__(self, z_score: float, model_version: str):
        super().__init__()
        self.z_score       = z_score
        self.model_version = model_version

    def evaluate(self) -> dict:
        t = self.THRESHOLDS.get(self.model_version, self.THRESHOLDS["Z_double_prime"])

        if self.z_score > t["safe"]:
            self.zone     = self.ZONE_SAFE
            self.decision = self.APPROVED
        elif self.z_score < t["distress"]:
            self.zone     = self.ZONE_DISTRESS
            self.decision = self.DENIED
        else:
            self.zone     = self.ZONE_GREY
            self.decision = self.APPROVED_WARNING

        label = "Z-Score" if self.model_version == "Z" else "Z''-Score"
        self.reasoning = (
            f"{label} = {self.z_score:.4f} | "
            f"Zona segura: >{t['safe']} | "
            f"Zona distress: <{t['distress']} | "
            f"Resultado: {self.zone}"
        )
        return self.get_summary()


class MertonDecision(BaseCreditDecision):
    """
    Umbrales sobre Probability of Default:
    PD < 2%  → SAFE
    2%-5%    → GREY ZONE
    PD > 5%  → DISTRESS
    """

    PD_SAFE     = 0.02
    PD_DISTRESS = 0.05

    def __init__(self, PD: float, DD: float):
        super().__init__()
        self.PD = PD
        self.DD = DD

    def evaluate(self) -> dict:
        if self.PD < self.PD_SAFE:
            self.zone     = self.ZONE_SAFE
            self.decision = self.APPROVED
        elif self.PD > self.PD_DISTRESS:
            self.zone     = self.ZONE_DISTRESS
            self.decision = self.DENIED
        else:
            self.zone     = self.ZONE_GREY
            self.decision = self.APPROVED_WARNING

        self.reasoning = (
            f"PD = {self.PD * 100:.4f}% | DD = {self.DD:.4f} | "
            f"Umbral seguro: <{self.PD_SAFE*100:.0f}% | "
            f"Umbral distress: >{self.PD_DISTRESS*100:.0f}% | "
            f"Resultado: {self.zone}"
        )
        return self.get_summary()