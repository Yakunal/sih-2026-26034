/*
  types.ts — the shape of everything the backend sends us.

  These mirror backend/models.py one-for-one. If you change a Pydantic model
  there, change the matching type here.
*/

/** What the AI read off the label. Every field can be null: a declaration that
 *  is not visible in the photograph comes back as null, never as a guess. */
export interface ExtractedData {
  product_name: string | null
  common_generic_name: string | null
  manufacturer_name: string | null
  manufacturer_address: string | null
  packer_name: string | null
  importer_name: string | null
  net_quantity: string | null
  mrp: string | null
  mrp_text_verbatim: string | null
  date_of_packing: string | null
  consumer_care: string | null
  country_of_origin: string | null
  image_quality: string | null
  all_declarations_legible: boolean | null
  overall_confidence: number | null
  notes: string | null
}

export type CheckResult = 'PASS' | 'FAIL' | 'REVIEW' | 'NOT_APPLICABLE'
export type Status = 'COMPLIANT' | 'NEEDS_REVIEW' | 'POTENTIAL_VIOLATION'

/** One rule, and what the rule engine concluded about it. */
export interface RuleCheck {
  rule_id: string
  rule_reference: string
  name: string
  requirement: string
  check_type: string
  weight: number
  result: CheckResult
  observed: string | null
  reason: string
  escalates: boolean
  citation_verified: boolean
}

export interface ComplianceResult {
  score: number
  status: Status
  status_reason: string
  passed: number
  failed: number
  review: number
  not_applicable: number
  checks: RuleCheck[]
}

/** Where a result's extraction came from. Shown in the UI so a cached demo
 *  reading is never mistaken for a fresh AI analysis. */
export type Source = 'live_ai' | 'demo_cached' | 'seed'

export interface InspectionSummary {
  id: number
  product_name: string
  manufacturer: string
  scan_date: string
  score: number
  status: Status
  source: Source
}

export interface InspectionDetail extends InspectionSummary {
  image_url: string | null
  extracted: ExtractedData
  compliance: ComplianceResult
  explanation: string | null
  model_used: string | null
}

export interface ScanResponse {
  inspection: InspectionDetail
  /** True when the extraction step was cached. The rule engine always ran live. */
  is_demo: boolean
}

export interface ViolationCount {
  rule_id: string
  name: string
  count: number
}

export interface Stats {
  total: number
  compliant: number
  needs_review: number
  potential_violations: number
  compliance_percentage: number
  average_score: number
  includes_sample_data: boolean
  common_violations: ViolationCount[]
  recent: InspectionSummary[]
}

export interface Health {
  status: string
  ai_configured: boolean
  model: string
  rules_loaded: number
  message: string
}

export interface DemoProduct {
  id: string
  label: string
  description: string
  expected_status: Status
  image_url: string
}

/** One rule as it is written in backend/rules.json. */
export interface Rule {
  id: string
  rule_reference: string
  name: string
  requirement: string
  check: string
  field: string
  alt_fields: string[]
  pattern: string | null
  trigger_field: string | null
  weight: number
  escalates: boolean
  source: string
  citation_verified: boolean
}

export interface RulesResponse {
  total: number
  scoreable: number
  manual: number
  unverified_citations: number
  scoring_formula: string
  rules: Rule[]
}
