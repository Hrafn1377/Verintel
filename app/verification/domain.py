import whois
from datetime import datetime, timezone
from dateutil import parser as dateutil_parser
from scoring.models import ScoreSignal, Verdict


def check_domain(domain: str) -> ScoreSignal:
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
    parts = domain.split(".")
    if parts[0] in ("www", "careers", "jobs", "apply"):
        domain = ".".join(parts[1:])
    try:
        w = whois.whois(domain)

        creation_date = w.creation_date
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
        if isinstance(creation_date, str):
            creation_date = dateutil_parser.parse(creation_date)

        if creation_date is None:
            return ScoreSignal(
                label="Domain age",
                verdict=Verdict.FAIL,
                weight=0.3,
                score=0.0,
                reason="Domain has no creation date on record. This is a strong indicator of a fake or disposable domain.",
                source="WHOIS"
            )

        if creation_date.tzinfo is None:
            creation_date = creation_date.replace(tzinfo=timezone.utc)

        age_days = (datetime.now(timezone.utc) - creation_date).days

        if age_days < 30:
            return ScoreSignal(
                label="Domain age",
                verdict=Verdict.FAIL,
                weight=0.3,
                score=0.1,
                reason=f"Domain is only {age_days} days old. Legitimate companies rarely post jobs from brand new domains.",
                source="WHOIS"
            )

        if age_days < 180:
            return ScoreSignal(
                label="Domain age",
                verdict=Verdict.WARN,
                weight=0.3,
                score=0.5,
                reason=f"Domain is {age_days} days old. Still relatively new — worth checking other signals.",
                source="WHOIS"
            )

        return ScoreSignal(
            label="Domain age",
            verdict=Verdict.PASS,
            weight=0.3,
            score=1.0,
            reason=f"Domain has been registered for {age_days // 365} years. This is a good sign.",
            source="WHOIS"
        )

    except Exception as e:
        return ScoreSignal(
            label="Domain age",
            verdict=Verdict.WARN,
            weight=0.3,
            score=0.3,
            reason="Could not retrieve domain registration data. This may be due to WHOIS privacy protection.",
            source="WHOIS"
        )