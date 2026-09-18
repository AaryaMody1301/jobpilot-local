(() => {
  if (document.getElementById('phase9-distribution')) return;

  document.querySelector('.privacy-note').textContent = 'No telemetry. No cloud AI. Phase 9 keeps distribution and recovery local; the measured real-application pilot is explicit, per-launch, and fail-closed.';
  document.querySelector('.eyebrow').textContent = 'PHASE 9 · DISTRIBUTION & MEASURED PILOT';
  const dashboardBanner = document.querySelector('#dashboard .banner');
  if (dashboardBanner) dashboardBanner.innerHTML = '<strong>User-authorized measured pilot.</strong> Every launch starts with real employer writes inactive. Activate locally, inspect a supported prepared form, and explicitly arm each application. CAPTCHA/challenge, stale-package, eligibility, answer and resume-review gates remain authoritative.';

  const system = document.getElementById('system');
  const section = document.createElement('div');
  section.id = 'phase9-distribution';
  section.innerHTML = `
    <div class="banner"><strong>Real submissions are off by default on every launch.</strong> Activation does not queue anything. A prepared application must pass read-only recognition and then be armed individually before the existing single worker can submit it.</div>
    <div class="grid two">
      <article class="card">
        <h2>Windows distribution</h2>
        <div id="phase9-install" class="detail-list"></div>
        <p class="muted">The release bundle is a verified per-user Windows x64 onedir package. Setup/upgrade replaces program files only; private JobPilot data stays under the separate local data root.</p>
      </article>
      <article class="card">
        <h2>Portable backup</h2>
        <div id="phase9-backup" class="detail-list"></div>
        <div class="button-row"><button id="phase9-create-backup" class="primary">Create backup</button><button id="phase9-restore-backup">Restore backup</button></div>
        <p class="muted">Backups contain SQLite state, private source documents and application artifacts. Models, tools, browser/profile data, caches, runtime files and logs are machine-specific and are not transferred.</p>
      </article>
    </div>
    <article class="card section-card">
      <h2>Measured real-application pilot</h2>
      <div id="phase9-pilot" class="detail-list"></div>
      <div class="form-row">
        <label>Activation phrase<input id="phase9-pilot-confirmation" maxlength="80" autocomplete="off"></label>
        <button id="phase9-activate-pilot" class="primary">Activate for this launch</button>
        <button id="phase9-deactivate-pilot">Deactivate</button>
      </div>
      <p id="phase9-pilot-help" class="muted"></p>
      <p class="muted">Activation resets on restart. It never bypasses the five-resume automatic-tailoring gate, eligibility decisions, immutable-package freshness, exact-context application answers, provider blockers, or terminal UNCERTAIN handling.</p>
    </article>`;
  system.prepend(section);

  function pilotQueueButtons(state) {
    const distribution = state.distribution || {};
    const orchestration = state.orchestration || {};
    const attention = orchestration.attention || [];
    document.querySelectorAll('[data-phase8-inspect]').forEach(button => {
      const id = button.dataset.phase8Inspect;
      const item = attention.find(entry => entry.id === id);
      if (!item || item.state !== 'prepared') return;
      const live = item.live_form || {};
      const eligible = distribution.pilot_session_active && live.read_only && live.supported && !(live.blockers || []).length && Number(live.submit_controls || 0) === 1;
      const container = button.parentElement;
      if (!container) return;
      const existing = container.querySelector(`[data-phase9-pilot-queue="${CSS.escape(id)}"]`);
      if (eligible && !existing) {
        button.insertAdjacentHTML('afterend', `<button data-phase9-pilot-queue="${escapeAttr(id)}" class="primary">Arm one measured pilot submission</button>`);
      } else if (!eligible && existing) {
        existing.remove();
      }
    });
  }

  function renderPhase9(state) {
    const distribution = state.distribution;
    if (!distribution) return;
    const backup = distribution.backup || {};
    const pending = Boolean(backup.restore_pending);
    const active = Boolean(distribution.pilot_session_active);
    const phrase = distribution.pilot_confirmation_phrase || '';
    document.getElementById('phase9-install').innerHTML = `<div><span>App version</span><strong>${escapeHtml(distribution.app_version || '')}</strong></div><div><span>Target</span><strong>Windows 10/11 x64</strong></div><div><span>Data root</span><strong>Separate from installed program files</strong></div>`;
    document.getElementById('phase9-backup').innerHTML = `<div><span>Backup format</span><strong>v${Number(backup.format_version || 1)}</strong></div><div><span>Local backups</span><strong>${Number(backup.local_backups || 0)}</strong></div><div><span>Restore staged</span><strong>${pending ? 'Yes - restart required' : 'No'}</strong></div>${backup.latest_backup ? `<div><span>Latest backup</span><strong class="path">${escapeHtml(backup.latest_backup)}</strong></div>` : ''}${distribution.restore_applied_on_launch ? `<div><span>Restore applied on launch</span><strong>Yes</strong></div>` : ''}`;
    document.getElementById('phase9-pilot').innerHTML = `<div><span>Project authorization</span><strong>${distribution.pilot_authorized ? 'Recorded' : 'Not authorized'}</strong></div><div><span>This launch</span><strong>${active ? 'ACTIVE' : 'Inactive'}</strong></div><div><span>Real employer submission lane</span><strong>${distribution.real_employer_submission_enabled ? 'Enabled for individually armed applications' : 'Disabled'}</strong></div><div><span>Armed this launch</span><strong>${Number(distribution.pilot_armed_this_launch || 0)} / ${Number(distribution.pilot_arm_limit || 0)}</strong></div><div><span>Policy</span><strong>${escapeHtml(distribution.pilot_policy_revision || '')}</strong></div>`;
    const confirmation = document.getElementById('phase9-pilot-confirmation');
    confirmation.placeholder = phrase;
    document.getElementById('phase9-pilot-help').textContent = active ? 'Pilot is active for this launch. Inspect a prepared application in the Attention lane, then explicitly arm it.' : `To activate, type exactly: ${phrase}`;
    document.getElementById('phase9-create-backup').disabled = pending || state.session_state !== 'idle';
    document.getElementById('phase9-restore-backup').disabled = pending || state.session_state !== 'idle';
    confirmation.disabled = active || pending || state.session_state !== 'idle';
    document.getElementById('phase9-activate-pilot').disabled = active || pending || state.session_state !== 'idle' || confirmation.value.trim() !== phrase;
    document.getElementById('phase9-deactivate-pilot').disabled = !active || pending || state.session_state !== 'idle';
    pilotQueueButtons(state);
  }

  const renderBeforePhase9 = render;
  render = function phase9Render(state) {
    renderBeforePhase9(state);
    renderPhase9(state);
  };

  document.getElementById('phase9-create-backup').addEventListener('click', () => invoke('choose_local_backup'));
  document.getElementById('phase9-restore-backup').addEventListener('click', () => invoke('choose_local_restore'));
  document.getElementById('phase9-pilot-confirmation').addEventListener('input', event => {
    const distribution = latestState?.distribution || {};
    const pending = Boolean(distribution.backup?.restore_pending);
    const active = Boolean(distribution.pilot_session_active);
    document.getElementById('phase9-activate-pilot').disabled = active || pending || latestState?.session_state !== 'idle' || event.target.value.trim() !== (distribution.pilot_confirmation_phrase || '');
  });
  document.getElementById('phase9-activate-pilot').addEventListener('click', () => {
    const confirmation = document.getElementById('phase9-pilot-confirmation').value;
    const phrase = latestState?.distribution?.pilot_confirmation_phrase || '';
    if (confirmation.trim() !== phrase) return;
    invoke('activate_real_application_pilot', confirmation);
  });
  document.getElementById('phase9-deactivate-pilot').addEventListener('click', () => invoke('deactivate_real_application_pilot'));
  document.getElementById('phase8-attention').addEventListener('click', event => {
    const id = event.target.dataset.phase9PilotQueue;
    if (id) invoke('queue_prepared_pilot_application', id);
  });

  if (latestState) renderPhase9(latestState);
})();
