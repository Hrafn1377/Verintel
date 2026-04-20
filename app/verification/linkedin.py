from services.scraper import fetch_page_with_js
from scoring.models import ScoreSignal, Verdict


LINKEDIN_JS = """() => ({
    name: document.querySelector('h1')?.innerText?.trim() || null,
    employees: document.querySelector('.org-about-company-module__company-size-definition-text')?.innerText?.trim()
        || document.querySelector('[data-test-id="about-us__size"]')?.innerText?.trim()
        || null,
    founded: document.querySelector('[data-test-id="about-us__foundedOn"]')?.innerText?.trim() || null,
    headquarters: document.querySelector('[data-test-id="about-us__headquarters"]')?.innerText?.trim() || null,
    industry: document.querySelector('[data-test-id="about-us__industry"]')?.innerText?.trim() || null,
})"""


async def scrape_linkedin_company(slug: str) -> dict | None:
    url = f"https://www.linkedin.com/company/{slug}/"
    return await fetch_page_with_js(url, LINKEDIN_JS)


def check_employee_count(data: dict) -> ScoreSignal:
    employees = data.get("employees")

    if not employees:
        return ScoreSignal(
            label="LinkedIn employee count",
            verdict=Verdict.WARN,
            weight=0.2,
            score=0.3, 
            reason="Could not retrieve employee count from LinkedIn. Rpofile may be incomplete or private.",
            source="LinkedIn"
        )
    
    employees_clean = employees.lower()

    if "1-10" in employees_clean or "11-50" in employees_clean:
        return ScoreSignal(
            label="LinkedIn employee count",
            verdict=Verdict.WARN,
            weight=0.2,
            score=0.5,
            reason=f"Company lists {employees} employees on LinkedIn. Very small companies posting multiple roles can sometimes indicate a fake listing.",
            source="LinkedIn"
        )
    
    return ScoreSignal(
        label="LinkedIn employee count",
        verdict=Verdict.PASS,
        weight=0.2,
        score=1.0,
        reason=f"Company lists {employees} employees on LinkedIn.",
        source="LinkedIn"
    )


def check_founded_date(data: dict) -> ScoreSignal:
    founded = data.get("founded")

    if not founded:
        return ScoreSignal(
            label="LinkedIn founded date",
            verdict=Verdict.WARN,
            weight=0.2,
            score=0.3,
            reason="No founded date listed on LinkedIn. Established companies typically include this.",
            source="LinkedIn"
        )
    
    try:
        year = int(founded.strip())
        if year > 2023:
            return ScoreSignal(
                label="LinkedIn founded date",
                verdict=Verdict.WARN,
                weight=0.2,
                score=0.4,
                reason=f"Company was founded in {year}. Very recently founded companies posting aggressively can be a red flag.",
                source="LinkedIn"
            )
        
        return ScoreSignal(
            label="LinkedIn founded date",
            verdict=Verdict.PASS,
            weight=0.2,
            score=1.0,
            reason=f"Company has been established since {year}.",
            source="LinkedIn"
        )
    
    except ValueError:
        return ScoreSignal(
            label="LinkedIn founded date",
            verdict=Verdict.WARN,
            weight=0.2,
            score=0.3,
            reason="Founded date on LinkedIn is in an unexpected format.",
            source="LinkedIn"
        )
    

def check_profile_completeness(data: dict) -> ScoreSignal:
    filled = sum(1 for v in data.values() if v)
    total = len(data)
    ratio = filled / total

    if ratio < 0.4:
        return ScoreSignal(
            label="LinkedIn profile completeness",
            verdict=Verdict.FAIL,
            weight=0.3,
            score=0.1,
            reason="LinkedIn profile is mostly empty. Legitimate companies typically maintain complete profiles.",
            source="LinkedIn"
        )
    
    if ratio < 0.7:
        return ScoreSignal(
            label="LinkedIn profile completeness",
            verdict=Verdict.WARN,
            weight=0.3,
            score=0.5,
            reason="LinkedIn profile is partially complete. Some key details are missing.",
            source="LinkedIn"
        )
    
    return ScoreSignal(
        label="LinkedIn profile completeness",
        verdict=Verdict.PASS,
        weight=0.3,
        score=1.0,
        reason="LinkedIn profile is well populated with company details.",
        source="LinkedIn"
    )


async def run_linkedin_checks(slug: str) -> list[ScoreSignal]:
    data = await scrape_linkedin_company(slug)

    if not data:
        return [ScoreSignal(
            label="LinkedIn profile",
            verdict=Verdict.WARN,
            weight=0.7,
            score=0.2,
            reason="Could not retrieve LinkedIn company profile. The company may not have one, or the page is blocked.",
            source="LinkedIn"
        )]
    
    return [
        check_employee_count(data),
        check_founded_date(data),
        check_profile_completeness(data),
    ]