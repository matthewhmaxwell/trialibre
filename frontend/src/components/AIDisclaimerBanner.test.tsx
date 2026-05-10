/**
 * Smoke tests for the AI disclaimer banner.
 *
 * The banner is the project's most important UI safety surface — see
 * commit 6739b0c for the rationale. These tests pin two contracts:
 *  1. The banner renders with role="alert" and the title/body text
 *     keys (so a wording change is intentional, not accidental).
 *  2. Dismissal works AND persists per session via sessionStorage,
 *     so a user who dismissed it doesn't see it pop back on the next
 *     match within the same tab.
 *
 * If either test fails, a clinician using the system might miss the
 * "AI-generated, verify before clinical use" warning at the moment of
 * a referral — which is the whole reason the banner exists.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { AIDisclaimerBanner } from './AIDisclaimerBanner';

describe('AIDisclaimerBanner', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('renders an alert with the disclaimer title and body text', () => {
    render(<AIDisclaimerBanner />);

    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveTextContent('match.ai_disclaimer_banner_title');
    expect(alert).toHaveTextContent('match.ai_disclaimer_banner_body');
  });

  it('disappears after the user dismisses it and stays hidden on remount', async () => {
    const user = userEvent.setup();
    const { unmount } = render(<AIDisclaimerBanner />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    await user.click(screen.getByLabelText('Dismiss'));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();

    // Remount as if the user navigated away and came back during the
    // same tab — the dismissal must survive.
    unmount();
    render(<AIDisclaimerBanner />);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('reappears in a fresh session (sessionStorage cleared)', () => {
    sessionStorage.setItem('trialibre.ai_disclaimer.dismissed', '1');
    const { unmount } = render(<AIDisclaimerBanner />);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();

    unmount();
    sessionStorage.clear();
    render(<AIDisclaimerBanner />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});
