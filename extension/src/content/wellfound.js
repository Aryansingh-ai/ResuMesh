/**
 * Wellfound (formerly AngelList) Content Script
 * Extracts job listings from Wellfound job pages.
 */

(function () {
  'use strict';

  const PORTAL = 'wellfound';

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

    // Title — Wellfound uses h1 with specific data attributes
    const titleEl = document.querySelector(
      'h1[data-test="JobListingTitle"], h1.styles_title__xpQDw, h1'
    );
    if (titleEl) data.title = titleEl.textContent?.trim() || '';

    // Company
    const companyEl = document.querySelector(
      'a[data-test="StartupNameLink"], .styles_companyName__pRTmz, [class*="companyName"]'
    );
    if (companyEl) data.company = companyEl.textContent?.trim() || '';

    // Location
    const locationEl = document.querySelector(
      '[data-test="JobListingLocation"], [class*="location"], [class*="Location"]'
    );
    if (locationEl) data.location = locationEl.textContent?.trim() || '';

    // Job type
    const typeEl = document.querySelector(
      '[data-test="JobListingJobType"], [class*="jobType"], [class*="type"]'
    );
    if (typeEl) data.job_type = typeEl.textContent?.trim() || '';

    // Description — look for the main content block
    const descSelectors = [
      '[data-test="JobListingDescription"]',
      '.styles_description__GiJeU',
      '[class*="jobDescription"]',
      '[class*="description"]',
      'div.prose',
    ];
    for (const sel of descSelectors) {
      const el = document.querySelector(sel);
      if (el && el.textContent && el.textContent.trim().length > 100) {
        data.raw_description = el.textContent.trim();
        break;
      }
    }

    return data;
  }

  function injectResuMeshOverlay(jobData) {
    if (document.getElementById('resumesh-wf-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'resumesh-wf-overlay';
    overlay.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 9999;
      font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
    `;

    overlay.innerHTML = `
      <div id="resumesh-wf-card" style="
        background: #0a0a0f;
        border: 1px solid #1e1e2e;
        border-radius: 16px;
        padding: 16px;
        width: 300px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.6);
      ">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="color:#a78bfa;font-weight:700;font-size:14px;">⚡ ResuMesh</span>
          </div>
          <button id="rm-wf-close" style="background:none;border:none;color:#6b7280;cursor:pointer;font-size:16px;">✕</button>
        </div>
        <div style="color:#e2e8f0;font-size:12px;font-weight:600;margin-bottom:4px;">${(jobData.title || '').substring(0, 40)}</div>
        <div style="color:#6b7280;font-size:11px;margin-bottom:12px;">${jobData.company}</div>
        <div id="rm-wf-content" style="text-align:center;color:#6b7280;font-size:12px;padding:8px 0;">
          Analyzing job match...
        </div>
        <button id="rm-wf-analyze" style="
          width:100%;padding:10px;margin-top:10px;
          background:linear-gradient(135deg,#7c3aed,#5b21b6);
          color:white;border:none;border-radius:8px;
          font-size:12px;font-weight:600;cursor:pointer;
        ">Analyze with ResuMesh</button>
      </div>
    `;

    document.body.appendChild(overlay);

    document.getElementById('rm-wf-close')?.addEventListener('click', () => overlay.remove());
    document.getElementById('rm-wf-analyze')?.addEventListener('click', async () => {
      const result = await chrome.runtime.sendMessage({
        type: 'ANALYZE_JOB',
        payload: { jobData },
      });
      const content = document.getElementById('rm-wf-content');
      if (content) {
        if (result.error) {
          content.innerHTML = `<span style="color:#f87171">${result.error}</span>`;
        } else {
          content.innerHTML = `
            <div style="color:#4ade80;font-size:20px;font-weight:800;">${Math.round(result.job?.match_score || 0)}%</div>
            <div style="color:#9ca3af;font-size:11px;">Match Score</div>
          `;
        }
      }
    });
  }

  function init() {
    if (!window.location.href.includes('/jobs') && !window.location.href.includes('/role/')) return;

    setTimeout(() => {
      const jobData = extractJobData();
      if (jobData.title || jobData.raw_description) {
        injectResuMeshOverlay(jobData);
      }
    }, 2500);
  }

  // Watch for SPA navigation
  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      document.getElementById('resumesh-wf-overlay')?.remove();
      setTimeout(init, 2000);
    }
  }).observe(document.body, { childList: true, subtree: true });

  init();
  console.log('[ResuMesh] Wellfound content script loaded');
})();
