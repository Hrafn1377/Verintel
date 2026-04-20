import httpx
from scoring.models import ScoreSignal, Verdict

JURISDICTION_MAP = {
    "us": "us_de",
    "gb": "gb",
    "ca": "ca",
    "au": "au",
    "ie": "ie",
    "de": "de",
    "fr": "fr",
}

OPENCORPORATES_BASE = "https://api.opencorporates.com/v0.4"


async def check_opencorporates(company_name: str, jurisdiction: str = "us") -> ScoreSignal:
    try:
        resolved = JURISDICTION_MAP.get(jurisdiction.lower(), jurisdiction)
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{OPENCORPORATES_BASE}/companies/search",
                params={
                    "q": company_name,
                    "jurisdiction_code": resolved,
                    "inactive": "false",
                }
            )
            data = r.json()
            companies = data.get("results", {}).get("companies", [])

            if not companies:
                return ScoreSignal(
                    label="Business registry",
                    verdict=Verdict.FAIL,
                    weight=0.4,
                    score=0.0,
                    reason=f"No active company named '{company_name}' found in the {jurisdiction.upper()} business registry. Large companies may be registered under a parent company name or in a different jurisdiction. Check the spelling or try searching for the parent company.",
                    source="OpenCorporates"
                )

            top = companies[0].get("company", {})
            status = top.get("current_status", "").lower()

            if "dissolved" in status or "inactive" in status:
                return ScoreSignal(
                    label="Business registry",
                    verdict=Verdict.FAIL,
                    weight=0.4,
                    score=0.1,
                    reason=f"A company named '{company_name}' exists in the registry but is dissolved or inactive. This is a strong red flag.",
                    source="OpenCorporates"
                )

            return ScoreSignal(
                label="Business registry",
                verdict=Verdict.PASS,
                weight=0.4,
                score=1.0,
                reason=f"'{company_name}' is registered and active in the {jurisdiction.upper()} business registry.",
                source="OpenCorporates"
            )

    except Exception:
        return ScoreSignal(
            label="Business registry",
            verdict=Verdict.WARN,
            weight=0.4,
            score=0.3,
            reason="Could not reach the business registry. Score is provisional until this check completes.",
            source="OpenCorporates"
        )


def check_company_name_mismatch(posting_company: str, registered_name: str) -> ScoreSignal:
    posting_clean = posting_company.strip().lower()
    registered_clean = registered_name.strip().lower()

    if posting_clean == registered_clean:
        return ScoreSignal(
            label="Company name match",
            verdict=Verdict.PASS,
            weight=0.3,
            score=1.0,
            reason="Company name on the job posting matches the registered business name exactly.",
            source="Name check"
        )

    if posting_clean in registered_clean or registered_clean in posting_clean:
        return ScoreSignal(
            label="Company name match",
            verdict=Verdict.WARN,
            weight=0.3,
            score=0.6,
            reason=f"Company name '{posting_company}' is similar but not identical to the registered name '{registered_name}'. Could be a trading name — worth verifying.",
            source="Name check"
        )

    return ScoreSignal(
        label="Company name match",
        verdict=Verdict.FAIL,
        weight=0.3,
        score=0.0,
        reason=f"Company name '{posting_company}' does not match the registered name '{registered_name}'. This may indicate impersonation.",
        source="Name check"
    )


async def run_company_checks(
    company_name: str,
    jurisdiction: str = "us",
    registered_name: str | None = None
) -> list[ScoreSignal]:
    signals = []
    signals.append(await check_opencorporates(company_name, jurisdiction))

    if registered_name:
        signals.append(check_company_name_mismatch(company_name, registered_name))

    return signals