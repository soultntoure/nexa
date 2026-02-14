/** Shared helpers for audit UI components. */

const SOURCE_LABELS: Record<string, string> = {
  constellation_analysis: 'Triage Constellation',
  cross_account: 'Cross-Account Analysis',
  financial_behavior: 'Financial Behavior',
  identity_access: 'Identity & Access',
  triage: 'Triage Analysis',
  investigator: 'Investigator Finding',
  supporting: 'Supporting Evidence',
  sql_trace: 'SQL Trace',
  web_trace: 'Web Trace',
}

/** Map raw source key to a human-friendly label. */
export function friendlySourceLabel(source: string): string {
  const normalized = source.trim().toLowerCase()
  if (SOURCE_LABELS[normalized]) return SOURCE_LABELS[normalized]
  return source
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

interface Severity {
  label: string
  class: string
  badgeClass: string
}

/** Derive severity tier from confidence score. */
export function severityFromConfidence(confidence: number): Severity {
  if (confidence >= 0.8) return {
    label: 'Critical',
    class: 'bg-red-100 text-red-700',
    badgeClass: 'bg-red-100 text-red-700',
  }
  if (confidence >= 0.6) return {
    label: 'High',
    class: 'bg-orange-100 text-orange-700',
    badgeClass: 'bg-orange-100 text-orange-700',
  }
  if (confidence >= 0.4) return {
    label: 'Medium',
    class: 'bg-yellow-100 text-yellow-700',
    badgeClass: 'bg-yellow-100 text-yellow-700',
  }
  return {
    label: 'Low',
    class: 'bg-gray-100 text-gray-600',
    badgeClass: 'bg-gray-100 text-gray-600',
  }
}

/** Human-readable explanation of what confidence means. */
export function confidenceExplainer(confidence: number): string {
  if (confidence >= 0.8) return 'Very strong evidence this is real fraud'
  if (confidence >= 0.6) return 'Strong evidence — likely fraudulent activity'
  if (confidence >= 0.4) return 'Moderate evidence — needs officer review'
  return 'Weak signal — may be legitimate activity'
}

/** Human-readable explanation of what quality means. */
export function qualityExplainer(quality: number): string {
  if (quality >= 0.8) return 'Rich evidence from multiple independent sources'
  if (quality >= 0.6) return 'Good evidence with corroborating signals'
  if (quality >= 0.4) return 'Limited evidence — based on fewer data points'
  return 'Thin evidence — treat as preliminary'
}
