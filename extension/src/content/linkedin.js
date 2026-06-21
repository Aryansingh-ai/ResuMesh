/**
 * LinkedIn Content Script
 * Extracts job data from LinkedIn job detail pages and injects ResuMesh sidebar.
 */

(function () {
  'use strict';

  const PORTAL = 'linkedin';
  let sidebarInjected = false;
  let currentJobUrl = '';

  // ── Job Data Extraction ────────────────────────────────────────────────────
  function extractJobData() {
    const data = {
      title: '',
      company: '',
      location: '',
      job_type: '',
      portal: PORTAL,
      job_url: window.location.href,
      raw_description: '',
    };

    // Title
    const titleEl = document.querySelector(
      'h1.t-24, h1.jobs-unified-top-card__job-title, h1[class*="job-title"]'
    );
    if (titleEl) data.title = titleEl.textContent.trim();

    // Company
    const companyEl = document.querySelector(
      '.jobs-unified-top-card__company-name a, .job-details-jobs-unified-top-card__company-name a, [data-test-id="job-company-name"]'
    );
    if (companyEl) data.company = companyEl.textContent.trim();

    // Location
    const locationEl = document.querySelector(
      '.jobs-unified-top-card__bullet, .job-details-jobs-unified-top-card__primary-description-without-tagline'
    );
    if (locationEl) data.location = locationEl.textContent.trim().split('·')[0].trim();

    // Job description
    const descEl = document.querySelector(
      '.jobs-description-content__text, #job-details, .jobs-box__html-content'
    );
    if (descEl) data.raw_description = descEl.textContent.trim();

    return data;
  }

  // ── Sidebar Injection ────────────────────────────────────────────────────────
  function injectSidebar(jobData) {
    // Remove existing sidebar
    const existing = document.getElementById('resumesh-sidebar');
    if (existing) existing.remove();

    const sidebar = document.createElement('div');
    sidebar.id = 'resumesh-sidebar';
    sidebar.style.cssText = `
      position: fixed;
      right: 0;
      top: 60px;
      width: 340px;
      height: calc(100vh - 60px);
      background: #0a0a0f;
      border-left: 1px solid #1a1a2e;
      z-index: 9999;
      font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
      overflow-y: auto;
      box-shadow: -4px 0 20px rgba(0,0,0,0.5);
    `;

    sidebar.innerHTML = `
      <div style="padding:20px;">
        <!-- Header -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:18px;">⚡</span>
            <span style="color:#a78bfa;font-weight:700;font-size:15px;">ResuMesh</span>
          </div>
          <button id="rm-close" style="background:none;border:none;color:#6b7280;cursor:pointer;font-size:18px;">✕</button>
        </div>

        <!-- Job Info -->
        <div style="background:#111118;border:1px solid #1e1e2e;border-radius:10px;padding:14px;margin-bottom:14px;">
          <div style="color:#e2e8f0;font-weight:600;font-size:13px;margin-bottom:4px;">${escapeHtml(jobData.title || 'Loading...')}</div>
          <div style="color:#9ca3af;font-size:12px;">${escapeHtml(jobData.company || '')} · ${escapeHtml(jobData.location || '')}</div>
        </div>

        <!-- Loading State -->
        <div id="rm-loading" style="text-align:center;padding:30px;color:#6b7280;">
          <div style="font-size:24px;margin-bottom:10px;">🔍</div>
          <div style="font-size:13px;">Analyzing job match...</div>
          <div style="margin-top:12px;height:3px;background:#1e1e2e;border-radius:2px;overflow:hidden;">
            <div id="rm-progress-bar" style="height:100%;width:0%;background:linear-gradient(90deg,#7c3aed,#a78bfa);border-radius:2px;transition:width 0.3s ease;"></div>
          </div>
        </div>

        <!-- Results (hidden initially) -->
        <div id="rm-results" style="display:none;">
          <!-- Score -->
          <div style="background:#111118;border:1px solid #1e1e2e;border-radius:10px;padding:14px;margin-bottom:12px;text-align:center;">
            <div style="color:#9ca3af;font-size:11px;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Match Score</div>
            <div id="rm-score" style="font-size:42px;font-weight:800;color:#a78bfa;"></div>
            <div id="rm-score-label" style="font-size:12px;color:#6b7280;margin-top:4px;"></div>
          </div>

          <!-- Matched Skills -->
          <div style="margin-bottom:12px;">
            <div style="color:#9ca3af;font-size:11px;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">✅ Matched Skills</div>
            <div id="rm-matched-skills" style="display:flex;flex-wrap:wrap;gap:6px;"></div>
          </div>

          <!-- Missing Skills -->
          <div style="margin-bottom:14px;">
            <div style="color:#9ca3af;font-size:11px;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">❌ Missing Skills</div>
            <div id="rm-missing-skills" style="display:flex;flex-wrap:wrap;gap:6px;"></div>
          </div>

          <!-- Actions -->
          <button id="rm-cover-letter-btn" style="width:100%;padding:11px;background:linear-gradient(135deg,#7c3aed,#5b21b6);color:white;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;margin-bottom:8px;">
            ✉️ Generate Cover Letter
          </button>
          <button id="rm-save-btn" style="width:100%;padding:11px;background:#111118;color:#a78bfa;border:1px solid #7c3aed;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;">
            🔖 Save Job
          </button>
        </div>

        <!-- Auth prompt -->
        <div id="rm-auth-prompt" style="display:none;text-align:center;padding:20px;">
          <div style="font-size:32px;margin-bottom:10px;">🔒</div>
          <div style="color:#e2e8f0;font-size:13px;margin-bottom:14px;">Sign in to analyze this job</div>
          <a href="http://localhost:3000/login" target="_blank" style="display:inline-block;padding:10px 20px;background:linear-gradient(135deg,#7c3aed,#5b21b6);color:white;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;">
            Sign In to ResuMesh
          </a>
        </div>

        <!-- Error -->
        <div id="rm-error" style="display:none;background:#1a0a0a;border:1px solid #7f1d1d;border-radius:8px;padding:12px;color:#fca5a5;font-size:12px;margin-top:10px;"></div>
      </div>
    `;

    document.body.appendChild(sidebar);
    sidebarInjected = true;

    // Event listeners
    document.getElementById('rm-close')?.addEventListener('click', () => sidebar.remove());
    document.getElementById('rm-cover-letter-btn')?.addEventListener('click', () => {
      chrome.runtime.sendMessage({ type: 'OPEN_COVER_LETTER', payload: { jobData } });
    });
    document.getElementById('rm-save-btn')?.addEventListener('click', handleSaveJob);

    // Start analysis
    analyzeJob(jobData);
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  }

  function skillBadge(skill, type = 'matched') {
    const colors = {
      matched: 'background:#0f2d17;color:#4ade80;border:1px solid #166534;',
      missing: 'background:#2d0f0f;color:#f87171;border:1px solid #7f1d1d;',
    };
    return `<span style="${colors[type]}border-radius:4px;padding:3px 8px;font-size:11px;">${escapeHtml(skill)}</span>`;
  }

  function updateProgress(percent) {
    const bar = document.getElementById('rm-progress-bar');
    if (bar) bar.style.width = `${percent}%`;
  }

  async function analyzeJob(jobData) {
    updateProgress(20);

    const authStatus = await chrome.runtime.sendMessage({ type: 'GET_AUTH_STATUS' });

    if (!authStatus.isAuthenticated) {
      document.getElementById('rm-loading').style.display = 'none';
      document.getElementById('rm-auth-prompt').style.display = 'block';
      return;
    }

    updateProgress(50);

    try {
      // Get quick match score
      const matchResult = await chrome.runtime.sendMessage({
        type: 'GET_MATCH_SCORE',
        payload: {
          resumeText: '', // Will be fetched from primary resume
          jobText: jobData.raw_description,
        },
      });

      updateProgress(90);

      if (matchResult.error) throw new Error(matchResult.error);

      const match = matchResult.match;
      showResults(match);
      updateProgress(100);

    } catch (error) {
      document.getElementById('rm-loading').style.display = 'none';
      const errEl = document.getElementById('rm-error');
      if (errEl) {
        errEl.style.display = 'block';
        errEl.textContent = `Error: ${error.message}`;
      }
    }
  }

  function showResults(match) {
    document.getElementById('rm-loading').style.display = 'none';
    const results = document.getElementById('rm-results');
    if (!results) return;
    results.style.display = 'block';

    const score = match.score || 0;
    const scoreEl = document.getElementById('rm-score');
    const labelEl = document.getElementById('rm-score-label');

    if (scoreEl) {
      scoreEl.textContent = `${Math.round(score)}%`;
      scoreEl.style.color = score >= 70 ? '#4ade80' : score >= 50 ? '#fbbf24' : '#f87171';
    }
    if (labelEl) {
      labelEl.textContent = score >= 70 ? 'Great Match!' : score >= 50 ? 'Decent Match' : 'Needs Work';
    }

    const matchedContainer = document.getElementById('rm-matched-skills');
    if (matchedContainer) {
      matchedContainer.innerHTML = (match.matched_skills || []).slice(0, 8).map((s) => skillBadge(s, 'matched')).join('');
      if (!match.matched_skills?.length) matchedContainer.innerHTML = '<span style="color:#6b7280;font-size:12px;">None detected</span>';
    }

    const missingContainer = document.getElementById('rm-missing-skills');
    if (missingContainer) {
      missingContainer.innerHTML = (match.missing_skills || []).slice(0, 8).map((s) => skillBadge(s, 'missing')).join('');
      if (!match.missing_skills?.length) missingContainer.innerHTML = '<span style="color:#4ade80;font-size:12px;">🎉 All skills matched!</span>';
    }
  }

  async function handleSaveJob() {
    // This would save the job via the background service worker
    const btn = document.getElementById('rm-save-btn');
    if (btn) {
      btn.textContent = '✅ Saved!';
      btn.disabled = true;
    }
  }

  // ── Observer — detect job page navigation ────────────────────────────────────
  function checkJobPage() {
    const isJobPage = window.location.href.includes('/jobs/view/') ||
                      window.location.href.includes('/jobs/search/');

    if (isJobPage && window.location.href !== currentJobUrl) {
      currentJobUrl = window.location.href;
      sidebarInjected = false;

      // Wait for DOM to settle
      setTimeout(() => {
        const jobData = extractJobData();
        if (jobData.title && !sidebarInjected) {
          injectSidebar(jobData);
        }
      }, 2000);
    }
  }

  // MutationObserver for SPA navigation
  const observer = new MutationObserver(() => checkJobPage());
  observer.observe(document.body, { childList: true, subtree: true });

  // Initial check
  checkJobPage();
  console.log('[ResuMesh] LinkedIn content script loaded');
})();
