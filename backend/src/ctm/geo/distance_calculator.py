"""Geographic distance calculation for trial site matching.

Uses Haversine formula (approximate great-circle distance).
"""

from __future__ import annotations

import math

from ctm.models.trial import ClinicalTrial, TrialSite


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in km."""
    R = 6371.0  # Earth radius in km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def find_nearest_site(
    patient_lat: float,
    patient_lon: float,
    trial: ClinicalTrial,
) -> tuple[TrialSite | None, float | None]:
    """Find the nearest trial site to a patient location.

    Returns:
        Tuple of (nearest site, distance in km). Both None if no sites have coords.
    """
    nearest: TrialSite | None = None
    min_dist: float | None = None

    for site in trial.sites:
        if site.latitude is not None and site.longitude is not None:
            dist = haversine_km(patient_lat, patient_lon, site.latitude, site.longitude)
            if min_dist is None or dist < min_dist:
                min_dist = dist
                nearest = site

    return nearest, min_dist


def filter_trials_by_distance(
    patient_lat: float,
    patient_lon: float,
    trials: list[ClinicalTrial],
    max_distance_km: float,
) -> list[tuple[ClinicalTrial, float]]:
    """Filter trials to those within a maximum distance.

    Returns:
        List of (trial, distance_km) tuples for trials within range.
    """
    results = []
    for trial in trials:
        _, dist = find_nearest_site(patient_lat, patient_lon, trial)
        if dist is not None and dist <= max_distance_km:
            results.append((trial, dist))

    return sorted(results, key=lambda x: x[1])
