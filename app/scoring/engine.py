import uuid
from scoring.models import ScoreSignal, TrustReport, Verdict
from verification.domain import check_domain
from verification.email import run_email_checks
from verification.company import run_company_checks
from verification.linkedin import run_linkedin_checks
from verification.glassdoor import run_glassdoor_checks
from verification.indeed import run_indeed_checks
from verification.location import run_location_checks
from scoring.nlp import run_nlp_checks


def detect_fraud_patterns(report: TrustReport) -> TrustReport:
    signals_by_label = {s.label: s for s in report.signals}

    salary_sanity = signals_by_label.get("Salary sanity")
    business_registry = signals_by_label.get("Business registry")
    vague_language = signals_by_label.get("Vague language")
    domain_age = signals_by_label.get("Domain age")
    incomplete_posting = signals_by_label.get("Incomplete posting")
    salary_transparency = signals_by_label.get("Salary transparency")
    currency_conversion = signals_by_label.get("Currency conversion check")
    phone_country = signals_by_label.get("Phone country")

    fraud_indicators = []

    if salary_sanity and salary_sanity.verdict == Verdict.FAIL:
        fraud_indicators.append("unrealistic salary")

    if business_registry and business_registry.verdict == Verdict.FAIL:
        fraud_indicators.append("not found in business registry")

    if vague_language and vague_language.verdict in (Verdict.WARN, Verdict.FAIL):
        fraud_indicators.append("vague or misleading language")
    
    if domain_age and domain_age.verdict == Verdict.FAIL:
        fraud_indicators.append("brand new domain")

    if incomplete_posting and incomplete_posting.verdict == Verdict.WARN:
        fraud_indicators.append("incomplete posting fields")

    if salary_transparency and salary_transparency.verdict == Verdict.FAIL:
        fraud_indicators.append("fraudulent salary figures")

    if currency_conversion and currency_conversion.verdict == Verdict.FAIL:
        fraud_indicators.append("salary matches foreign currency conversion")

    if phone_country and phone_country.verdict == Verdict.WARN:
        fraud_indicators.append("phone number country mismatch")
    
    if len(fraud_indicators) >= 3:
        report.signals.append(ScoreSignal(
            label="Fraud pattern detected",
            verdict=Verdict.FAIL,
            weight=0.5,
            score=0.0,
            reason=f"This posting shows multiple characteristics consistent with fraud: {', '.join(fraud_indicators)}. We strongly recommend not applying to this role.",
            source="Fraud detection"
        ))
    elif len(fraud_indicators) == 2:
        report.signals.append(ScoreSignal(
            label="Fraud indicators",
            verdict=Verdict.WARN,
            weight=0.3,
            score=0.1,
            reason=f"This posting shows some characteristics associated with fraudulent listings: {', '.join(fraud_indicators)}. Proceed with caution and research this company independently.",
            source="Fraud detection"
        ))

    return report

def generate_summary(report: TrustReport) -> str:
    score = report.overall_score
    fails = [s for s in report.signals if s.verdict == Verdict.FAIL]
    warns = [s for s in report.signals if s.verdict == Verdict.WARN]

    fraud = next((s for s in fails if s.label == "Fraud pattern detected"), None)
    if fraud:
        return "Fraud pattern detected — this posting shows multiple characteristics of a scam. Do not apply."

    if fails:
        fail_labels = ", ".join(f.label.lower() for f in fails[:2])
        return f"Flagged — failed checks on {fail_labels}. Treat with caution."

    if score >= 0.8:
        return "Looks legitimate — all major checks passed."

    if score >= 0.6:
        warn_labels = ", ".join(w.label.lower() for w in warns[:2])
        return f"Mostly okay but has warnings on {warn_labels}. Worth a closer look."

    if score >= 0.4:
        return "Several concerns detected. Research this company independently before applying."

    return "Low trust score. Multiple red flags detected — proceed with extreme caution."


async def score_company(
    company_name: str,
    domain: str,
    linkedin_slug: str | None = None,
    claimed_country: str = "us",
    phone: str | None = None,
    ip: str | None = None,
    registered_name: str | None = None,
) -> TrustReport:
    report = TrustReport(
        entity_id=str(uuid.uuid4()),
        entity_type="company",
        overall_score=0.0,
    )

    report.signals.append(check_domain(domain))
    report.signals.extend(
        await run_company_checks(company_name, claimed_country, registered_name)
    )
    report.signals.extend(
        await run_location_checks(claimed_country, domain, phone, ip)
    )
    report.signals.extend(await run_glassdoor_checks(company_name))

    if linkedin_slug:
        report.signals.extend(await run_linkedin_checks(linkedin_slug))

    report = detect_fraud_patterns(report)
    report.compute()
    report.summary = generate_summary(report)
    return report


async def score_recruiter(
    recruiter_email: str,
    company_domain: str,
    claimed_country: str = "us",
    phone: str | None = None,
    ip: str | None = None,
) -> TrustReport:
    report = TrustReport(
        entity_id=str(uuid.uuid4()),
        entity_type="recruiter",
        overall_score=0.0,
    )

    report.signals.extend(run_email_checks(recruiter_email, company_domain))
    report.signals.extend(
        await run_location_checks(claimed_country, None, phone, ip)
    )

    report = detect_fraud_patterns(report)
    report.compute()
    report.summary = generate_summary(report)
    return report


async def score_posting(
    posting_text: str,
    company_name: str,
    domain: str,
    recruiter_email: str | None = None,
    linkedin_slug: str | None = None,
    indeed_job_id: str | None = None,
    claimed_country: str = "us",
    phone: str | None = None,
    ip: str | None = None,
) -> TrustReport:
    report = TrustReport(
        entity_id=str(uuid.uuid4()),
        entity_type="posting",
        overall_score=0.0,
    )

    report.signals.extend(await run_nlp_checks(posting_text))
    report.signals.append(check_domain(domain))
    report.signals.extend(
        await run_company_checks(company_name, claimed_country)
    )
    report.signals.extend(
        await run_location_checks(claimed_country, domain, phone, ip)
    )
   # report.signals.extend(await run_glassdoor_checks(company_name))

    if recruiter_email:
        report.signals.extend(run_email_checks(recruiter_email, domain))

    if linkedin_slug:
        report.signals.extend(await run_linkedin_checks(linkedin_slug))

    if indeed_job_id:
        report.signals.extend(await run_indeed_checks(indeed_job_id))

    report = detect_fraud_patterns(report)
    report.compute()
    report.summary = generate_summary(report)
    return report