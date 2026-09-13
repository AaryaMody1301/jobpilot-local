(() => {
  if (document.getElementById('application-queue-form')) return;

  document.querySelector('.privacy-note').textContent = 'No telemetry. No cloud AI. Phase 6 submits controlled localhost fixtures only.';
  document.querySelector('.eyebrow').textContent = 'PHASE 6 · CONTROLLED APPLICATION ENGINE';
  const dashboardBanner = document.querySelector('#dashboard .banner');
  if (dashboardBanner) dashboardBanner.innerHTML = '<strong>Controlled application-engine mode.</strong> Start runs one Playwright worker against localhost fixtures only. Real employer targets are rejected. CAPTCHA, assessments, login/verification, payment and unsupported required fields stop safely.';

  const history = document.getElementById('history');
  history.innerHTML = `
    <div class="banner"><strong>Development safety boundary.</strong> Only absolute localhost/loopback HTTP(S) fixtures can be queued in Phase 6. Real employer applications remain disabled until a later explicit pilot phase.</div>
    <div class="grid two">
      <article class="card">
        <h2>Queue controlled fixture</h2>
        <p>Use a local fixture server to exercise the transactional worker. Duplicate job identities are deduplicated.</p>
        <form id="application-queue-form">
          <label>Fixture job identity<input id="application-job-identity" maxlength="300" placeholder="fixture-data-engineer-001" required></label>
          <label>Local form URL<input id="application-target-url" type="url" maxlength="2000" placeholder="http://127.0.0.1:8000/form" required></label>
          <button type="submit" class="primary">Queue fixture</button>
        </form>
      </article>
      <article class="card">
        <h2>Single worker</h2>
        <div id="application-worker-summary" class="detail-list"></div>
        <p class="muted">Pause prevents new claims. Stop cancels pre-submit work; once Submit may have started, the worker waits only for explicit confirmation and ambiguity becomes UNCERTAIN.</p>
      </article>
    </div>
    <article class="card section-card">
      <div class="card-heading"><div><h2>Questions needing review</h2><p>Answers are reusable only for the exact semantic context fingerprint shown by the controlled fixture.</p></div><span id="application-question-count" class="muted"></span></div>
      <div id="application-questions" class="fact-list"></div>
    </article>
    <article class="card section-card">
      <div class="card-heading"><div><h2>Controlled application journal</h2><p>Every transition is persisted locally. UNCERTAIN is terminal and never automatically retried.</p></div><span id="application-counts" class="muted"></span></div>
      <div id="application-attempts" class="fact-list"></div>
    </article>`;

  function renderPhase6Applications(state) {
    const applications = state.applications;
    if (!applications) return;
    const worker = applications.worker || {};
    const workerSummary = document.getElementById('application-worker-summary');
    workerSummary.innerHTML = `<div><span>Status</span><strong>${worker.alive ? (worker.paused ? 'Paused' : 'Running') : 'Idle'}</strong></div><div><span>Current attempt</span><strong>${escapeHtml(worker.current_application_id || 'None')}</strong></div>${worker.last_error ? `<div><span>Worker error</span><strong class="error-text">${escapeHtml(worker.last_error)}</strong></div>` : ''}<div><span>Approved answers</span><strong>${applications.approved_answers}</strong></div>`;

    const counts = Object.entries(applications.counts || {}).sort().map(([key, value]) => `${key}: ${value}`).join(' · ');
    document.getElementById('application-counts').textContent = counts || 'No controlled attempts yet';
    document.getElementById('application-question-count').textContent = `${applications.open_questions.length} open`;

    document.getElementById('application-questions').innerHTML = applications.open_questions.length ? applications.open_questions.map(question => `
      <div class="fact-item">
        <strong>${escapeHtml(question.label)}</strong>
        <div class="fact-source">${escapeHtml(question.job_identity)} · key ${escapeHtml(question.question_key)}<br>Context ${escapeHtml(question.context_sha256.slice(0, 16))}…</div>
        <div class="form-row"><label>Approved answer<input data-application-answer="${escapeAttr(question.id)}" maxlength="4000"></label><button data-approve-application-question="${escapeAttr(question.id)}" class="primary">Approve & requeue</button></div>
      </div>`).join('') : '<p>No mandatory questions are waiting for review.</p>';

    document.getElementById('application-attempts').innerHTML = applications.attempts.length ? applications.attempts.map(attempt => `
      <div class="fact-item"><div class="fact-meta"><span class="pill ${escapeAttr(attempt.state)}">${escapeHtml(attempt.state)}</span><strong>${escapeHtml(attempt.job_identity)}</strong></div><div class="fact-source">${escapeHtml(attempt.target_url || '')}<br>${escapeHtml(attempt.last_reason || '')}${attempt.retry_count ? `<br>Safe pre-submit retries: ${attempt.retry_count}` : ''}</div></div>`).join('') : '<p>No controlled fixtures have been queued.</p>';
  }

  const renderBeforePhase6 = render;
  render = function phase6Render(state) {
    renderBeforePhase6(state);
    renderPhase6Applications(state);
  };

  document.getElementById('application-queue-form').addEventListener('submit', event => {
    event.preventDefault();
    invoke('queue_controlled_application', document.getElementById('application-job-identity').value, document.getElementById('application-target-url').value);
  });
  document.getElementById('application-questions').addEventListener('click', event => {
    const id = event.target.dataset.approveApplicationQuestion;
    if (!id) return;
    const input = document.querySelector(`[data-application-answer="${CSS.escape(id)}"]`);
    invoke('approve_application_question', id, input ? input.value : '');
  });

  if (latestState) renderPhase6Applications(latestState);
})();
