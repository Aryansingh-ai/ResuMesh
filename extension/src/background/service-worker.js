/**
 * ResuMesh Chrome Extension Background Service Worker
 * Handles API communication, token storage, and cross-tab messaging.
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

// ── Storage helpers ────────────────────────────────────────────────────────────
async function getAuthToken() {
  const data = await chrome.storage.local.get(['access_token']);
  return data.access_token || null;
}

async function setAuthToken(token, refreshToken) {
  await chrome.storage.local.set({
    access_token: token,
    refresh_token: refreshToken,
  });
}

async function getUserData() {
  const data = await chrome.storage.local.get(['user_data']);
  return data.user_data || null;
}

async function setUserData(userData) {
  await chrome.storage.local.set({ user_data: userData });
}

// ── API helpers ────────────────────────────────────────────────────────────────
async function apiRequest(endpoint, options = {}) {
  const token = await getAuthToken();

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Try to refresh token
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiRequest(endpoint, options); // Retry once
    }
    throw new Error('Authentication required');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Unknown error' }));
    throw new Error(error.detail || error.message || `HTTP ${response.status}`);
  }

  return response.json();
}

async function refreshAccessToken() {
  const data = await chrome.storage.local.get(['refresh_token']);
  if (!data.refresh_token) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: data.refresh_token }),
    });

    if (!response.ok) {
      await chrome.storage.local.clear();
      return false;
    }

    const tokens = await response.json();
    await setAuthToken(tokens.access_token, tokens.refresh_token);
    return true;
  } catch {
    return false;
  }
}

// ── Message handler ────────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender)
    .then(sendResponse)
    .catch((error) => sendResponse({ error: error.message }));
  return true; // Keep channel open for async response
});

async function handleMessage(message, sender) {
  const { type, payload } = message;

  switch (type) {
    case 'GET_AUTH_STATUS': {
      const token = await getAuthToken();
      const user = await getUserData();
      return { isAuthenticated: !!token, user };
    }

    case 'LOGIN': {
      const { email, password } = payload;
      const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      await setAuthToken(data.access_token, data.refresh_token);
      await setUserData({
        id: data.user_id,
        email: data.email,
        full_name: data.full_name,
      });
      return { success: true, user: data };
    }

    case 'LOGOUT': {
      await chrome.storage.local.clear();
      return { success: true };
    }

    case 'ANALYZE_JOB': {
      const { jobData } = payload;
      const result = await apiRequest('/jobs/analyze', {
        method: 'POST',
        body: JSON.stringify(jobData),
      });
      return { success: true, job: result };
    }

    case 'GET_MATCH_SCORE': {
      const { resumeText, jobText } = payload;
      const result = await apiRequest('/matching/quick-score', {
        method: 'POST',
        body: JSON.stringify({ resume_text: resumeText, job_text: jobText }),
      });
      return { success: true, match: result };
    }

    case 'SAVE_JOB': {
      const { jobId } = payload;
      const result = await apiRequest('/applications/', {
        method: 'POST',
        body: JSON.stringify({ job_id: jobId, status: 'saved' }),
      });
      return { success: true, application: result };
    }

    case 'GET_PRIMARY_RESUME': {
      const result = await apiRequest('/resumes/');
      const resumes = result.items || [];
      const primary = resumes.find((r) => r.is_primary) || resumes[0];
      return { success: true, resume: primary };
    }

    default:
      return { error: `Unknown message type: ${type}` };
  }
}

// ── Installation handler ───────────────────────────────────────────────────────
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    chrome.tabs.create({ url: 'http://localhost:3000/register' });
  }
});

console.log('[ResuMesh] Service worker initialized');
