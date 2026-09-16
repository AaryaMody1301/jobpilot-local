(() => {
  if (document.getElementById('phase9-distribution')) return;

  document.querySelector('.privacy-note').textContent = 'No telemetry. No cloud AI. Phase 9 distribution and recovery are local; the real-application pilot is still locked.';
  document.querySelector('.eyebrow').textContent = 'PHASE 9 · DISTRIBUTION & RECOVERY';
  const dashboardBanner = document.querySelector('#dashboard .banner');
  if (dashboardBanner) dashboardBanner.innerHTML = '<strong>Distribution-ready local workspace.</strong> Phase 9 adds verified Windows packaging plus local backup/restore. Real employer filling and submission remain disabled until a separate explicit pilot authorization is recorded.';

  const system = document.getElementById('system');
  const section = document.createElement('div');
  section.id = 'phase9-distribution';
  section.innerHTML = `
    <div class="banner"><strong>Real-application pilot is not active.</strong> This build intentionally contains no user-facing activation action for employer writes. Distribution/recovery work can be accepted independently.</div>
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
      <h2>Pilot boundary</h2>
      <div id="phase9-pilot" class="detail-list"></div>
      <p class="muted">Prepared employer applications remain read-only. CAPTCHA, login/verification, assessment, payment, unsupported-form and UNCERTAIN rules remain unchanged.</p>
    </article>`;
  system.prepend(section);

  function renderPhase9(state) {
    const distribution = state.distribution;
    if (!distribution) return;
    const backup = distribution.backup || {};
    const pending = Boolean(backup.restore_pending);
    document.getElementById('phase9-install').innerHTML = `<div><span>App version</span><strong>${escapeHtml(distribution.app_version || '')}</strong></div><div><span>Target</span><strong>Windows 10/11 x64</strong></div><div><span>Data root</span><strong>Separate from installed program files</strong></div>`;
    document.getElementById('phase9-backup').innerHTML = `<div><span>Backup format</span><strong>v${Number(backup.format_version || 1)}</strong></div><div><span>Local backups</span><strong>${Number(backup.local_backups || 0)}</strong></div><div><span>Restore staged</span><strong>${pending ? 'Yes - restart required' : 'No'}</strong></div>${backup.latest_backup ? `<div><span>Latest backup</span><strong class="path">${escapeHtml(backup.latest_backup)}</strong></div>` : ''}${distribution.restore_applied_on_launch ? `<div><span>Restore applied on launch</span><strong>Yes</strong></div>` : ''}`;
    document.getElementById('phase9-pilot').innerHTML = `<div><span>Explicit pilot authorization</span><strong>${distribution.pilot_authorized ? 'Authorized' : 'Not authorized'}</strong></div><div><span>Real employer submission</span><strong>${distribution.real_employer_submission_enabled ? 'Enabled' : 'Disabled'}</strong></div><div><span>Activation action in this build</span><strong>${distribution.pilot_activation_available ? 'Available' : 'Intentionally unavailable'}</strong></div>`;
    document.getElementById('phase9-create-backup').disabled = pending || state.session_state !== 'idle';
    document.getElementById('phase9-restore-backup').disabled = pending || state.session_state !== 'idle';
  }

  const renderBeforePhase9 = render;
  render = function phase9Render(state) {
    renderBeforePhase9(state);
    renderPhase9(state);
  };

  document.getElementById('phase9-create-backup').addEventListener('click', () => invoke('choose_local_backup'));
  document.getElementById('phase9-restore-backup').addEventListener('click', () => invoke('choose_local_restore'));

  if (latestState) renderPhase9(latestState);
})();
