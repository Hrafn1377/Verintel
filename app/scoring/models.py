from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class ScoreSignal:
    label: str
    verdict: Verdict
    weight: float
    score: float
    reason: str
    source: str


@dataclass
class TrustReport:
    entity_id: str
    entity_type: str
    overall_score: float = 0.0
    signals: list[ScoreSignal] = field(default_factory=list)
    summary: str = ""

    def compute(self):
        if not self.signals:
            return self
        total_weight = sum(s.weight for s in self.signals)
        if total_weight == 0:
            return self
        self.overall_score = sum(
        s.score * (s.weight / total_weight) for s in self.signals
    )
        return self