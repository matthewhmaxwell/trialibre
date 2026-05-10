/** TypeScript types matching the backend Pydantic models. */

export type MatchStrength = 'strong' | 'possible' | 'unlikely';

export type EligibilityLabel =
  | 'included'
  | 'not included'
  | 'excluded'
  | 'not excluded'
  | 'not applicable'
  | 'not enough information';

export interface TrialScore {
  trial_id: string;
  trial_title: string;
  matching_score: number;
  relevance_score: number;
  eligibility_score: number;
  combined_score: number;
  strength: MatchStrength;
  relevance_explanation: string;
  eligibility_explanation: string;
  confidence: number;
  criteria_met: number;
  criteria_not_met: number;
  criteria_excluded: number;
  criteria_unknown: number;
  criteria_total: number;
  // Per-criterion details — populated for any match result produced by a
  // recent backend; may be absent on legacy or demo-mode responses, which
  // is why the field is optional. The TrialCard expanded view uses these
  // to render the "criterion-level explainability" promise.
  inclusion_results?: CriterionResult[];
  exclusion_results?: CriterionResult[];
  nearest_site_distance_km: number | null;
  nearest_site_name: string;
  drug_interaction_flags: string[];
}

export interface DeIdSummary {
  applied: boolean;
  processing_location: 'local' | 'cloud';
  entities_removed: string[];
  validation_flags: string[];
}

export interface MatchResponse {
  patient_id: string;
  rankings: TrialScore[];
  strong_count: number;
  possible_count: number;
  unlikely_count: number;
  total_trials_screened: number;
  retrieval_time_ms: number;
  matching_time_ms: number;
  ranking_time_ms: number;
  sandbox_mode: boolean;
  warnings?: string[];
  // Privacy-gate outcome from the /match response. Optional because
  // older backends and demo-mode fixtures don't have it; new backends
  // always do (default `{ applied: false, processing_location: 'local',
  // entities_removed: [], validation_flags: [] }`).
  deid?: DeIdSummary;
}

export interface HealthResponse {
  status: string;
  version: string;
  llm_provider: string;
  llm_connected: boolean;
  sandbox_mode: boolean;
  trial_count: number;
  database_backend: string;
  warnings?: string[];
  capabilities?: Record<string, boolean>;
}

export interface PrivacyStatus {
  label: string;
  color: 'green' | 'blue' | 'yellow';
  details: string[];
  deid_active: boolean;
  processing_location: string;
}

export interface SandboxPatient {
  patient_id: string;
  age: number | null;
  sex: string | null;
  diagnoses: string[];
  language: string;
}

export interface SandboxTrial {
  nct_id: string;
  brief_title: string;
  diseases: string[];
  phase: string | null;
  status: string | null;
}

export interface DemoScenario {
  id: string;
  title: string;
  description: string;
  patient_id: string;
  highlights: string[];
}

export interface CriterionResult {
  criterion_index: number;
  criterion_text: string;
  category: 'inclusion' | 'exclusion';
  reasoning: string;
  plain_reasoning: string;
  evidence_sentence_ids: number[];
  label: string;
  confidence: number;
}

export type MatchFilter = 'all' | 'strong' | 'possible' | 'unlikely';
export type InputTab = 'type' | 'upload' | 'photo';
