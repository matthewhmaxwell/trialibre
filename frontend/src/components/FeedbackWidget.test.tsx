/**
 * Smoke tests for FeedbackWidget.
 *
 * The widget is the loop closer for shipping — every "right/wrong/unsure"
 * verdict from a real clinician feeds the dataset we'll later use to
 * recalibrate prompts and thresholds. These tests pin three contracts:
 *  1. "Correct" submits immediately (one-click for the easy case).
 *  2. "Incorrect" / "Unsure" reveal the textarea so the user can write
 *     before the verdict is sent.
 *  3. The POST body includes the score context (strength, scores, criteria
 *     counts) so each row is self-contained for later drift analysis.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { FeedbackWidget } from './FeedbackWidget';
import type { TrialScore } from '../types/api';

function makeTrial(): TrialScore {
  return {
    trial_id: 'NCT-001',
    trial_title: 'Test trial',
    matching_score: 0.6,
    relevance_score: 0.9,
    eligibility_score: 0.7,
    combined_score: 0.75,
    strength: 'strong',
    relevance_explanation: '',
    eligibility_explanation: '',
    confidence: 0.9,
    criteria_met: 5,
    criteria_not_met: 1,
    criteria_excluded: 0,
    criteria_unknown: 4,
    criteria_total: 10,
    inclusion_results: [],
    exclusion_results: [],
    nearest_site_distance_km: null,
    nearest_site_name: '',
    drug_interaction_flags: [],
  };
}

describe('FeedbackWidget', () => {
  beforeEach(() => {
    vi.spyOn(window, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ feedback_id: 'fb-test' }), { status: 201 }),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('submits "correct" immediately on click with no note', async () => {
    const user = userEvent.setup();
    render(<FeedbackWidget patientId="P-001" trial={makeTrial()} />);

    await user.click(screen.getByText('feedback.correct'));

    await waitFor(() => {
      expect(window.fetch).toHaveBeenCalledTimes(1);
    });
    const [, init] = (window.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse((init as RequestInit).body as string);

    expect(body.patient_id).toBe('P-001');
    expect(body.trial_id).toBe('NCT-001');
    expect(body.feedback_type).toBe('correct');
    expect(body.notes).toBe('');
    // Score context attached so this row is self-contained for analysis.
    expect(body.data.combined_score).toBe(0.75);
    expect(body.data.strength).toBe('strong');
    expect(body.data.criteria_met).toBe(5);

    expect(await screen.findByText(/feedback\.thanks/)).toBeInTheDocument();
  });

  it('reveals the textarea when "incorrect" is picked, sends with the note', async () => {
    const user = userEvent.setup();
    render(<FeedbackWidget patientId="P-001" trial={makeTrial()} />);

    // No textarea yet.
    expect(screen.queryByPlaceholderText('feedback.notes_placeholder')).not.toBeInTheDocument();
    expect(window.fetch).not.toHaveBeenCalled();

    await user.click(screen.getByText('feedback.incorrect'));

    // Now the textarea + Send button are visible; nothing has been sent yet.
    const textarea = screen.getByPlaceholderText('feedback.notes_placeholder');
    expect(textarea).toBeInTheDocument();
    expect(window.fetch).not.toHaveBeenCalled();

    await user.type(textarea, 'Patient is too young for this trial.');
    await user.click(screen.getByText('feedback.send'));

    await waitFor(() => expect(window.fetch).toHaveBeenCalledTimes(1));
    const [, init] = (window.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.feedback_type).toBe('incorrect');
    expect(body.notes).toBe('Patient is too young for this trial.');
  });

  it('shows an error when the POST fails, doesn\'t hide the verdict buttons', async () => {
    const user = userEvent.setup();
    vi.spyOn(window, 'fetch').mockResolvedValue(
      new Response('boom', { status: 500 }),
    );

    render(<FeedbackWidget patientId="P-001" trial={makeTrial()} />);
    await user.click(screen.getByText('feedback.correct'));

    expect(await screen.findByText(/feedback\.error/)).toBeInTheDocument();
    // Verdict buttons should still be visible so the user can retry.
    expect(screen.getByText('feedback.correct')).toBeInTheDocument();
  });
});
