const NONCE_KEY = 'proof_nonce';
const QUEUE_KEY = 'proof_queue';

export async function refreshNonce(api) {
  try {
    const path = (api && api.defaults && api.defaults.baseURL && api.defaults.baseURL.includes('/api')) ? '/proof/nonce' : '/api/proof/nonce';
    const data = await api.get(path).then(r => r.data);
    localStorage.setItem(NONCE_KEY, JSON.stringify({ ...data, fetchedAt: new Date().toISOString() }));
    return data;
  } catch (e) {
    return null;
  }
}

export function getCachedNonce() {
  const raw = localStorage.getItem(NONCE_KEY);
  if (!raw) return null;
  try {
    const data = JSON.parse(raw);
    const ageDays = (Date.now() - new Date(data.fetchedAt).getTime()) / 86400000;
    if (ageDays > 2) return null;
    return data;
  } catch (e) {
    return null;
  }
}

export function enqueueProof(item) {
  const queue = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
  queue.push(item);
  localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
}

export function getQueue() {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
  } catch (e) {
    return [];
  }
}

export async function flushQueue(submitFn) {
  const queue = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
  if (queue.length === 0) return;
  const remaining = [];
  for (const item of queue) {
    try {
      await submitFn(item);
      // success: don't add back
    } catch (e) {
      if (e.response && e.response.status >= 400 && e.response.status < 500 && e.response.status !== 401) {
        // 4xx except 401: show error, drop from queue
        console.error('Proof queue item rejected:', e.response.data);
      } else {
        remaining.push(item); // network error or 401: keep
      }
    }
  }
  localStorage.setItem(QUEUE_KEY, JSON.stringify(remaining));
}
