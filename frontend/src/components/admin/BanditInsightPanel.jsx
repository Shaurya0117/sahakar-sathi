import { useState, useEffect } from 'react';
import api from '../../services/api';

export default function BanditInsightPanel() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.get('/ml/status')
      .then(r => setStats(r.data?.bandit))
      .catch(() => {});
  }, []);

  if (!stats) return null;

  return (
    <div style={{
      background: '#f0fdf4', border: '1px solid #86efac',
      borderRadius: 8, padding: '12px 16px', marginBottom: 16
    }}>
      <h4 style={{ margin: '0 0 8px', color: '#15803d', fontSize: '0.875rem' }}>
        🎰 Bandit Learning — Sequential Offer Escalation
      </h4>
      <div style={{ display: 'flex', gap: 24, fontSize: '0.8rem', color: '#166534' }}>
        <span><b>{stats.total_contexts}</b> trade×time contexts learned</span>
        <span><b>{stats.total_trials}</b> offer outcomes recorded</span>
        <span><b>{stats.n_arms}</b> offer ranks</span>
      </div>
    </div>
  );
}
