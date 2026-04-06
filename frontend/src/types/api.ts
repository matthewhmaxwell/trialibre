/** TypeScript types matching the backend Pydantic models. */

export type MatchStrength = 'strong' | 'possible' | 'unlikely';

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
  nearest_site_distance_km: number | null;
  nearest_site_name: string;
  drug_interaction_flags: string[];
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
}

export interface HealthResponse {
  status: string;
  version: string;
  llm_provider: string;
  llm_connected: boolean;
  sandbox_mode: boolean;
  trial_count: number;
  database_backend: string;
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
