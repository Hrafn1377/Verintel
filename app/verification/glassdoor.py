from services.scraper import fetch_page_with_js
from scoring.models import ScoreSignal, Verdict


GLASSDOOR_JS = """() => ({
     name: document.querySelector('[data-test="employer-short-name"]')?.innerText?.trim() || null,
    rating: document.querySelector('[data-test="rating-info__rating"]')?.innerText?.trim() || null,
    review_count: document.querySelector('[data-test="rating-info__reviews-count"]')?.innerText?.trim() || null,
    size: document.querySelector('[data-test="employer-size"]')?.innerText?.trim() || null,
    founded: document.querySelector('[data-test="employer-founded"]')?.innerText?.trim() || null,
    industry: document.querySelector('[data-test="employer-industry"]')?.innerText?.trim() || null,
})"""


async def scrape_glassdoor_company(company_name: str) -> dict | None:
    slug = company_name.lower().replace(" ", "-")
    url = f"https://www.glassdoor.com/Overview/Working-at-{slug}-EI.htm"
    return await fetch_page_with_js(url, GLASSDOOR_JS)


def check_review_count(data: dict) -> ScoreSignal:
    review_count = data.get("review_count")

    if not review_count:
        return ScoreSignal(
            label="Glassdoor review count",
            verdict=Verdict.WARN,
            weight=0.25,
            score=0.3,
            reason="No reviews found on Glassdoor. Legitimate companies typically have at least some employee reviews.",
            source="Glassdoor"
        )
    
    count_clean = review_count.lower().replace(",", "").replace("reviews", "").strip()

    try:
        count = int(count_clean)

        if count <5:
            return ScoreSignal(
                label="Glassdoor review count",
                verdict=Verdict.WARN,
                weight=0.25,
                score=0.4,
                reason=f"Company has only {count} reviews on Glassdoor. Very few reviews can indicate a new or fake company.",
                source="Glassdoor"
            )

        return ScoreSignal(
            label="Glassdoor review count",
            verdict=Verdict.PASS,
            weight=0.25,
            score=1.0,
            reason=f"Company has {count} reviews on Glassdoor.",
            source="Glassdoor"
        )
    
    except ValueError:
        return ScoreSignal(
            label="Glassdoor review count",
            verdict=Verdict.WARN,
            weight=0.25,
            score=0.3,
            reason="Could not parse Glassdoor review count.",
            source="Glassdoor"
        )
    

def check_rating_suspicion(data: dict) -> ScoreSignal:
    rating = data.get("rating")
    review_count = data.get("review_count")

    if not rating:
        return ScoreSignal(
            label="Glassdoor rating",
            verdict=Verdict.WARN,
            weight=0.25,
            score=0.3,
            reason="No rating found on Glassdoor.",
            source="Glassdoor"
        )

    try:
        rating_float = float(rating)
        count_clean = review_count.lower().replace(",", "").replace("reviews", "").strip() if review_count else "0"
        count = int(count_clean) if count_clean.isdigit() else 0

        if rating_float >= 4.8 and count < 20:
            return ScoreSignal(
                label="Glassdoor rating",
                verdict=Verdict.WARN,
                weight=0.25,
                score=0.3,
                reason=f"Company has a suspiciously high rating ({rating_float}) with very few reviews ({count}). This pattern is common with fake or manipulated profiles.",
                source="Glassdoor"
            )

        if rating_float < 2.5:
            return ScoreSignal(
                label="Glassdoor rating",
                verdict=Verdict.WARN,
                weight=0.25,
                score=0.4,
                reason=f"Company has a low Glassdoor rating of {rating_float}. This may indicate poor working conditions or management issues.",
                source="Glassdoor"
            )
        
        return ScoreSignal(
            label="Glassdoor rating",
            verdict=Verdict.PASS,
            weight=0.25,
            score=1.0,
            reason=f"Company has a Glassdoor rating of {rating_float} based on {count} reviews.",
            source="Glassdoor"
        )

    except (ValueError, AttributeError):
        return ScoreSignal(
            label="Glassdoor rating",
            verdict=Verdict.WARN,
            weight=0.25,
            score=0.3,
            reason="Could not parse Glassdoor rating data.",
            source="Glassdoor"
        )
    

def check_glassdoor_completeness(data: dict) -> ScoreSignal:
    filled = sum(1 for v in data.values() if v)
    total = len(data)
    ration = filled / total

    if ratio < 0.4:
        return ScoreSignal(
            label="Glassdoor profile completeness",
            verdict=Verdict.FAIL,
            weight=0.25,
            score=0.1,
            reason="Glassdoor profile is mostly empty. Legitimate companies typically maintain a complete profile.",
            source="Glassdoor"
        )

    if ratio < 0.7:
        return ScoreSignal(
            label="Glassdoor profile completeness",
            verdict=Verdict.WARN,
            weight=0.25,
            score=0.5,
            reason="Glassdoor profile is partially complete. Some key details are missing.",
            source="Glassdoor"
        )

    return ScoreSignal(
        label="Glassdoor profile completeness",
        verdict=Verdict.PASS,
        weight=0.25,
        score=1.0,
        reason="Glassdoor profile is well populated with company details.",
        source="Glassdoor"
    )


async def run_glassdoor_checks(company_name: str) -> list[ScoreSignal]:
    data = await scrape_glassdoor_company(company_name)

    if not data:
        return [ScoreSignal(
            label="Glassdoor profile",
            verdict=Verdict.WARN,
            weight=0.7,
            score=0.2,
            reason="Could not retrieve Glassdoor company profile. The company may not have one, or the page is blocked.",
            source="Glassdoor"
        )]
    
    return [
        check_review_count(data),
        check_rating_suspicion(data),
        check_glassdoor_completeness(data),
    ]