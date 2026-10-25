/**
 * DurationBadge — Shows ML-predicted duration for a booking.
 * Props: serviceType (string), estimatedHours (number, may be null)
 */
export default function DurationBadge({ serviceType, estimatedHours }) {
  if (!estimatedHours) return null;
  const h = Math.floor(estimatedHours);
  const m = Math.round((estimatedHours - h) * 60);
  const label = h > 0 ? `~${h}h ${m > 0 ? m + 'm' : ''}`.trim() : `~${m}m`;
  return (
    <span style={{
      background: '#e0f2fe', color: '#0369a1',
      padding: '2px 8px', borderRadius: '9999px',
      fontSize: '0.75rem', fontWeight: 600,
      display: 'inline-flex', alignItems: 'center', gap: '4px'
    }}>
      ⏱ {label}
    </span>
  );
}
