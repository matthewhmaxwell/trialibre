"""CSV export for batch results."""

from __future__ import annotations

import csv
import io

from ctm.models.matching import PatientTrialRanking


def export_rankings_csv(rankings: list[PatientTrialRanking]) -> str:
    """Export batch rankings to CSV format.

    Returns:
        CSV string with headers.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Patient ID",
        "Trial ID",
        "Trial Title",
        "Match Strength",
        "Combined Score",
        "Criteria Met",
        "Criteria Not Met",
        "Criteria Unknown",
        "Criteria Total",
        "Nearest Site (km)",
        "Drug Interaction Flags",
    ])

    for ranking in rankings:
        for score in ranking.scores:
            writer.writerow([
                ranking.patient_id,
                score.trial_id,
                score.trial_title,
                score.strength.value,
                f"{score.combined_score:.3f}",
                score.criteria_met,
                score.criteria_not_met,
                score.criteria_unknown,
                score.criteria_total,
                f"{score.nearest_site_distance_km:.1f}" if score.nearest_site_distance_km else "",
                "; ".join(score.drug_interaction_flags) if score.drug_interaction_flags else "",
            ])

    return output.getvalue()
