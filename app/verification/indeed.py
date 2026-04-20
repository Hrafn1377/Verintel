from services.scraper import fetch_page_with_js
from scoring.models import ScoreSignal, Verdict


INDEED_JS = """() => ({
    company_name: document.querySelector('[data-testid="inlineHeader-companyName"]')?.innerText?.trim() || null,
    rating: document.querySelector('[data-testid="inlineHeader-ratings-link"]')?.innerText?.trim() || null,
    review_count: document.querySelector('[data-testid="inlineHeader-ratings-link"] span')?.innerText?.trim() || null,
    location: document.querySelector('[data-testid="inlineHeader-companyLocation"]')?.innerText?.trim() || null,
    job_title: document.querySelector('[data-testid="jobsearch-JobInfoHeader-title"]')?.innerText?.trim() || null,
    posted_date: document.querySelector('[data-testid="myJobsStateDate"]')?.innerText?.trim() || null,
    apply_count: document.querySelector('[data-testid="indeedApply-button"]')?.innerText?.trim() || null,
})"""


async def scrape_indeed_posting(job_id: str) -> dict | None:
    url = f"https://www.indeed.com/viewjob?jk={job_id}"
    return await fetch_page_with_js(url, INDEED_JS)


def check_indeed_rating(data: dict) -> ScoreSignal:
    rating = data.get("rating")
    review_count = data.get("review_count")

    if not rating:
        return ScoreSignal(
            label="Indeed company rating",
            verdict=Verdict.WARN,
            weight=0.25,
            score=0.3,
            reason="No Indeed company rating found. Established companies typically have employee ratings.",
            source="Indeed"
        )

    try:
        rating_float = float(rating.split()[0])
        count_str = review_count.replace(",", "").split()[0] if review_count else "0"
        count = int(count_str) if count_str.isdigit() else 0

        if rating_float >= 4.8 and count < 10:
            return ScoreSignal(
                label="Indeed company rating",
                verdict=Verdict.WARN,
                weight=0.25,
                score=0.3,
                reason=f"Suspiciously high Indeed rating ({rating_float}) with very few reviews ({count}). This pattern is common with fake company profiles.",
                source="Indeed"
            )

        if rating_float < 2.5:
            return ScoreSignal(
                label="Indeed company rating",
                verdict=Verdict.WARN,
                weight=0.25,
                score=0.4,
                reason=f"Company has a low Indeed rating of {rating_float}. Worth researching further before applying.",
                source="Indeed"
            )

        return ScoreSignal(
            label="Indeed company rating",
            verdict=Verdict.PASS,
            weight=0.25,
            score=1.0,
            reason=f"Company has an Indeed rating of {rating_float} based on {count} reviews.",
            source="Indeed"
        )

    except (ValueError, AttributeError):
        return ScoreSignal(
            label="Indeed company rating",
            verdict=Verdict.WARN,
            weight=0.25,
            score=0.3,
            reason="Could not parse Indeed rating data.",
            source="Indeed"
        )


def check_posting_age(data: dict) -> ScoreSignal:
    posted_date = data.get("posted_date")

    if not posted_date:
        return ScoreSignal(
            label="Posting age",
            verdict=Verdict.WARN,
            weight=0.25,
            score=0.3,
            reason="Could not determine when this job was posted.",
            source="Indeed"
        )

    posted_clean = posted_date.lower()

    if "just posted" in posted_clean or "today" in posted_clean:
        return ScoreSignal(
            label="Posting age",
            verdict=Verdict.PASS,
            weight=0.25,
            score=1.0,
            reason="Job was posted recently.",
            source="Indeed"
        )

    if "30+" in posted_clean or "60" in posted_clean or "90" in posted_clean:
        return ScoreSignal(
            label="Posting age",
            verdict=Verdict.WARN,
            weight=0.25,
            score=0.4,
            reason=f"Job posting is old ({posted_date}). Postings that stay up for months without being filled can indicate ghost jobs or fake listings.",
            source="Indeed"
        )

    return ScoreSignal(
        label="Posting age",
        verdict=Verdict.PASS,
        weight=0.25,
        score=0.8,
        reason=f"Job was posted {posted_date}.",
        source="Indeed"
    )


def check_indeed_completeness(data: dict) -> ScoreSignal:
    filled = sum(1 for v in data.values() if v)
    total = len(data)
    ratio = filled / total

    if ratio < 0.4:
        return ScoreSignal(
            label="Indeed profile completeness",
            verdict=Verdict.FAIL,
            weight=0.25,
            score=0.1,
            reason="Indeed job posting is missing key information. Legitimate postings typically include full company and role details.",
            source="Indeed"
        )

    if ratio < 0.7:
        return ScoreSignal(
            label="Indeed profile completeness",
            verdict=Verdict.WARN,
            weight=0.25,
            score=0.5,
            reason="Indeed job posting is missing some details.",
            source="Indeed"
        )

    return ScoreSignal(
        label="Indeed profile completeness",
        verdict=Verdict.PASS,
        weight=0.25,
        score=1.0,
        reason="Indeed job posting is complete with all key details.",
        source="Indeed"
    )


async def run_indeed_checks(job_id: str) -> list[ScoreSignal]:
    data = await scrape_indeed_posting(job_id)

    if not data:
        return [ScoreSignal(
            label="Indeed profile",
            verdict=Verdict.WARN,
            weight=0.7,
            score=0.2,
            reason="Could not retrieve Indeed job posting. The listing may have been removed or the page is blocked.",
            source="Indeed"
        )]

    return [
        check_indeed_rating(data),
        check_posting_age(data),
        check_indeed_completeness(data),
    ]