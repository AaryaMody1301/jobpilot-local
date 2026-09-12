(() => {
  const jobsView = document.getElementById('jobs');
  if (!jobsView || document.getElementById('job-discover')) return;

  document.querySelector('.privacy-note').textContent = 'No telemetry. No cloud AI. Public ATS discovery only. No employer submissions.';
  document.querySelector('.eyebrow').textContent = 'PHASE 5 · JOB DISCOVERY & MATCHING';
  const dashboardBanner = document.querySelector('#dashboard .banner');
  if (dashboardBanner) dashboardBanner.innerHTML = '<strong>Local discovery and matching mode.</strong> Public Greenhouse, Lever, and Ashby boards can be checked explicitly. Matching is evidence-backed and conservative. Employer form filling and submission remain disabled.';
  const history = document.querySelector('#history .empty-state');
  if (history) history.innerHTML = '<h2>No application history yet</h2><p>Phase 5 discovers and ranks jobs only. Employer application states remain inactive.</p>';

  jobsView.innerHTML = `
    <div class="banner"><strong>Public discovery only.</strong> JobPilot reads verified public Greenhouse, Lever, and Ashby posting feeds. Unknown eligibility is sent to review rather than guessed. No employer form is opened or submitted.</div>
    <div class="grid two">
      <article class="card">
        <div class="card-heading"><div><h2>Verified job boards</h2><p>Starter boards are versioned locally. User-added identifiers are accepted only after a live public endpoint returns a valid supported payload.</p></div><button id="job-discover" class="primary">Discover now</button></div>
        <div id="job-board-list" class="fact-list"></div>
        <form id="job-board-form" class="section-card">
          <label>Provider<select id="job-board-provider"><option value="greenhouse">Greenhouse</option><option value="lever">Lever</option><option value="ashby">Ashby</option></select></label>
          <label>Employer<input id="job-board-employer" maxlength="200" required></label>
          <label>Board identifier<input id="job-board-token" maxlength="100" required></label>
          <button type="submit">Verify & add</button>
        </form>
      </article>
      <article class="card">
        <h2>Manual job import</h2><p>Use this for a job outside the supported board registry. The job text remains untrusted data.</p>
        <form id="manual-job-form">
          <label>Employer<input id="manual-job-employer" maxlength="200" required></label>
          <label>Title<input id="manual-job-title" maxlength="300" required></label>
          <label>Location<input id="manual-job-location" maxlength="300" placeholder="Surat, India"></label>
          <div class="form-row"><label>Workplace<select id="manual-job-workplace"><option value="">Unknown</option><option value="onsite">On-site</option><option value="hybrid">Hybrid</option><option value="remote">Remote</option></select></label><label>Employment<select id="manual-job-employment"><option value="">Unknown</option><option value="permanent_full_time">Permanent full-time</option><option value="contract">Contract</option><option value="part_time">Part-time</option><option value="internship">Internship</option></select></label></div>
          <label>Source URL<input id="manual-job-url" type="url" maxlength="2000" required></label>
          <label>Description<textarea id="manual-job-description" rows="10" maxlength="100000" required></textarea></label>
          <button type="submit">Import & match</button>
        </form>
      </article>
    </div>
    <article class="card section-card">
      <div class="card-heading"><div><h2>Matched jobs</h2><p>Hard eligibility is separated from evidence matching. Scores explain ordering; they are not ATS scores or interview probabilities.</p></div><span id="job-counts" class="muted"></span></div>
      <div id="job-list" class="fact-list"></div>
    </article>`;

  function renderPhase5Jobs(state, session, busy) {
    const jobs = state.jobs;
    if (!jobs) return;
    const idle = session === 'idle' && !busy;
    document.getElementById('job-discover').disabled = !idle;
    document.querySelector('#job-board-form button[type="submit"]').disabled = !idle;
    document.querySelector('#manual-job-form button[type="submit"]').disabled = !idle;
    document.getElementById('job-counts').textContent = `${jobs.counts.eligible} eligible · ${jobs.counts.review} review · ${jobs.counts.ineligible} ineligible · ${jobs.approved_evidence_facts} approved evidence facts`;
    document.getElementById('job-board-list').innerHTML = jobs.boards.map(board => `
      <label class="region-item"><input type="checkbox" data-job-board-id="${escapeAttr(board.id)}" ${Number(board.enabled) === 1 ? 'checked' : ''} ${idle ? '' : 'disabled'}><span><strong>${escapeHtml(board.employer)}</strong> · ${escapeHtml(board.provider)} · <code>${escapeHtml(board.board_token)}</code><br>${board.last_checked_at ? `Checked ${escapeHtml(board.last_checked_at)}` : 'Not checked this install'}${board.last_error ? `<br><span class="error-text">${escapeHtml(board.last_error)}</span>` : ''}</span></label>`).join('');
    document.getElementById('job-list').innerHTML = jobs.items.length ? jobs.items.map(job => {
      const reasons = [...job.hard_reasons, ...job.review_reasons];
      return `<div class="fact-item"><div class="fact-meta"><span class="pill ${escapeAttr(job.eligibility)}">${escapeHtml(job.eligibility)}</span><strong>${job.score}/100</strong></div><strong>${escapeHtml(job.title)}</strong><div class="fact-source">${escapeHtml(job.employer)} · ${escapeHtml(job.location)} · ${escapeHtml(job.workplace_type || 'workplace unknown')} · ${escapeHtml(job.employment_type || 'employment unknown')}<br>Source: ${escapeHtml(job.source_url)}</div>${reasons.length ? `<div class="fact-source">${reasons.map(escapeHtml).join('<br>')}</div>` : ''}<div class="fact-source">Evidence terms: ${job.supported_terms.length ? job.supported_terms.map(escapeHtml).join(', ') : 'none'}<br>Required evidence: ${job.matched_required.length}/${job.required_requirements.length} · Preferred: ${job.matched_preferred.length}/${job.preferred_requirements.length}</div></div>`;
    }).join('') : '<p>No jobs imported yet. Run discovery or add a manual job.</p>';
  }

  const renderBeforePhase5 = render;
  render = function phase5Render(state) {
    renderBeforePhase5(state);
    renderPhase5Jobs(state, state.session_state, Boolean(state.onboarding_busy));
  };

  document.getElementById('job-discover').addEventListener('click', () => invoke('discover_jobs'));
  document.getElementById('job-board-form').addEventListener('submit', event => {
    event.preventDefault();
    invoke('add_verified_job_board', document.getElementById('job-board-provider').value, document.getElementById('job-board-employer').value, document.getElementById('job-board-token').value);
  });
  document.getElementById('job-board-list').addEventListener('change', event => {
    const id = event.target.dataset.jobBoardId;
    if (id) invoke('set_job_board_enabled', id, event.target.checked);
  });
  document.getElementById('manual-job-form').addEventListener('submit', event => {
    event.preventDefault();
    invoke('import_manual_job', {
      employer: document.getElementById('manual-job-employer').value,
      title: document.getElementById('manual-job-title').value,
      location: document.getElementById('manual-job-location').value,
      workplace_type: document.getElementById('manual-job-workplace').value,
      employment_type: document.getElementById('manual-job-employment').value,
      source_url: document.getElementById('manual-job-url').value,
      description: document.getElementById('manual-job-description').value,
    });
  });

  if (latestState) renderPhase5Jobs(latestState, latestState.session_state, Boolean(latestState.onboarding_busy));
})();
