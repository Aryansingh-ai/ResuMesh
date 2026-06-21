/**
 * Naukri Content Script
 * Extracts job details from Naukri job detail pages.
 */

(function () {
  'use strict';

  const PORTAL = 'naukri';

  function extractJobData() {
    const data = {
      title: '',
      company: '',
      location: '',
      job_type: 'full-time',
      portal: PORTAL,
      job_url: window.location.href,
      raw_description: '',
    };

    // Title
    const titleEl = document.querySelector(
      'h1.styles_jd-header-title__rZwM1, h1[class*="title"], .jd-header h1, h1'
    );
    if (titleEl) data.title = titleEl.textContent?.trim() || '';

    // Company
    const companyEl = document.querySelector(
      'a[class*="comp-name"], .jd-header-comp-name, [class*="companyName"], .company-name'
    );
    if (companyEl) data.company = companyEl.textContent?.trim() || '';

    // Location
    const locEl = document.querySelector(
      '[class*="location"], [class*="locWdth"], .loc-link'
    );
    if (locEl) data.location = locEl.textContent?.trim() || '';

    // Job description
    const descSelectors = [
      '.styles_JDC__dang-inner-html__h0K4t',
      '[class*="job-desc"]',
      '#jobDescriptionText',
      '.jd-desc',
      '[class*="description"]',
      'section.styles_key-container__',
    ];

    for (const sel of descSelectors) {
      const el = document.querySelector(sel);
      if (el && el.textContent && el.textContent.trim().length > 100) {
        data.raw_description = el.textContent.trim();
        break;
      }
    }

    // Fallback: gather key skills section
    if (!data.raw_description) {
      const keySkills = document.querySelector('[class*="key-skill"], .key-skills');
      const about = document.querySelector('[class*="about-company"]');
      data.raw_description = [keySkills?.textContent, about?.textContent]
        .filter(Boolean).join('\n').trim();
    }

    return data;
  }

  let sidebarOpen = false;

  function injectSidebar(jobData) {
    if (document.getElementById('resumesh-naukri-sidebar')) return;

    // Create toggle button first
    const toggleBtn = document.createElement('button');
    toggleBtn.id = 'resumesh-naukri-toggle';
    toggleBtn.textContent = '⚡';
    toggleBtn.title = 'Open ResuMesh';
    toggleBtn.style.cssText = `
      position: fixed;
      right: 0;
      top: 50%;
      transform: translateY(-50%);
      z-index: 9998;
      background: linear-gradient(135deg, #7c3aed, #5b21b6);
      color: white;
      border: none;
      border-radius: 8px 0 0 8px;
      width: 36px;
      height: 48px;
      cursor: pointer;
      font-size: 18px;
      box-shadow: -4px 0 16px rgba(124,58,237,0.4);
      transition: width 0.2s;
    `;

    const sidebar = document.createElement('div');
    sidebar.id = 'resumesh-naukri-sidebar';
    sidebar.style.cssText = `
      position: fixed;
      right: -340px;
      top: 0;
      bottom: 0;
      width: 340px;
      background: #0a0a0f;
      border-left: 1px solid #1a1a2e;
      z-index: 9999;
      font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
      overflow-y: auto;
      box-shadow: -8px 0 32px rgba(0,0,0,0.6);
      transition: right 0.3s ease;
      padding: 20px;
    `;

    sidebar.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
        <span style="color:#a78bfa;font-weight:700;font-size:15px;">⚡ ResuMesh</span>
        <button id="rm-n-close" style="background:none;border:none;color:#6b7280;cursor:pointer;font-size:18px;">✕</button>
      </div>

      <div style="background:#111118;border:1px solid #1e1e2e;border-radius:10px;padding:12px;margin-bottom:14px;">
        <div style="color:#e2e8f0;font-weight:600;font-size:13px;">${escapeHtml(jobData.title)}</div>
        <div style="color:#9ca3af;font-size:11px;margin-top:2px;">${escapeHtml(jobData.company)}</div>
      </div>

      <div id="rm-n-results" style="color:#9ca3af;font-size:12px;text-align:center;padding:20px 0;">
        <div style="font-size:24px;margin-bottom:8px;">🔍</div>
        Click Analyze to check your match
      </div>

      <button id="rm-n-analyze" style="
        width:100%;padding:11px;
        background:linear-gradient(135deg,#7c3aed,#5b21b6);
        color:white;border:none;border-radius:8px;
        font-size:13px;font-weight:600;cursor:pointer;margin-bottom:8px;
      ">⚡ Analyze Match</button>

      <a href="http://localhost:3000" target="_blank" style="
        display:block;text-align:center;padding:9px;
        background:#111118;color:#a78bfa;border:1px solid #7c3aed33;
        border-radius:8px;text-decoration:none;font-size:12px;font-weight:600;
      ">Open Dashboard →</a>
    `;

    document.body.appendChild(toggleBtn);
    document.body.appendChild(sidebar);

    function escapeHtml(str) {
      return String(str || '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
    }

    toggleBtn.addEventListener('click', () => {
      sidebarOpen = !sidebarOpen;
      sidebar.style.right = sidebarOpen ? '0' : '-340px';
    });

    document.getElementById('rm-n-close')?.addEventListener('click', () => {
      sidebarOpen = false;
      sidebar.style.right = '-340px';
    });

    document.getElementById('rm-n-analyze')?.addEventListener('click', () => analyzeJob(jobData));
  }

  async function analyzeJob(jobData) {
    const resultsEl = document.getElementById('rm-n-results');
    if (!resultsEl) return;
    resultsEl.innerHTML = '<div style="text-align:center;padding:20px;color:#9ca3af;">Analyzing...</div>';

    try {
      const auth = await chrome.runtime.sendMessage({ type: 'GET_AUTH_STATUS' });
      if (!auth.isAuthenticated) {
        resultsEl.innerHTML = `
          <div style="text-align:center;padding:16px;">
            <div style="font-size:28px;margin-bottom:8px;">🔒</div>
            <a href="http://localhost:3000/login" target="_blank"
              style="color:#a78bfa;font-size:12px;font-weight:600;">Sign in to ResuMesh →</a>
          </div>
        `;
        return;
      }

      const result = await chrome.runtime.sendMessage({
        type: 'GET_MATCH_SCORE',
        payload: { resumeText: '', jobText: jobData.raw_description },
      });

      if (result.error) throw new Error(result.error);
      const match = result.match;
      const score = Math.round(match.score || 0);
      const col = score >= 70 ? '#4ade80' : score >= 50 ? '#fbbf24' : '#f87171';

      const badge = (s, c) => `<span style="background:${c}20;color:${c};border:1px solid ${c}40;
        border-radius:4px;padding:2px 7px;font-size:10px;margin:2px;display:inline-block;">${s}</span>`;

      resultsEl.innerHTML = `
        <div style="text-align:center;margin-bottom:14px;">
          <div style="font-size:48px;font-weight:800;color:${col};">${score}%</div>
          <div style="font-size:12px;color:#9ca3af;">${score >= 70 ? '✅ Great Match!' : score >= 50 ? '⚠️ Decent Match' : '❌ Needs Work'}</div>
        </div>
        <div style="margin-bottom:10px;">
          <div style="color:#9ca3af;font-size:10px;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;">✅ Matched</div>
          <div>${(match.matched_skills || []).slice(0, 6).map(s => badge(s, '#4ade80')).join('') || '<span style="color:#6b7280;font-size:11px;">None</span>'}</div>
        </div>
        <div>
          <div style="color:#9ca3af;font-size:10px;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;">❌ Missing</div>
          <div>${(match.missing_skills || []).slice(0, 6).map(s => badge(s, '#f87171')).join('') || '<span style="color:#4ade80;font-size:11px;">All covered! 🎉</span>'}</div>
        </div>
      `;
    } catch (err) {
      resultsEl.innerHTML = `<div style="color:#f87171;font-size:12px;padding:8px;">Error: ${err.message}</div>`;
    }
  }

  function init() {
    const isJobPage = /\/job-listings\//.test(window.location.href) ||
                      /\/jobs\//.test(window.location.href) ||
                      document.querySelector('[class*="jd-header"]');
    if (!isJobPage) return;

    setTimeout(() => {
      const jobData = extractJobData();
      if (jobData.title || jobData.raw_description) {
        injectSidebar(jobData);
      }
    }, 2500);
  }

  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      document.getElementById('resumesh-naukri-sidebar')?.remove();
      document.getElementById('resumesh-naukri-toggle')?.remove();
      sidebarOpen = false;
      setTimeout(init, 2000);
    }
  }).observe(document.body, { childList: true, subtree: true });

  init();
  console.log('[ResuMesh] Naukri content script loaded');
})();
