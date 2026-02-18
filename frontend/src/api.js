const BASE = '';

// ── Token management ──
let _token = localStorage.getItem('jarvis_token') || '';

export function setToken(token) {
  _token = token;
  if (token) localStorage.setItem('jarvis_token', token);
  else localStorage.removeItem('jarvis_token');
}

export function getToken() { return _token; }

function authHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (_token) h['Authorization'] = `Bearer ${_token}`;
  return h;
}

// ── Auth API ──

export async function apiRegister(username, password, email, displayName) {
  const res = await fetch(`${BASE}/api/auth/register`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password, email: email || null, display_name: displayName || '' }),
  });
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Registration failed'); }
  const data = await res.json();
  setToken(data.token);
  return data;
}

export async function apiLogin(username, password) {
  const res = await fetch(`${BASE}/api/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Login failed'); }
  const data = await res.json();
  setToken(data.token);
  return data;
}

export async function apiGoogleLogin(credential) {
  const res = await fetch(`${BASE}/api/auth/google`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ credential }),
  });
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Google login failed'); }
  const data = await res.json();
  setToken(data.token);
  return data;
}

export async function apiGuest() {
  const res = await fetch(`${BASE}/api/auth/guest`, { method: 'POST' });
  if (!res.ok) throw new Error('Guest login failed');
  const data = await res.json();
  setToken(data.token);
  return data;
}

export async function apiGetMe() {
  const res = await fetch(`${BASE}/api/auth/me`, { headers: authHeaders() });
  if (!res.ok) return null;
  return res.json();
}

export async function apiUpgradeGuest(username, password, email, displayName) {
  const res = await fetch(`${BASE}/api/auth/upgrade-guest`, {
    method: 'POST', headers: authHeaders(),
    body: JSON.stringify({ username, password, email: email || null, display_name: displayName || '' }),
  });
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Upgrade failed'); }
  const data = await res.json();
  setToken(data.token);
  return data;
}

export function apiLogout() {
  setToken('');
}

// ── User Memory API ──

export async function getUserFacts(category) {
  const q = category ? `?category=${encodeURIComponent(category)}` : '';
  const res = await fetch(`${BASE}/api/user/facts${q}`, { headers: authHeaders() });
  if (!res.ok) return [];
  return res.json();
}

export async function learnFact(key, value, category = 'general') {
  const res = await fetch(`${BASE}/api/user/facts`, {
    method: 'POST', headers: authHeaders(),
    body: JSON.stringify({ key, value, category }),
  });
  if (!res.ok) throw new Error('Failed to learn fact');
  return res.json();
}

export async function deleteFact(factId) {
  const res = await fetch(`${BASE}/api/user/facts/${factId}`, {
    method: 'DELETE', headers: authHeaders(),
  });
  return res.ok;
}

export async function getUserConversations(limit = 50) {
  const res = await fetch(`${BASE}/api/user/conversations?limit=${limit}`, { headers: authHeaders() });
  if (!res.ok) return [];
  return res.json();
}

// ── Chat API (with auth token) ──

export async function sendChat(sessionId, message) {
  const res = await fetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  return res.json();
}

export async function getState(sessionId) {
  const res = await fetch(`${BASE}/api/state?session_id=${encodeURIComponent(sessionId)}`);
  if (!res.ok) throw new Error(`State failed: ${res.status}`);
  return res.json();
}

export async function getMemory(sessionId) {
  const res = await fetch(`${BASE}/api/memory?session_id=${encodeURIComponent(sessionId)}`);
  if (!res.ok) throw new Error(`Memory failed: ${res.status}`);
  return res.json();
}

export async function getSkills() {
  const res = await fetch(`${BASE}/api/skills`);
  if (!res.ok) throw new Error(`Skills failed: ${res.status}`);
  return res.json();
}

export async function resetSession(sessionId) {
  const res = await fetch(`${BASE}/api/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`Reset failed: ${res.status}`);
  return res.json();
}

export async function getExportHistory(sessionId) {
  const res = await fetch(`${BASE}/api/export/history?session_id=${encodeURIComponent(sessionId)}`);
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);
  return res.json();
}

export async function downloadExportTxt(sessionId) {
  const res = await fetch(`${BASE}/api/export/txt?session_id=${encodeURIComponent(sessionId)}`);
  if (!res.ok) throw new Error(`TXT export failed: ${res.status}`);
  const text = await res.text();
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `jarvis_export_${sessionId}.txt`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadExportCsv(sessionId) {
  const res = await fetch(`${BASE}/api/export/csv?session_id=${encodeURIComponent(sessionId)}`);
  if (!res.ok) throw new Error(`CSV export failed: ${res.status}`);
  const text = await res.text();
  const blob = new Blob([text], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `jarvis_export_${sessionId}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
