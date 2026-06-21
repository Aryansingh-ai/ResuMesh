/**
 * Internshala Content Script
 * Extracts internship/job details from Internshala listing pages.
 */

(function () {
  'use strict';

  const PORTAL = 'internshala';

  function extractJobData() {
    const data = {
      title: '',
      company: '',
      location: '',
      job_type: 'internship',
      portal: PORTAL,
      job_url: window.location.href,
      raw_description: '',
    };

    // Title
    const titleEl = document.querySelector(
      '.profile h1, h1.heading_4_5, .internship_heading h1, [class*="heading"]'
    );
    if (titleEl) data.title = titleEl.textContent?.trim() || '';

    // Company
    const companyEl = document.querySelector(
      '.company-name, a.link_display_like_text, .internship-overview .company, [class*="company"]'
    );
    if (companyEl) data.company = companyEl.textContent?.trim() || '';

    // Location
    const locEl = document.querySelector(
      '.location_link, .location span, [id="location_names"]'
    );
    if (locEl) data.location = locEl.textContent?.trim() || '';

    // Description — gather all text from the details section
    const descSections = [
      '.internship_other_details_container',
      '#about_company',
      '.section_heading + div',
      '[class*="about"]',
      '.internship-detail',
    ];

    let descText = '';
    for (const sel of descSections) {
      const el = document.querySelector(sel);
      if (el) descText += el.textContent?.trim() + '\n\n';
    }
    data.raw_description = descText.trim();

    // Fallback: grab main content area
    if (!data.raw_description) {
      const main = document.querySelector('#detail_container, main, .detail-wrapper');
      if (main) data.raw_description = main.textContent?.trim().substring(0, 3000) || '';
    }

    return data;
  }

  function createBadge(text, type) {
    const colors = {
      matched: '#4ade80',
      missing: '#f87171',
      neutral: '#a78bfa',
    };
    return `<span style="
      background:${colors[type] || colors.neutral}20;
      color:${colors[type] || colors.neutral};
      border:1px solid ${colors[type] || colors.neutral}40;
      border-radius:4px;padding:2px 7px;font-size:10px;margin:2px;display:inline-block;
    ">${text}</span>`;
  }

  async function runAnalysis(jobData) {
    const statusEl = document.getElementById('rm-is-status');
    if (statusEl) statusEl.textContent = 'Analyzing your match...';

    try {
      const auth = await chrome.runtime.sendMessage({ type: 'GET_AUTH_STATUS' });
      if (!auth.isAuthenticated) {
        if (statusEl) statusEl.innerHTML = '<a href="http://localhost:3000/login" target="_blank" style="color:#a78bfa;">Sign in to ResuMesh →</a>';
        return;
      }

      const result = await chrome.runtime.sendMessage({
        type: 'GET_MATCH_SCORE',
        payload: { resumeText: '', jobText: jobData.raw_description },
      });

      if (result.error) throw new Error(result.error);
      const match = result.match;

      const panel = document.getElementById('rm-is-panel');
      if (panel) {
        const score = Math.round(match.score || 0);
        const scoreColor = score >= 70 ? '#4ade80' : score >= 50 ? '#fbbf24' : '#f87171';

        panel.innerHTML = `
          <div style="display:flex;align-items:center;gap:16px;margin-bottom:12px;">
            <div style="text-align:center;">
              <div style="font-size:32px;font-weight:800;color:${scoreColor};">${score}%</div>
              <div style="font-size:10px;color:#9ca3af;">Match Score</div>
            </div>
            <div style="flex:1;">
              <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;">Matched Skills</div>
              <div>${(match.matched_skills || []).slice(0, 5).map(s => createBadge(s, 'matched')).join('')}</div>
              <div style="font-size:11px;color:#9ca3af;margin-top:8px;margin-bottom:4px;">Missing Skills</div>
              <div>${(match.missing_skills || []).slice(0, 5).map(s => createBadge(s, 'missing')).join('') || '<span style="color:#4ade80;font-size:11px;">All covered! 🎉</span>'}</div>
            </div>
          </div>
          <a href="http://localhost:3000/coach" target="_blank" style="
            display:block;text-align:center;padding:8px;
            background:linear-gradient(135deg,#7c3aed,#5b21b6);
            color:white;border-radius:8px;text-decoration:none;font-size:12px;font-weight:600;
          ">Get Improvement Tips →</a>
        `;
      }
    } catch (err) {
      if (statusEl) statusEl.innerHTML = `<span style="color:#f87171;">Error: ${err.message}</span>`;
    }
  }

  function inject(jobData) {
    if (document.getElementById('resumesh-is-widget')) return;

    const widget = document.createElement('div');
    widget.id = 'resumesh-is-widget';
    widget.style.cssText = `
      background: #0a0a0f;
      border: 1px solid #1e1e2e;
      border-radius: 12px;
      padding: 16px;
      margin: 16px 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
    `;

    widget.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
        <div style="color:#a78bfa;font-weight:700;font-size:13px;">⚡ ResuMesh Analysis</div>
        <button onclick="document.getElementById('resumesh-is-widget').remove()"
          style="background:none;border:none;color:#6b7280;cursor:pointer;font-size:14px;">✕</button>
      </div>
      <div id="rm-is-panel">
        <div id="rm-is-status" style="color:#9ca3af;font-size:12px;text-align:center;padding:8px;">
          Checking auth status...
        </div>
      </div>
    `;

    // Insert near the apply button or at the top of the detail section
    const insertTarget = document.querySelector(
      '.internship_other_details_container, #detail_container > .container, .internship-detail'
    );
    if (insertTarget) {
      insertTarget.insertBefore(widget, insertTarget.firstChild);
    } else {
      document.body.prepend(widget);
    }

    runAnalysis(jobData);
  }

  function init() {
    const isJobPage = /\/(internship|job)\//.test(window.location.pathname) ||
                      /\/(jobs|internships)\//.test(window.location.pathname);
    if (!isJobPage) return;

    setTimeout(() => {
      const jobData = extractJobData();
      if (jobData.title || jobData.raw_description.length > 50) {
        inject(jobData);
      }
    }, 2000);
  }

  init();
  console.log('[ResuMesh] Internshala content script loaded');
})();
