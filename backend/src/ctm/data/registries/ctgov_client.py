"""ClinicalTrials.gov v2 REST API client."""

from __future__ import annotations

import logging

import httpx

from ctm.models.trial import ClinicalTrial, EligibilityCriteria, TrialSite
from ctm.pipeline.matching.criteria_parser import parse_criteria

logger = logging.getLogger(__name__)

CTGOV_BASE = "https://clinicaltrials.gov/api/v2"


class CTGovClient:
    """Async client for ClinicalTrials.gov v2 API."""

    def __init__(self, verify_ssl: bool = True) -> None:
        self._client = httpx.AsyncClient(
            base_url=CTGOV_BASE,
            timeout=30.0,
            verify=verify_ssl,
            headers={
                "Accept": "application/json",
                "User-Agent": "Trialibre/0.1 (clinical-trial-matching; +https://github.com/matthewhmaxwell/trialibre)",
            },
        )

    async def search(
        self,
        condition: str | None = None,
        intervention: str | None = None,
        location: str | None = None,
        status: list[str] | None = None,
        phase: list[str] | None = None,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> dict:
        """Search for clinical trials.

        Returns:
            {"trials": [...], "total": int, "next_page_token": str|None}
        """
        params: dict = {"pageSize": page_size}

        query_parts = []
        if condition:
            query_parts.append(f"AREA[Condition]{condition}")
        if intervention:
            query_parts.append(f"AREA[Intervention]{intervention}")
        if location:
            params["query.locn"] = location

        if query_parts:
            params["query.cond"] = condition or ""
            params["query.intr"] = intervention or ""

        if status:
            params["filter.overallStatus"] = ",".join(status)
        if phase:
            params["filter.phase"] = ",".join(phase)
        if page_token:
            params["pageToken"] = page_token

        resp = await self._client.get("/studies", params=params)
        resp.raise_for_status()
        data = resp.json()

        trials = [self._parse_study(s) for s in data.get("studies", [])]

        return {
            "trials": trials,
            "total": data.get("totalCount", 0),
            "next_page_token": data.get("nextPageToken"),
        }

    async def get_trial(self, nct_id: str) -> ClinicalTrial | None:
        """Get a single trial by NCT ID."""
        try:
            resp = await self._client.get(f"/studies/{nct_id}")
            resp.raise_for_status()
            return self._parse_study(resp.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    def _parse_study(self, study: dict) -> ClinicalTrial:
        """Parse CT.gov API response into ClinicalTrial model."""
        proto = study.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        status_mod = proto.get("statusModule", {})
        design = proto.get("designModule", {})
        elig = proto.get("eligibilityModule", {})
        desc = proto.get("descriptionModule", {})
        cond_mod = proto.get("conditionsModule", {})
        arms = proto.get("armsInterventionsModule", {})
        contacts = proto.get("contactsLocationsModule", {})
        sponsor_mod = proto.get("sponsorCollaboratorsModule", {})

        # Parse eligibility criteria
        criteria_text = elig.get("eligibilityCriteria", "")
        inc_text, exc_text = self._split_criteria(criteria_text)

        # Parse sites
        sites = []
        for loc in contacts.get("locations", []):
            sites.append(TrialSite(
                facility=loc.get("facility", ""),
                city=loc.get("city", ""),
                state=loc.get("state", ""),
                country=loc.get("country", ""),
                zip_code=loc.get("zip", ""),
                latitude=loc.get("geoPoint", {}).get("lat"),
                longitude=loc.get("geoPoint", {}).get("lon"),
            ))

        # Parse interventions
        interventions = [
            i.get("name", "") for i in arms.get("interventions", [])
        ]

        # Phases
        phases = design.get("phases", [])
        phase_str = ", ".join(phases) if phases else None

        return ClinicalTrial(
            nct_id=ident.get("nctId", ""),
            brief_title=ident.get("briefTitle", ""),
            official_title=ident.get("officialTitle", ""),
            diseases=cond_mod.get("conditions", []),
            interventions=interventions,
            brief_summary=desc.get("briefSummary", ""),
            detailed_description=desc.get("detailedDescription", ""),
            phase=phase_str,
            status=status_mod.get("overallStatus"),
            enrollment=design.get("enrollmentInfo", {}).get("count"),
            sponsor=sponsor_mod.get("leadSponsor", {}).get("name", ""),
            start_date=status_mod.get("startDateStruct", {}).get("date"),
            completion_date=status_mod.get("completionDateStruct", {}).get("date"),
            inclusion_criteria=parse_criteria(inc_text, "inclusion"),
            exclusion_criteria=parse_criteria(exc_text, "exclusion"),
            raw_inclusion_text=inc_text,
            raw_exclusion_text=exc_text,
            min_age=elig.get("minimumAge"),
            max_age=elig.get("maximumAge"),
            sex=elig.get("sex"),
            sites=sites,
            source_registry="ctgov",
            source_url=f"https://clinicaltrials.gov/study/{ident.get('nctId', '')}",
        )

    def _split_criteria(self, text: str) -> tuple[str, str]:
        """Split combined criteria text into inclusion and exclusion."""
        text_lower = text.lower()

        exc_start = -1
        for marker in ["exclusion criteria", "exclusion criteria:"]:
            idx = text_lower.find(marker)
            if idx >= 0:
                exc_start = idx
                break

        if exc_start >= 0:
            inc_text = text[:exc_start].strip()
            exc_text = text[exc_start:].strip()
            # Remove header from inclusion
            for header in ["inclusion criteria:", "inclusion criteria"]:
                if inc_text.lower().startswith(header):
                    inc_text = inc_text[len(header):].strip()
            # Remove header from exclusion
            for header in ["exclusion criteria:", "exclusion criteria"]:
                if exc_text.lower().startswith(header):
                    exc_text = exc_text[len(header):].strip()
            return inc_text, exc_text

        return text, ""

    async def close(self) -> None:
        await self._client.aclose()
