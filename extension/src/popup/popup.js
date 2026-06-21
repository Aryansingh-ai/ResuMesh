/**
 * ResuMesh Extension Popup Script
 * Manages auth state, tab navigation, and job analysis in the popup UI.
 */

'use strict';

// ── Helpers ──────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const msg = (type, payload) => chrome.runtime.sendMessage({ type, payload });

function setScore(score) {
  const card = $('score-card');
  if (!card) return;
  const col = score >= 70 ? '#4ade80' : score >= 50 ? '#fbbf24' : '#f87171';
  const label = score >= 70 ? '🎯 Great Match!' : score >= 50 ? '⚠️ Decent Match' : '❌ Needs Work';
  card.innerHTML = `
    <div class="score-value" style="color:${col}">${Math.round(score)}%</div>
    <div class="score-label">${label}</div>
  `;
}

function renderSkillTags(skills, containerId, type) {
  const el = $(containerId);
  if (!el) return;
  if (!skills || !skills.length) {
    el.innerHTML = type === 'matched'
      ? '<span class="tag-empty">None detected</span>'
      : '<span style="color:#4ade80;font-size:11px;">🎉 All skills covered!</span>';
    return;
  }
  el.innerHTML = skills.slice(0, 8).map(s =>
    `<span class="tag tag-${type === 'matched' ? 'green' : 'red'}">${s}</span>`
  ).join('');
}

function showError(message) {
  const el = $('login-error');
  if (el) el.textContent = message;
}

function setLoading(btn, loading) {
  if (!btn) return;
  btn.disabled = loading;
  if (loading) {
    btn.innerHTML = '<div class="spinner"></div>';
  } else {
    btn.innerHTML = '⚡ Analyze Current Job';
  }
}

// ── Auth UI ──────────────────────────────────────────────────────────────────
function showAuthSection() {
  $('auth-section').style.display = 'block';
  $('dashboard-section').style.display = 'none';
}

function showDashboard(user) {
  $('auth-section').style.display = 'none';
  $('dashboard-section').style.display = 'block';

  if (user) {
    const initials = (user.full_name || user.email || 'U').charAt(0).toUpperCase();
    $('user-avatar').textContent = initials;
    $('user-name').textContent = user.full_name || 'User';
    $('user-email').textContent = user.email || '';
  }
}

// ── Tab Switcher ─────────────────────────────────────────────────────────────
function initTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const name = tab.dataset.tab;
      ['match', 'recent', 'quick'].forEach(t => {
        const el = $(`tab-${t}`);
        if (el) el.style.display = t === name ? 'block' : 'none';
      });

      if (name === 'recent') loadRecentJobs();
    });
  });
}

// ── Current Tab Job Detection ─────────────────────────────────────────────────
async function detectCurrentJob() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return null;

  const url = tab.url || '';
  let portal = null;

  if (url.includes('linkedin.com/jobs')) portal = 'linkedin';
  else if (url.includes('wellfound.com') || url.includes('angel.co')) portal = 'wellfound';
  else if (url.includes('internshala.com')) portal = 'internshala';
  else if (url.includes('naukri.com')) portal = 'naukri';

  if (!portal) {
    $('current-job-title').textContent = 'No job page detected';
    $('current-job-meta').textContent = 'Navigate to a job on LinkedIn, Wellfound, Internshala, or Naukri';
    return null;
  }

  $('current-job-title').textContent = 'Job page detected';
  $('current-job-meta').textContent = `${portal.charAt(0).toUpperCase() + portal.slice(1)} · ${tab.title?.substring(0, 40) || url.substring(0, 40)}`;

  return { portal, tabId: tab.id, url };
}

