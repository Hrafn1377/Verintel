import httpx
import phonenumbers
from phonenumbers import geocoder
from scoring.models import ScoreSignal, Verdict

COUNTRY_CODE_MAP = {
    "us": ["us"],
    "gb": ["gb", "uk"],
    "ca": ["ca"],
    "au": ["au"],
    "de": ["de"],
    "fr": ["fr"],
    "ie": ["ie"],
}

TLD_COUNTRY_MAP = {
    ".co.uk": "gb",
    ".uk": "gb",
    ".us": "us",
    ".ca": "ca",
    ".com.au": "au",
    ".de": "de",
    ".fr": "fr",
    ".ie": "ie",
}


async def check_ip_geolocation(ip: str, claimed_country: str) -> ScoreSignal:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"https://ipapi.co/{ip}/json/")
            data = r.json()
            detected_country = data.get("country_code", "").lower()
            claimed_clean = claimed_country.lower().strip()

            if not detected_country:
                return ScoreSignal(
                    label="IP geolocation",
                    verdict=Verdict.WARN,
                    weight=0.2,
                    score=0.1,
                    reason="Could not determine location from IP address.",
                    source="IP geolocation"
                )
            
            expected = COUNTRY_CODE_MAP.get(claimed_country, [claimed_clean])

            if detected_country in expected:
                return ScoreSignal(
                    label="IP geolocation",
                    verdict=Verdict.PASS,
                    weight=0.2,
                    score=1.0,
                    reason=f"IP address location matches claimed country ({claimed_country.upper()}).",
                    source="IP geolocation"
                )
            
            return ScoreSignal(
                label="IP geolocation",
                verdict=Verdict.WARN,
                weight=0.2,
                score=0.1,
                reason=f"IP address is located in {detected_country.upper()} but company claims to be in {claimed_country.upper()}. Could indicated a VPN or misrepresentation.",
                source="IP geolocation"
            )
        
    except Exception:
        return ScoreSignal(
            label="IP geolocation",
            verdict=Verdict.WARN,
            weight=0.2,
            score=0.3,
            reason="IP geolocation check failed. Unable to verify location.",
            source="IP geolocation"
        )
    

def check_domain_tld(domain: str, claimed_country: str) -> ScoreSignal:
    claimed_clean = claimed_country.lower().strip()
    domain_clean = domain.lower().strip()

    for tld, country in TLD_COUNTRY_MAP.items():
        if domain_clean.endswith(tld):
            expected = COUNTRY_CODE_MAP.get(claimed_clean, [claimed_clean])
            if country in expected:
                return ScoreSignal(
                    label="Domain TLD",
                    verdict=Verdict.PASS,
                    weight=0.2,
                    score=1.0,
                    reason=f"Domain TLD matches claimed country ({claimed_country.upper()}).",
                    source="Domain TLD"
                )
            
            return ScoreSignal(
                label="Domain TLD",
                verdict=Verdict.WARN,
                weight=0.2,
                score=0.3,
                reason=f"Domain TLD suggests {country.upper()} but company claims to be in {claimed_country.upper()}.",
                source="Domain TLD"
            )

    return ScoreSignal(
        label="Domain TLD",
        verdict=Verdict.PASS,
        weight=0.2,
        score=0.5,
        reason="Domain uses a generic TLD (.com, .org etc.) — no country mismatch detected.",
        source="Domain TLD"
    )


def check_phone_country(phone: str, claimed_country: str) -> ScoreSignal:
    try:
        parsed = phonenumbers.parse(phone, None)
        phone_region = geocoder.region_codes_for_number(parsed)
        claimed_clean = claimed_country.lower().strip()
        expected - COUNTRY_CODE_MAP.get(claimed_clean, [claimed_clean])

        match = any(r.lower() in expected for r in phone_region)

        if match:
            return ScoreSignal(
                label="Phone country",
                verdict=Verdict.PASS,
                weight=0.3,
                score=1.0,
                reason=f"Phone number country code matches claimed location ({claimed_country.upper()}).",
                source="Phone check"
            )

        return ScoreSignal(
            label="Phone country",
            verdict=Verdict.WARN,
            weight=0.3,
            score=0.3,
            reason=f"Phone number country code does not match claimed location ({claimed_country.upper()}). Regions detected: {', '.join(phone_region)}.",
            source="Phone check"
        )

    except Exception:
        return ScoreSignal(
            label="Phone country",
            verdict=Verdict.WARN,
            weight=0.3,
            score=0.3,
            reason="Could not parse phone number to verify country.",
            source="Phone check"
        )


async def run_location_checks(
    claimed_country: str,
    domain: str | None = None,
    phone: str | None = None,
    ip: str | None = None,
) -> list[ScoreSignal]:
    signals = []

    if ip:
        signals.append(await check_ip_geolocation(ip, claimed_country))

    if domain:
        signals.append(check_domain_tld(domain, claimed_country))

    if phone:
        signals.append(check_phone_country(phone, claimed_country))

    if not signals:
        return [ScoreSignal(
            label="Location verification",
            verdict=Verdict.WARN,
            weight=0.5,
            score=0.3,
            reason="No location data provided to verify against claimed country.",
            source="Location check"
        )]

    return signals