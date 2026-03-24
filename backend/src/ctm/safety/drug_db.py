"""Drug database integration using RxNorm and OpenFDA.

Checks for drug interactions between patient medications and
trial interventions/exclusion criteria.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

OPENFDA_BASE = "https://api.fda.gov/drug"
RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"


class DrugDatabase:
    """Query drug information from RxNorm and OpenFDA."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0)

    async def get_interactions(self, drug_names: list[str]) -> list[dict]:
        """Get known interactions between a list of drugs.

        Args:
            drug_names: List of drug names.

        Returns:
            List of interaction dicts with severity and description.
        """
        if len(drug_names) < 2:
            return []

        interactions = []
        # Get RxCUI for each drug
        rxcuis = []
        for name in drug_names:
            rxcui = await self._get_rxcui(name)
            if rxcui:
                rxcuis.append((name, rxcui))

        if len(rxcuis) < 2:
            return []

        # Check interactions via RxNorm
        cui_list = "+".join(cui for _, cui in rxcuis)
        try:
            resp = await self._client.get(
                f"{RXNORM_BASE}/interaction/list.json",
                params={"rxcuis": cui_list},
            )
            if resp.status_code == 200:
                data = resp.json()
                for group in data.get("fullInteractionTypeGroup", []):
                    for itype in group.get("fullInteractionType", []):
                        for pair in itype.get("interactionPair", []):
                            interactions.append({
                                "severity": pair.get("severity", "unknown"),
                                "description": pair.get("description", ""),
                                "drugs": [
                                    c.get("minConceptItem", {}).get("name", "")
                                    for c in pair.get("interactionConcept", [])
                                ],
                            })
        except Exception as e:
            logger.warning(f"RxNorm interaction check failed: {e}")

        return interactions

    async def _get_rxcui(self, drug_name: str) -> str | None:
        """Look up RxCUI for a drug name."""
        try:
            resp = await self._client.get(
                f"{RXNORM_BASE}/rxcui.json",
                params={"name": drug_name, "search": 1},
            )
            if resp.status_code == 200:
                data = resp.json()
                ids = data.get("idGroup", {}).get("rxnormId", [])
                return ids[0] if ids else None
        except Exception as e:
            logger.debug(f"RxCUI lookup failed for {drug_name}: {e}")
        return None

    async def close(self) -> None:
        await self._client.aclose()