// ── Analyze ──────────────────────────────────────────────────────────────────
async function analyzeCurrentJob() {
  const analyzeBtn = $('analyze-btn');
  setLoading(analyzeBtn, true);

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) throw new Error('No active tab found');

    // Inject content script to extract job description
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        // Generic extractor fallback
        const title = document.querySelector('h1')?.textContent?.trim() || '';
        const desc = document.querySelector(
          '[class*="description"], [class*="jd"], [id*="job"], main'
        )?.textContent?.trim().substring(0, 4000) || document.body.textContent.substring(0, 2000);
        return { title, raw_description: desc, url: location.href };
      },
    });

    const jobData = results?.[0]?.result;
    if (!jobData?.raw_description || jobData.raw_description.length < 50) {
      throw new Error('Could not extract job description from this page');
    }

    const result = await msg('GET_MATCH_SCORE', {
      resumeText: '',
      jobText: jobData.raw_description,
    });

    if (result.error) throw new Error(result.error);

    const match = result.match;
    setScore(match.score || 0);

    $('skills-section').style.display = 'block';
    renderSkillTags(match.matched_skills, 'matched-tags', 'matched');
    renderSkillTags(match.missing_skills, 'missing-tags', 'missing');

    // Store in recent
    const recent = await chrome.storage.local.get(['recent_jobs']);
    const recentList = recent.recent_jobs || [];
    recentList.unshift({
      title: jobData.title || 'Unknown Job',
      url: jobData.url,
      score: match.score,
      timestamp: Date.now(),
    });
    await chrome.storage.local.set({ recent_jobs: recentList.slice(0, 10) });

  } catch (err) {
    $('score-card').innerHTML = `<div style="color:#f87171;font-size:11px;">${err.message}</div>`;
  } finally {
    setLoading(analyzeBtn, false);
    analyzeBtn.innerHTML = '⚡ Analyze Current Job';
  }
}

// ── Recent Jobs ───────────────────────────────────────────────────────────────
async function loadRecentJobs() {
  const data = await chrome.storage.local.get(['recent_jobs']);
  const jobs = data.recent_jobs || [];
  const container = $('recent-jobs-list');
  if (!container) return;

  if (!jobs.length) {
    container.innerHTML = '<div style="color:#6b7280;font-size:12px;text-align:center;padding:20px;">No jobs analyzed yet.</div>';
    return;
  }

  container.innerHTML = jobs.map(j => {
    const col = j.score >= 70 ? '#4ade80' : j.score >= 50 ? '#fbbf24' : '#f87171';
    const ago = Math.round((Date.now() - j.timestamp) / 60000);
    const timeStr = ago < 60 ? `${ago}m ago` : `${Math.round(ago / 60)}h ago`;
    return `
      <div class="recent-item">
        <div>
          <div class="recent-title">${j.title.substring(0, 30)}</div>
          <div class="recent-company">${timeStr}</div>
        </div>
        <div class="score-badge" style="color:${col};background:${col}20;">${Math.round(j.score)}%</div>
      </div>
    `;
  }).join('');
}

// ── Init ─────────────────────────────────────────────────────────────────────
async function init() {
  initTabs();

  // Check auth status
  const authStatus = await msg('GET_AUTH_STATUS');

  if (!authStatus.isAuthenticated) {
    showAuthSection();

    // Login handler
    $('login-btn')?.addEventListener('click', async () => {
      const email = $('email-input')?.value?.trim();
      const password = $('password-input')?.value;

      if (!email || !password) { showError('Enter email and password'); return; }

      $('login-btn').disabled = true;
      $('login-btn').innerHTML = '<div class="spinner"></div>';

      const result = await msg('LOGIN', { email, password });

      if (result.error) {
        showError(result.error);
        $('login-btn').disabled = false;
        $('login-btn').textContent = 'Sign In';
      } else {
        showDashboard(result.user);
        detectCurrentJob();
      }
    });

    // Allow Enter key
    $('password-input')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') $('login-btn')?.click();
    });

  } else {
    showDashboard(authStatus.user);
    detectCurrentJob();
  }

  // Logout
  $('logout-btn')?.addEventListener('click', async () => {
    await msg('LOGOUT');
    showAuthSection();
  });

  // Analyze
  $('analyze-btn')?.addEventListener('click', analyzeCurrentJob);

  // Quick action buttons
  $('open-coach-btn')?.addEventListener('click', () => chrome.tabs.create({ url: 'http://localhost:3000/coach' }));
  $('open-dashboard-btn')?.addEventListener('click', () => chrome.tabs.create({ url: 'http://localhost:3000/dashboard' }));
  $('save-job-btn')?.addEventListener('click', () => chrome.tabs.create({ url: 'http://localhost:3000/applications' }));
  $('cover-letter-btn')?.addEventListener('click', () => chrome.tabs.create({ url: 'http://localhost:3000/cover-letters' }));
}

document.addEventListener('DOMContentLoaded', init);
