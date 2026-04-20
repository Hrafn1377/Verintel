import httpx
from scoring.models import ScoreSignal, Verdict

DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com",
    "throwaway.email", "sharklasers.com", "yopmail.com",
    "trashmail.com", "maildrop.cc", "dispostable.com",
    "spamgourmet.com", "fakeinbox.com", "spamherelots.com",
}

FREE_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "live.com", "icloud.com", "protonmail.com", "aol.com",
}


def get_domain(email: str) -> str:
    return email.strip().lower().split("@")[-1]


def check_disposable(email: str) -> ScoreSignal:
    domain = get_domain(email)

    if domain in DISPOSABLE_DOMAINS:
        return ScoreSignal(
            label="Disposable email",
            verdict=Verdict.FAIL,
            weight=0.4,
            score=0.0,
            reason=f"This email uses a known disposable domain ({domain}). Legitimate recruiters do not use throwaway addresses.",
            source="Email check"
        )
    
    return ScoreSignal(
        label="Disposable email",
        verdict=Verdict.PASS,
        weight=0.4,
        score=1.0,
        reason="Email domain is not a known disposable provider.",
        source="Email check"
    )


def check_free_provider(email: str) -> ScoreSignal:
    domain = get_domain(email)

    if domain in FREE_DOMAINS:
        return ScoreSignal(
            label="Free email provider",
            verdict=Verdict.WARN,
            weight=0.2,
            score=0.4,
            reason=f"Recruiter is using a free email provider ({domain}) rathen than a company domain. Legitimate recruiters contact candidates from a company email address, not a personal or free provider. Not necessarily fake, but worth proceeding with caution.",
            source="Email check"
        )
    
    return ScoreSignal(
        label="Free email provider",
        verdict=Verdict.PASS,
        weight=0.2,
        score=1.0,
        reason="Recruiter email matches a company domain, not a free provider.",
        source="Email check"
    )


def check_domain_match(recruiter_email: str, company_domain: str) -> ScoreSignal:
    recruiter_domain = get_domain(recruiter_email)

    if recruiter_domain == company_domain.lower().strip():
        return ScoreSignal(
            label="Email domain match",
            verdict=Verdict.PASS,
            weight=0.4,
            score=1.0, 
            reason=f"Recruiter email domain matches the company domain ({company_domain}).",
            source="Email check"
        )
    
    return ScoreSignal(
        label="Email domain match",
        verdict=Verdict.FAIL,
        weight=0.4,
        score=0.0,
        reason=f"Recruiter email domain ({recruiter_domain}) does not match the company domain ({company_domain}). This is a common sign of impersonation.",
        source="Email check"
    )


def run_email_checks(recruiter_email: str, company_domain: str) -> list[ScoreSignal]:
    return [
        check_disposable(recruiter_email),
        check_free_provider(recruiter_email),
        check_domain_match(recruiter_email, company_domain),
    ]