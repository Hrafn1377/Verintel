import re
import spacy
from scoring.models import ScoreSignal, Verdict

nlp = spacy.load("en_core_web_sm")


def extract_max_salary(money_text: str) -> int | None:
    numbers = re.findall(r'[\d,]+', money_text)
    if not numbers:
        return None
    amounts = []
    for n in numbers:
        try:
            amounts.append(int(n.replace(",", "")))
        except ValueError:
            continue
    return max(amounts) if amounts else None

VAGUE_PHRASES = {
    "unlimited earning potential",
    "be your own boss",
    "work from anywhere",
    "no experience necessary",
    "must be self-motivated",
    "ground floor opportunity",
    "entrepreneurial mindset",
    "commission only",
    "multi-level",
    "passive income",
    "financial freedom",
    "uncapped commission",
    "results-driven",
    "hustle",
    "strong problem-solving skills",
    "excellent communication skills",
    "team player",
    "fast-paced environment",
    "go-getter",
    "self-starter",
    "think outside the box",
    "wear many hats",
    "rockstar",
    "ninja",
    "guru",
    "passionate about",
    "dynamic team",
    "hit the ground running",
    "best practices",
    "detail-oriented",
    "proactive",
    "synergy",
    "leverage",
    "move the needle",
    "deep dive",
    "bandwidth",
    "circle back",
    "take ownership",
    "growth mindset",
}

URGENCY_PHRASES = {
    "apply immediately",
    "urgent hire",
    "immediate start",
    "must apply now",
    "limited positions",
    "positions filling fast",
    "don't miss out",
    "act now",
}

PERSONAL_INFO_REQUESTS = {
    "bank account",
    "social security",
    "national insurance",
    "passport number",
    "date of birth",
    "home address",
    "upfront payment",
    "training fee",
    "starter kit",
}


def check_vague_language(text: str) -> ScoreSignal:
    text_lower = text.lower()
    found = [p for p in VAGUE_PHRASES if p in text_lower]

    if len(found) >= 3:
        return ScoreSignal(
            label="Vague language",
            verdict=Verdict.FAIL,
            weight=0.25,
            score=0.0,
            reason=f"Posting contains {len(found)} vague or MLM-style phrases: {', '.join(found[:3])}. Legitimate job postings describe specific roles and responsibilities.",
            source="NLP"
        )

    if len(found) >= 1:
        return ScoreSignal(
            label="Vague language",
            verdict=Verdict.WARN,
            weight=0.25,
            score=0.5,
            reason=f"Posting contains potentially vague language: {', '.join(found)}. Worth reading carefully.",
            source="NLP"
        )

    return ScoreSignal(
        label="Vague language",
        verdict=Verdict.PASS,
        weight=0.25,
        score=1.0,
        reason="No vague or misleading language patterns detected in the posting.",
        source="NLP"
    )


def check_urgency(text: str) -> ScoreSignal:
    text_lower = text.lower()
    found = [p for p in URGENCY_PHRASES if p in text_lower]

    if found:
        return ScoreSignal(
            label="Urgency language",
            verdict=Verdict.WARN,
            weight=0.2,
            score=0.3,
            reason=f"Posting uses urgency tactics: {', '.join(found)}. This is a common pressure technique in scam postings.",
            source="NLP"
        )

    return ScoreSignal(
        label="Urgency language",
        verdict=Verdict.PASS,
        weight=0.2,
        score=1.0,
        reason="No urgency pressure tactics detected.",
        source="NLP"
    )


def check_personal_info_requests(text: str) -> ScoreSignal:
    text_lower = text.lower()
    found = [p for p in PERSONAL_INFO_REQUESTS if p in text_lower]

    if found:
        return ScoreSignal(
            label="Personal info request",
            verdict=Verdict.FAIL,
            weight=0.4,
            score=0.0,
            reason=f"Posting requests sensitive personal information: {', '.join(found)}. Legitimate employers never ask for this in a job posting.",
            source="NLP"
        )

    return ScoreSignal(
        label="Personal info request",
        verdict=Verdict.PASS,
        weight=0.4,
        score=1.0,
        reason="No requests for sensitive personal information found.",
        source="NLP"
    )


def check_salary_vagueness(text: str) -> ScoreSignal:
    doc = nlp(text)
    has_money = any(ent.label_ == "MONEY" for ent in doc.ents)

    vague_salary = any(p in text.lower() for p in [
        "competitive salary",
        "market rate",
        "to be discussed",
        "doe",
        "negotiable",
        "based on experience",
    ])

    if not has_money and vague_salary:
        return ScoreSignal(
            label="Salary transparency",
            verdict=Verdict.WARN,
            weight=0.15,
            score=0.4,
            reason="Posting uses vague salary language with no specific figures. Transparent employers typically include a salary range.",
            source="NLP"
        )

    if not has_money:
        return ScoreSignal(
            label="Salary transparency",
            verdict=Verdict.WARN,
            weight=0.15,
            score=0.5,
            reason="No salary information found in the posting.",
            source="NLP"
        )

    if has_money:
        money_entities = [ent.text for ent in doc.ents if ent.label_ == "MONEY"]
        for money in money_entities:
            amount = extract_max_salary(money)
            if amount is None:
                continue
            if amount > 400000:
                return ScoreSignal(
                    label="Salary transparency",
                    verdict=Verdict.FAIL,
                    weight=0.15,
                    score=0.0,
                    reason=f"Salary figure of {money} is present but appears fraudulent. Legitimate employers do not post salaries in this range for standard roles.",
                    source="NLP"
                )

    return ScoreSignal(
        label="Salary transparency",
        verdict=Verdict.PASS,
        weight=0.15,
        score=1.0,
        reason="Posting includes specific salary or compensation figures within a realistic range.",
        source="NLP"
    )

