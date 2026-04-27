import httpx
from scoring.models import ScoreSignal, Verdict

DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com",
    "throwaway.email", "sharklasers.com", "yopmail.com",
    "trashmail.com", "maildrop.cc", "dispostable.com",
    "spamgourmet.com", "fakeinbox.com", "spamherelots.com",
    "tempinbox.com", "getairmail.com", "filzmail.com",
    "throwam.com", "spamfree24.org", "mailnull.com",
    "spamspot.com", "spamgourmet.net", "spam4.me",
    "trashmail.at", "trashmail.io", "trashmail.me",
    "discard.email", "spamoff.de", "wegwerfmail.de",
}

FREE_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "live.com", "icloud.com", "protonmail.com", "aol.com",
    "mail.com", "zoho.com", "yandex.com", "gmx.com",
    "inbox.com", "fastmail.com", "hushmail.com",
}

SUBDOMAIN_PATTERNS = [
    "mail.", "email.", "careers.", "jobs.", "hr.", "recruit.",
    "hiring.", "talent.", "people.", "work.",
]


def get_domain(email: str) -> str:
    return email.strip().lower().split("@")[-1]


def normalize_domain(domain: str) -> str:
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0].lower().strip()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


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
            reason=f"Recruiter is using a free email provider ({domain}) rather than a company domain. Legitimate recruiters contact candidates from a company email address, not a personal or free provider. Not necessarily fake, but worth proceeding with caution.",
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
    company_clean = normalize_domain(company_domain)

    if recruiter_domain in DISPOSABLE_DOMAINS:
        return ScoreSignal(
            label="Email domain match",
            verdict=Verdict.FAIL,
            weight=0.4,
            score=0.0,
            reason=f"Recruiter email uses a disposable domain ({recruiter_domain}). This is a strong indicator of fraud.",
            source="Email check"
        )

    if recruiter_domain in FREE_DOMAINS:
        return ScoreSignal(
            label="Email domain match",
            verdict=Verdict.WARN,
            weight=0.4,
            score=0.3,
            reason=f"Recruiter email uses a free provider ({recruiter_domain}) instead of the company domain ({company_clean}). Legitimate recruiters use company email addresses.",
            source="Email check"
        )

    if recruiter_domain == company_clean:
        return ScoreSignal(
            label="Email domain match",
            verdict=Verdict.PASS,
            weight=0.4,
            score=1.0,
            reason=f"Recruiter email domain matches the company domain ({company_clean}).",
            source="Email check"
        )

    for pattern in SUBDOMAIN_PATTERNS:
        if recruiter_domain == f"{pattern}{company_clean}":
            return ScoreSignal(
                label="Email domain match",
                verdict=Verdict.PASS,
                weight=0.4,
                score=0.9,
                reason=f"Recruiter email uses a recognised subdomain of the company domain ({company_clean}).",
                source="Email check"
            )

    recruiter_root = ".".join(recruiter_domain.split(".")[-2:])
    company_root = ".".join(company_clean.split(".")[-2:])

    if recruiter_root == company_root:
        return ScoreSignal(
            label="Email domain match",
            verdict=Verdict.PASS,
            weight=0.4,
            score=0.85,
            reason=f"Recruiter email domain is a subdomain of the company domain ({company_clean}).",
            source="Email check"
        )

    if company_clean in recruiter_domain or recruiter_domain in company_clean:
        return ScoreSignal(
            label="Email domain match",
            verdict=Verdict.WARN,
            weight=0.4,
            score=0.4,
            reason=f"Recruiter email domain ({recruiter_domain}) partially matches the company domain ({company_clean}). This could indicate a lookalike domain used for impersonation.",
            source="Email check"
        )

    return ScoreSignal(
        label="Email domain match",
        verdict=Verdict.FAIL,
        weight=0.4,
        score=0.0,
        reason=f"Recruiter email domain ({recruiter_domain}) does not match the company domain ({company_clean}). This is a common sign of impersonation or a fraudulent recruiter.",
        source="Email check"
    )


def run_email_checks(recruiter_email: str, company_domain: str) -> list[ScoreSignal]:
    return [
        check_disposable(recruiter_email),
        check_free_provider(recruiter_email),
        check_domain_match(recruiter_email, company_domain),
    ]