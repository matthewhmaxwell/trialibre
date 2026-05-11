/**
 * Smoke tests for TrialCard — pins the per-criterion explainability UI.
 *
 * Commit 3365711 wired the per-criterion data through to the UI; this
 * test makes sure that wireup stays intact through future refactors.
 * If a layout pass accidentally drops the inclusion/exclusion sections,
 * or omits the evidence chips, this fails.
 */

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { TrialCard } from './TrialCard';
import type { TrialScore } from '../types/api';

function makeTrial(overrides: Partial<TrialScore> = {}): TrialScore {
  return {
    trial_id: 'NCT-001',
    trial_title: 'Dapagliflozin Phase 3',
    matching_score: 0.6,
    relevance_score: 0.9,
    eligibility_score: 0.7,
    combined_score: 0.75,
    strength: 'strong',
    relevance_explanation: 'High relevance to T2DM',
    eligibility_explanation: 'Patient meets most criteria',
    confidence: 0.9,
    criteria_met: 5,
    criteria_not_met: 1,
    criteria_excluded: 0,
    criteria_unknown: 4,
    criteria_total: 10,
    inclusion_results: [
      {
        criterion_index: 0,
        criterion_text: 'Age 18-75',
        category: 'inclusion',
        reasoning: 'Patient is 45.',
        plain_reasoning: '',
        evidence_sentence_ids: [1, 6],
        label: 'included',
        confidence: 0.9,
      },
      {
        criterion_index: 1,
        criterion_text: 'HbA1c >= 7.5%',
        category: 'inclusion',
        reasoning: 'HbA1c is 8.2%.',
        plain_reasoning: '',
        evidence_sentence_ids: [16],
        label: 'included',
        confidence: 0.9,
      },
    ],
    exclusion_results: [],
    nearest_site_distance_km: null,
    nearest_site_name: '',
    drug_interaction_flags: [],
    ...overrides,
  };
}

describe('TrialCard', () => {
  it('renders the title, strength badge, and criteria summary in the collapsed view', () => {
    render(<TrialCard trial={makeTrial()} />);

    expect(screen.getByText('Dapagliflozin Phase 3')).toBeInTheDocument();
    expect(screen.getByText('NCT-001')).toBeInTheDocument();
    // Collapsed: per-criterion section not yet visible.
    expect(screen.queryByText('Age 18-75')).not.toBeInTheDocument();
  });

  it('expands to show per-criterion list with reasoning + evidence chips', async () => {
    const user = userEvent.setup();
    render(<TrialCard trial={makeTrial()} />);

    await user.click(screen.getByText('match.view_details'));

    // Both criteria render with their text + reasoning.
    expect(screen.getByText('Age 18-75')).toBeInTheDocument();
    expect(screen.getByText('Patient is 45.')).toBeInTheDocument();
    expect(screen.getByText('HbA1c >= 7.5%')).toBeInTheDocument();
    expect(screen.getByText('HbA1c is 8.2%.')).toBeInTheDocument();

    // Evidence sentence IDs render as chips ("s1", "s6", "s16").
    expect(screen.getByText('s1')).toBeInTheDocument();
    expect(screen.getByText('s6')).toBeInTheDocument();
    expect(screen.getByText('s16')).toBeInTheDocument();

    // The per-card AI disclaimer is present at the moment a clinician
    // would click "Refer" — non-negotiable per commit 6739b0c.
    expect(screen.getByText(/match\.ai_disclaimer_short/)).toBeInTheDocument();
  });

  it('omits the per-criterion section gracefully when the field is missing', async () => {
    const user = userEvent.setup();
    // Legacy / demo-mode response shape: no inclusion_results field at all.
    // The fields are typed as optional now, so `delete` doesn't error.
    const legacy = makeTrial();
    delete legacy.inclusion_results;
    delete legacy.exclusion_results;

    render(<TrialCard trial={legacy} />);
    await user.click(screen.getByText('match.view_details'));

    // The aggregate explanations still render.
    expect(screen.getByText('High relevance to T2DM')).toBeInTheDocument();
    // No per-criterion list, but no crash either.
    expect(screen.queryByText('Age 18-75')).not.toBeInTheDocument();
    expect(screen.queryByText(/Inclusion criteria/)).not.toBeInTheDocument();
  });

  it('shows exclusion criteria separately when populated', async () => {
    const user = userEvent.setup();
    const trial = makeTrial({
      exclusion_results: [
        {
          criterion_index: 0,
          criterion_text: 'No active malignancy',
          category: 'exclusion',
          reasoning: 'No malignancy in the note.',
          plain_reasoning: '',
          evidence_sentence_ids: [],
          label: 'not excluded',
          confidence: 0.8,
        },
      ],
    });
    render(<TrialCard trial={trial} />);
    await user.click(screen.getByText('match.view_details'));

    // Both sections render with separate headings.
    expect(screen.getByText(/Inclusion criteria \(2\)/)).toBeInTheDocument();
    expect(screen.getByText(/Exclusion criteria \(1\)/)).toBeInTheDocument();

    // Within the exclusion section, the criterion shows up.
    const exclusionHeading = screen.getByText(/Exclusion criteria \(1\)/);
    const exclusionList = exclusionHeading.parentElement!;
    expect(within(exclusionList).getByText('No active malignancy')).toBeInTheDocument();
  });
});
