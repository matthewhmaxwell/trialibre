/**
 * Demo Mode API Interceptor
 *
 * When demo mode is active, intercepts all /api/v1/* fetch calls
 * and returns pre-built responses from bundled sandbox data.
 * No backend server required — works as pure static files.
 */

import demoData from './demoData.json';

let _demoMode = false;
const _originalFetch = window.fetch;

export function isDemoMode(): boolean {
  return _demoMode;
}

export function activateDemoMode(): void {
  if (_demoMode) return;
  _demoMode = true;

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;

    // Only intercept /api/v1/* requests
    if (!url.includes('/api/v1/')) {
      return _originalFetch(input, init);
    }

    // Simulate network delay
    await new Promise(r => setTimeout(r, 200 + Math.random() * 300));

    const path = url.replace(/.*\/api\/v1/, '');
    const method = init?.method?.toUpperCase() || 'GET';

    try {
      const response = routeRequest(path, method, init);
      return new Response(JSON.stringify(response), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    } catch (e) {
      return new Response(JSON.stringify({ detail: (e as Error).message }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  };

  console.log('[Trialibre Demo] Demo mode activated — using sample data, no backend required');
}

function routeRequest(path: string, method: string, init?: RequestInit): unknown {
  // Health
  if (path === '/health') {
    return {
      status: 'ok',
      version: '0.1.0',
      llm_provider: 'demo',
      llm_connected: false,
      sandbox_mode: true,
      trial_count: demoData.trials.length,
      database_backend: 'demo',
      demo_mode: true,
    };
  }

  // Privacy
  if (path === '/privacy/status') {
    return {
      label: 'Demo',
      color: 'green',
      details: ['This is a demo — no real patient data is processed', 'All data is synthetic and stays in your browser'],
      deid_active: false,
      processing_location: 'browser',
    };
  }

  // Settings
  if (path === '/settings') {
    return {
      llm_provider: 'demo',
      llm_model: 'demo-mode',
      api_key: '',
      base_url: '',
      language: 'en',
      sandbox_mode: true,
      privacy_level: 'maximum',
      deid_mode: 'auto',
    };
  }

  // Trials list
  if (path === '/trials' && method === 'GET') {
    return demoData.trials;
  }

  // Sandbox patients
  if (path === '/sandbox/patients' && method === 'GET') {
    return demoData.patients;
  }

  // Sandbox protocols
  if (path === '/sandbox/protocols' && method === 'GET') {
    return demoData.trials;
  }

  // Sandbox scenarios
  if (path === '/sandbox/scenarios' && method === 'GET') {
    return [];
  }

  // Dashboard
  if (path.startsWith('/dashboard')) {
    return {
      total_matches: 47,
      total_referrals: 12,
      avg_match_score: 0.72,
      top_trials: demoData.trials.slice(0, 3).map(t => ({
        trial_id: t.nct_id, title: t.brief_title, match_count: Math.floor(Math.random() * 10 + 3),
      })),
      recent_matches: demoData.patients.slice(0, 5).map(p => ({
        patient_id: p.patient_id, timestamp: new Date().toISOString(),
        strong: Math.floor(Math.random() * 3 + 1), possible: Math.floor(Math.random() * 3),
      })),
      ta_distribution: {},
    };
  }

  // Referrals
  if (path === '/referrals') {
    return [];
  }

  // Audit
  if (path === '/audit') {
    return { entries: [], total: 0, chain_valid: true };
  }

  // Match
  if (path === '/match' && method === 'POST') {
    const body = JSON.parse(init?.body as string || '{}');
    const patientText = (body.patient_text || '').toLowerCase();

    // Find the best matching sandbox patient based on keyword overlap
    let bestMatch = 'SAMPLE-001';
    let bestScore = 0;

    const keywords: Record<string, string[]> = {
      'SAMPLE-001': ['diabetes', 'hba1c', 'metformin', 'type 2', 't2dm', 'glucose', 'bmi'],
      'SAMPLE-002': ['lung', 'nsclc', 'cancer', 'pd-l1', 'ecog', 'adenocarcinoma', 'carboplatin'],
      'SAMPLE-003': ['breast', 'her2', 'trastuzumab', 'lumpectomy', 'liver met'],
      'SAMPLE-004': ['alzheimer', 'cognitive', 'mmse', 'donepezil', 'dementia'],
      'SAMPLE-005': ['hiv', 'cd4', 'viral load', 'treatment-naive', 'antiretroviral'],
      'SAMPLE-006': ['kidney', 'ckd', 'egfr', 'nephropathy', 'creatinine'],
      'SAMPLE-007': ['asthma', 'inhaler', 'pediatric', 'fluticasone', 'wheezing'],
      'SAMPLE-008': ['depression', 'ssri', 'phq', 'antidepressant', 'treatment-resistant'],
      'SAMPLE-009': ['sickle cell', 'hbss', 'vaso-occlusive', 'hydroxyurea'],
      'SAMPLE-010': ['rheumatoid', 'arthritis', 'das28', 'methotrexate', 'joint'],
      'SAMPLE-011': ['malaria', 'falciparum', 'parasite', 'anemia', 'artesunate'],
      'SAMPLE-012': ['tuberculosis', 'tb', 'mdr', 'isoniazid', 'rifampicin', 'sputum'],
    };

    for (const [pid, kws] of Object.entries(keywords)) {
      const score = kws.filter(kw => patientText.includes(kw)).length;
      if (score > bestScore) {
        bestScore = score;
        bestMatch = pid;
      }
    }

    const result = demoData.match_results[bestMatch as keyof typeof demoData.match_results];
    if (result) {
      return { ...result, patient_id: body.patient_id || 'demo-patient' };
    }

    // Fallback to first patient's results
    return { ...Object.values(demoData.match_results)[0], patient_id: 'demo-patient' };
  }

  // Ingest trial (stub for demo)
  if (path.startsWith('/ingest/trial')) {
    return {
      nct_id: 'DEMO-UPLOAD',
      brief_title: 'Demo Upload (not functional in demo mode)',
      inclusion_count: 0,
      exclusion_count: 0,
      extraction_method: 'demo',
      confidence: 'none',
      source_format: 'demo',
      warnings: ['Protocol upload is not available in demo mode. Install Trialibre locally to use this feature.'],
    };
  }

  // Batch (stub for demo)
  if (path === '/batch' && method === 'POST') {
    return {
      job_id: 'demo-batch',
      status: 'completed',
      total: 0,
      completed: 0,
      failed: 0,
      results: [],
      message: 'Batch processing is not available in demo mode. Install Trialibre locally to use this feature.',
    };
  }

  throw new Error(`Demo mode: endpoint ${path} not available`);
}

/**
 * Auto-detect demo mode:
 * - If URL has ?demo=true
 * - If we're not on localhost (deployed to static hosting)
 */
export function shouldActivateDemo(): boolean {
  const params = new URLSearchParams(window.location.search);
  if (params.get('demo') === 'true') return true;

  // If not on localhost, we're probably on static hosting with no backend
  const host = window.location.hostname;
  if (host !== 'localhost' && host !== '127.0.0.1' && !host.includes('192.168.')) {
    return true;
  }

  return false;
}
