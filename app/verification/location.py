import httpx
import phonenumbers
import os
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
    "in": ["in"],
    "no": ["no"],
    "ph": ["ph"],
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
    ".in": "in",
    ".no": "no",
    ".ph": "ph",
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
        claimed_clean = claimed_country.lower().strip()
        phone = phone.strip().replace(" ", "").replace("-", "")
        
        try:
            parsed = phonenumbers.parse(phone, None)
        except Exception as e:
            region_hint = claimed_clean.upper()
            try:
                parsed = phonenumbers.parse(phone, region_hint)
            except Exception as e2:
                return ScoreSignal(
                    label="Phone country",
                    verdict=Verdict.WARN,
                    weight=0.3,
                    score=0.3,
                    reason=f"Could not parse phone number. Error: {str(e2)}",
                    source="Phone check"
                )

        if not phonenumbers.is_valid_number(parsed):
            return ScoreSignal(
                label="Phone country",
                verdict=Verdict.WARN,
                weight=0.3,
                score=0.3,
                reason="Phone number could not be validated.",
                source="Phone check"
            )

        phone_region = geocoder.region_code_for_number(parsed)
        expected = COUNTRY_CODE_MAP.get(claimed_clean, [claimed_clean])

        if not phone_region:
            return ScoreSignal(
                label="Phone country",
                verdict=Verdict.WARN,
                weight=0.3,
                score=0.1,
                reason=f"Could not determine region from phone number. Claimed country: {claimed_country.upper()}.",
                source="phone check",
            )

        match = phone_region.lower() in expected

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
            score=0.1,
            reason=f"Phone number country code does not match claimed location ({claimed_country.upper()}). Region detected: {phone_region}.",
            source="Phone check"
        )

    except Exception as e:
        return ScoreSignal(
            label="Phone country",
            verdict=Verdict.WARN,
            weight=0.3,
            score=0.3,
            reason="Could not parse phone number to verify country.",
            source="Phone check"
        )
    

async def check_voip(phone: str) -> ScoreSignal:
    api_key = os.getenv("APILAYER_KEY")
    if not api_key:
        return ScoreSignal(
            label="VOIP detection",
            verdict=Verdict.PASS,
            weight=0.2,
            score=0.8,
            reason="VOIP detection could not be completed. Manual review recommnded.",
            source="VOIP check"
        )
    
    phone_clean = phone.strip().replace(" ", "").replace("-", "")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.apilayer.com/number_verification/validate",
                params={"number": phone_clean},
                headers={"apikey": api_key},
                timeout=5.0
            )
            data = response.json()

        line_type = data.get("line_type", "").lower()
        valid = data.get("valid", False)
        carrier = data.get("carrier", "Unknown")
        country_code = data.get("country_code", "").lower()

        if not valid:
            return ScoreSignal(
                label="VOIP detection",
                verdict=Verdict.WARN,
                weight=0.2,
                score=0.3,
                reason="Phone number could not be validated",
                source="VOIP check"
            )
        
        if line_type in ("voip", "virtual"):
            return ScoreSignal(
                label="VOIP detection",
                verdict=Verdict.FAIL,
                weight=0.2,
                score=0.0,
                reason=f"Phone number is a VOIP or virtual number (carrier: {carrier}). Scammers commonly use virtual numbers to appear local while operating overseas.",
                source="VOIP check"
            )

        return ScoreSignal(
            label="VOIP detection",
            verdict=Verdict.PASS,
            weight=0.2,
            score=1.0,
            reason=f"Phone number appears to be a legitimate {line_type} line (carrier: {carrier}).",
            source="VOIP check"
        )

    except Exception:
        return ScoreSignal(
            label="VOIP detection",
            verdict=Verdict.PASS,
            weight=0.2,
            score=0.8,
            reason="VOIP detection check could not be completed. Manual review recommended.",
            source="VOIP check"
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
        signals.append(await check_voip(phone))

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