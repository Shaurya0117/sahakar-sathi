/**
 * ReviewAuditBadge — Displays ML Isolation Forest review integrity audit status.
 * Props:
 *  - anomalyScore: number (0.0 to 1.0)
 *  - riskLevel: "NORMAL" | "SUSPICIOUS" | "ANOMALOUS"
 */
export default function ReviewAuditBadge({ anomalyScore, riskLevel }) {
  if (anomalyScore == null && !riskLevel) return null;

  const score = anomalyScore ?? 0.0;
  const level = riskLevel ?? (score >= 0.65 ? 'ANOMALOUS' : score >= 0.50 ? 'SUSPICIOUS' : 'NORMAL');

  if (level === 'ANOMALOUS') {
    return (
      <span style={{
        background: '#fef2f2', color: '#b91c1c',
        border: '1px solid #fca5a5',
        padding: '2px 8px', borderRadius: '9999px',
        fontSize: '0.72rem', fontWeight: 700,
        display: 'inline-flex', alignItems: 'center', gap: '4px'
      }}>
        🚨 Anomaly Flagged ({Math.round(score * 100)}%)
      </span>
    );
  }

  if (level === 'SUSPICIOUS') {
    return (
      <span style={{
        background: '#fffbeb', color: '#b45309',
        border: '1px solid #fde68a',
        padding: '2px 8px', borderRadius: '9999px',
        fontSize: '0.72rem', fontWeight: 600,
        display: 'inline-flex', alignItems: 'center', gap: '4px'
      }}>
        ⚠️ Review Under Audit ({Math.round(score * 100)}%)
      </span>
    );
  }

  return (
    <span style={{
      background: '#f0fdf4', color: '#15803d',
      border: '1px solid #bbf7d0',
      padding: '2px 8px', borderRadius: '9999px',
      fontSize: '0.72rem', fontWeight: 600,
      display: 'inline-flex', alignItems: 'center', gap: '4px'
    }}>
      ✓ Verified Authentic
    </span>
  );
}
