import { useState, useEffect } from 'react';
import type { PrivacyStatus, HealthResponse } from '../types/api';

export function useSettings() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [privacy, setPrivacy] = useState<PrivacyStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const safeFetch = async (url: string) => {
      try {
        const r = await fetch(url);
        if (!r.ok) return null;
        const data = await r.json();
        return data;
      } catch {
        return null;
      }
    };
    Promise.all([safeFetch('/api/v1/health'), safeFetch('/api/v1/privacy/status')])
      .then(([h, p]) => {
        setHealth(h && h.status ? h : null);
        setPrivacy(p && p.label && p.color ? p : null);
        setLoading(false);
      });
  }, []);

  return { health, privacy, loading };
}