def check_salary_sanity(text: str) -> ScoreSignal:
    doc = nlp(text)
    money_entities = [ent.text for ent in doc.ents if ent.label_ == "MONEY"]

    if not money_entities:
        return ScoreSignal(
            label="Salary sanity",
            verdict=Verdict.PASS,
            weight=0.15,
            score=0.8,
            reason="No salary figures to verify",
            source="NLP"
        )
    
    for money in money_entities:
        amount = extract_max_salary(money)
        if amount is None:
            continue

        if amount > 400000:
            return ScoreSignal(
                label="Salary sanity",
                verdict=Verdict.FAIL,
                weight=0.15,
                score=0.0,
                reason=f"Salary figure of {money} is unrealistically high for most roles. This is a common tactic in fake job postings to attract applicants.",
                source="NLP"
            )
        
        if amount < 15000 and amount > 999:
            return ScoreSignal(
                label="Salary sanity",
                verdict=Verdict.WARN,
                weight=0.15,
                score=0.4,
                reason=f"Salary figure of {money} appears unusually low. Verify this is accurate before applying.",
                source="NLP"
            )
        
    return ScoreSignal(
        label="Salary sanity",
        verdict=Verdict.PASS,
        weight=0.15,
        score=1.0,
        reason="Salary figures appear within a reasonable range.",
        source="NLP"
    )


def check_incomplete_fields(text: str) -> ScoreSignal:
    patterns = [
        r"\byears of experience\b(?!\s*:?\s*\d)",
        r"\byears?\b\s*\(preferred\)",
        r"\b\d+\+?\s*-\s*\d+\s*years\b",
    ]

    incomplete = any(re.search(p, text.lower()) for p in patterns[:1])

    if incomplete:
        return ScoreSignal(
            label="Incomplete posting",
            verdict=Verdict.WARN,
            weight=0.1,
            score=0.3,
            reason="Posting contains incomplete fields such as 'years of experience' with no number specified. This may indicate an auto-generated or hastily copied posting.",
            source="NLP"
        )

    return ScoreSignal(
        label="Incomplete posting",
        verdict=Verdict.PASS,
        weight=0.1,
        score=1.0,
        reason="No incomplete fields detected in the posting.",
        source="NLP"
    )


async def check_currency_conversion(text: str) -> ScoreSignal:
    import httpx

    doc = nlp(text)
    money_entities = [ent.text for ent in doc.ents if ent.label_ == "MONEY"]

    if not money_entities:
        return ScoreSignal(
            label="Currency conversion check",
            verdict=Verdict.PASS,
            weight=0.2,
            score=1.0,
            reason="No salary figures found to check for currency conversion.",
            source="Frankfurter API",
        )

    amounts = []
    for money in money_entities:
        amount = extract_max_salary(money)
        if amount and amount > 1000:
            amounts.append(amount)

    if not amounts:
        return ScoreSignal(
            label="Currency conversion check",
            verdict=Verdict.PASS,
            weight=0.2,
            score=1.0,
            reason="Salary figures could not be parsed for conversion check.",
            source="Frankfurter API",
        )

    max_salary = max(amounts)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.frankfurter.dev/v2/rates",
                params={
                    "base": "USD",
                    "quotes": "INR,JPY,PKR,NGN,PHP,BDT,IDR,VND,MMK,LKR,NPR,KES,GHS,UGX,TZS,ETB"
                },
                timeout=5.0
            )
            data = response.json()
    except Exception:
        return ScoreSignal(
            label="Currency conversion check",
            verdict=Verdict.PASS,
            weight=0.2,
            score=0.8,
            reason="Currency conversion check could not be completed. Manual review recommended.",
            source="Frankfurter API",
        )

    rates = {item["quote"]: item["rate"] for item in data}
    suspicious_currencies = []

    for currency, rate in rates.items():
        converted = max_salary / rate
        if 5000 <= converted <= 150000:
            suspicious_currencies.append(currency)

    if suspicious_currencies:
        return ScoreSignal(
            label="Currency conversion check",
            verdict=Verdict.FAIL,
            weight=0.2,
            score=0.0,
            reason=f"Posted salary of {max_salary:,} appears to match a realistic salary when converted from {', '.join(suspicious_currencies)}. This is a common tactic used to make low foreign salaries appear as high USD figures.",
            source="Frankfurter API",
        )

    return ScoreSignal(
        label="Currency conversion check",
        verdict=Verdict.PASS,
        weight=0.2,
        score=1.0,
        reason="Salary figures do not match known currency conversion patterns.",
        source="Frankfurter API",
    )


async def run_nlp_checks(posting_text: str) -> list[ScoreSignal]:
    currency_signal = await check_currency_conversion(posting_text)
    return [
        check_vague_language(posting_text),
        check_urgency(posting_text),
        check_personal_info_requests(posting_text),
        check_salary_vagueness(posting_text),
        check_salary_sanity(posting_text),
        check_incomplete_fields(posting_text),
        currency_signal,
    ]

