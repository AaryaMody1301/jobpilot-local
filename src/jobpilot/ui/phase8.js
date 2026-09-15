(() => {
  if (document.getElementById('phase8-orchestration')) return;

  document.querySelector('.privacy-note').textContent = 'No telemetry. No cloud AI. Phase 8 orchestrates locally; real employer submission remains disabled until Phase 9.';
  document.querySelector('.eyebrow').textContent = 'PHASE 8 · END-TO-END ORCHESTRATION';
  const dashboardBanner = document.querySelector('#dashboard .banner');
  if (dashboardBanner) dashboardBanner.innerHTML = '<strong>End-to-end local orchestration.</strong> Explicit Start may refresh verified public boards, match jobs, prepare evidence-backed resumes and run controlled loopback submissions. Human review, stale-package, challenge and resource gates never weaken to chase the daily target. Real employer writes remain disabled until Phase 9.';

  const history = document.getElementById('history');
  const section = document.createElement('div');
  section.id = 'phase8-orchestration';
  section.innerHTML = `
    <div class="banner"><strong>Phase 9 activation boundary.</strong> Prepared real-employer applications remain read-only. Live form inspection can recognize supported fields and blockers, but Phase 8 never calls provider fill/submit on an employer page.</div>
    <div class="grid two">
      <article class="card">
        <h2>Local-day objective</h2>
        <div id="phase8-daily" class="detail-list"></div>
        <p class="muted">50 confirmed, well-matched real applications is a target, not a ceiling. Controlled fixtures never count toward it.</p>
      </article>
      <article class="card">
        <h2>Orchestration worker</h2>
        <div id="phase8-worker" class="detail-list"></div>
        <p class="muted">Discovery and tailoring run only during an explicit session. Critical resource pressure pauses new tailoring at a safe boundary.</p>
      </article>
    </div>
    <article class="card section-card">
      <div class="card-heading"><div><h2>Attention lane</h2><p>Eligibility unknowns, first-five resume reviews, stale packages, blockers and Phase 9 activation waits stay visible without blocking unrelated work.</p></div><span id="phase8-attention-count" class="muted"></span></div>
      <div id="phase8-attention" class="fact-list"></div>
    </article>
    <article class="card section-card">
      <div class="card-heading"><div><h2>Application history</h2><p>Discovery, eligibility, tailoring, package, controlled submission and terminal outcomes are persisted in the existing application journal.</p></div><span id="phase8-counts" class="muted"></span></div>
      <div id="phase8-history" class="fact-list"></div>
    </article>`;
  history.prepend(section);

  function identity(item) {
    if (item.employer || item.title) return `${item.employer || 'Unknown employer'} · ${item.title || 'Unknown role'}`;
    return item.job_identity || item.id;
  }

  function attentionAction(item) {
    if (item.attention_kind === 'eligibility_review') {
      return `<div class="form-row"><label>Review note<input data-phase8-eligibility-note="${escapeAttr(item.id)}" maxlength="1000" placeholder="Record the evidence/decision" required></label><button data-phase8-eligibility="approved" data-id="${escapeAttr(item.id)}" class="primary">Mark eligible</button><button data-phase8-eligibility="rejected" data-id="${escapeAttr(item.id)}">Mark ineligible</button></div>`;
    }
    if (item.attention_kind === 'tailoring_prerequisite') {
      return `<button data-phase8-retry-tailoring="${escapeAttr(item.id)}" class="primary">Retry tailoring</button>`;
    }
    if (item.attention_kind === 'pilot_activation_required' || item.attention_kind === 'live_form_blocked') {
      const live = item.live_form || {};
      const blockers = (live.blockers || []).length ? `<br>Live blockers: ${escapeHtml(live.blockers.join(', '))}` : '';
      return `<div class="fact-source">Read-only recognition: ${live.read_only ? (live.supported ? 'supported form shape' : 'unsupported/blocking form shape') : 'not checked'}${blockers}</div><button data-phase8-inspect="${escapeAttr(item.id)}">Inspect live form read-only</button>`;
    }
    return '';
  }

  function renderPhase8(state) {
    const orchestration = state.orchestration;
    if (!orchestration) return;
    const daily = orchestration.daily || {};
    document.getElementById('phase8-daily').innerHTML = `<div><span>Local date</span><strong>${escapeHtml(daily.local_date || '')}</strong></div><div><span>Confirmed real</span><strong>${Number(daily.confirmed_real || 0)} / ${Number(daily.target_confirmed || 50)}</strong></div><div><span>Remaining to target</span><strong>${Number(daily.remaining_to_target || 0)}</strong></div><div><span>Controlled confirmations</span><strong>${Number(daily.confirmed_controlled || 0)} (excluded)</strong></div>`;

    const worker = orchestration.worker || {};
    document.getElementById('phase8-worker').innerHTML = `<div><span>Status</span><strong>${escapeHtml(worker.status || (worker.alive ? 'Running' : 'Idle'))}</strong></div><div><span>Current application</span><strong>${escapeHtml(worker.current_application_id || 'None')}</strong></div><div><span>Immutable packages</span><strong>${Number(orchestration.packages || 0)}</strong></div>${worker.last_error ? `<div><span>Last worker error</span><strong class="error-text">${escapeHtml(worker.last_error)}</strong></div>` : ''}`;

    const counts = Object.entries(orchestration.counts || {}).sort().map(([key, value]) => `${key}: ${value}`).join(' · ');
    document.getElementById('phase8-counts').textContent = counts || 'No orchestrated applications yet';
    document.getElementById('phase8-attention-count').textContent = `${orchestration.attention.length} item${orchestration.attention.length === 1 ? '' : 's'}`;
    document.getElementById('phase8-attention').innerHTML = orchestration.attention.length ? orchestration.attention.map(item => {
      const eligibility = item.eligibility || {};
      const reasons = [...(eligibility.hard_reasons || []), ...(eligibility.review_reasons || [])];
      return `<div class="fact-item"><div class="fact-meta"><span class="pill ${escapeAttr(item.state)}">${escapeHtml(item.state)}</span><strong>${escapeHtml(identity(item))}</strong></div><div class="fact-source">${escapeHtml(item.attention_kind.replaceAll('_', ' '))}${reasons.length ? `<br>${escapeHtml(reasons.join(' · '))}` : ''}${item.last_reason ? `<br>${escapeHtml(item.last_reason)}` : ''}</div>${attentionAction(item)}</div>`;
    }).join('') : '<p>No orchestration item currently needs attention.</p>';

    document.getElementById('phase8-history').innerHTML = orchestration.history.length ? orchestration.history.map(item => {
      const packageHash = item.package_manifest_sha256 ? `<br>Package ${escapeHtml(item.package_manifest_sha256.slice(0, 16))}…` : '';
      const controlled = item.controlled_fixture ? ' · controlled fixture' : '';
      return `<div class="fact-item"><div class="fact-meta"><span class="pill ${escapeAttr(item.state)}">${escapeHtml(item.state)}</span><strong>${escapeHtml(identity(item))}</strong></div><div class="fact-source">${escapeHtml(item.provider || 'legacy')}${controlled}${item.location ? ` · ${escapeHtml(item.location)}` : ''}<br>${escapeHtml(item.last_reason || '')}${packageHash}</div></div>`;
    }).join('') : '<p>No Phase 8 application history yet.</p>';
  }

  const renderBeforePhase8 = render;
  render = function phase8Render(state) {
    renderBeforePhase8(state);
    renderPhase8(state);
  };

  document.getElementById('phase8-attention').addEventListener('click', event => {
    const eligibility = event.target.dataset.phase8Eligibility;
    if (eligibility) {
      const id = event.target.dataset.id;
      const input = document.querySelector(`[data-phase8-eligibility-note="${CSS.escape(id)}"]`);
      invoke('resolve_application_eligibility', id, eligibility === 'approved', input ? input.value : '');
      return;
    }
    const retry = event.target.dataset.phase8RetryTailoring;
    if (retry) {
      invoke('retry_application_tailoring', retry);
      return;
    }
    const inspect = event.target.dataset.phase8Inspect;
    if (inspect) invoke('inspect_prepared_application', inspect);
  });

  if (latestState) renderPhase8(latestState);
})();
