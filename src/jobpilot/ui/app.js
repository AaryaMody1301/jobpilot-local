const titles = { dashboard: 'Dashboard', resume: 'Resume & facts', jobs: 'Jobs', settings: 'Targeting', history: 'History', system: 'Local data' };
let latestState = null;
let refreshTimer = null;

function csv(value) { return value.split(',').map(v => v.trim()).filter(Boolean); }
function toast(message) { const el = document.getElementById('toast'); el.textContent = message; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 2200); }
function escapeHtml(value) { const div = document.createElement('div'); div.textContent = String(value ?? ''); return div.innerHTML; }
function escapeAttr(value) { return escapeHtml(value).replaceAll('"', '&quot;').replaceAll("'", '&#39;'); }
function shortHash(value) { return value ? `${String(value).slice(0, 12)}…` : '—'; }
function setBusy(message) { document.getElementById('fact-bank-status').textContent = message || ''; }

async function invoke(name, ...args) {
  try {
    const result = await window.pywebview.api[name](...args);
    render(result);
    return result;
  } catch (error) {
    toast(error.message || String(error));
    throw error;
  }
}

function render(state) {
  latestState = state;
  const session = state.session_state;
  const badge = document.getElementById('session-badge');
  badge.textContent = session;
  badge.className = `status ${session}`;
  const onboardingBusy = Boolean(state.onboarding_busy);
  document.getElementById('start-button').disabled = onboardingBusy || !(session === 'idle' || session === 'paused');
  document.getElementById('pause-button').disabled = session !== 'running';
  document.getElementById('stop-button').disabled = !(session === 'running' || session === 'paused');
  document.getElementById('reset-sample').disabled = onboardingBusy || session !== 'idle';

  const work = document.getElementById('sample-work');
  work.innerHTML = state.sample_work.map(item => `<div class="work-item"><span>${escapeHtml(item.label)}</span><span class="pill">${escapeHtml(item.state)}</span></div>`).join('');
  const activity = document.getElementById('activity');
  activity.innerHTML = state.activity.map(item => `<div class="activity-item"><strong>${escapeHtml(item.event_type)}</strong><span>${escapeHtml(item.message)}</span><br><time>${escapeHtml(item.created_at)}</time></div>`).join('');
  document.getElementById('data-root').textContent = state.data_root;

  const resume = state.resume;
  document.getElementById('resume-ready').textContent = resume.onboarding_ready ? 'Ready' : 'Not ready';
  document.getElementById('resume-ready-detail').textContent = resume.onboarding_ready ? 'Baseline, mapping, and facts resolved' : 'No tailoring or submission until onboarding is complete';
  document.getElementById('fact-revision').textContent = resume.fact_bank_revision;
  document.getElementById('fact-summary').textContent = `${resume.fact_counts.approved || 0} approved · ${resume.fact_counts.candidate || 0} candidate`;
  renderResume(resume, session, onboardingBusy);

  const t = state.targeting;
  document.getElementById('roles').value = t.roles.join(', ');
  document.getElementById('min-years').value = t.target_experience_min_years;
  document.getElementById('max-years').value = t.target_experience_max_years;
  document.getElementById('india-cities').value = t.india_office_cities.join(', ');
  document.getElementById('remote-city').value = t.remote_origin_city;
  document.getElementById('remote-country').value = t.remote_origin_country;
  document.getElementById('remote-origin-required').checked = t.remote_must_allow_origin;
  document.getElementById('salary-minimum').value = t.salary_minimum === null ? '' : t.salary_minimum;
  document.getElementById('notice-days').value = t.notice_period_days;
  document.getElementById('employment-types').value = t.employment_types.join(', ');
  document.getElementById('excluded-employers').value = t.excluded_employers.join(', ');
  document.getElementById('relocation').checked = t.relocation_outside_india;
  document.getElementById('sponsorship').checked = t.require_overseas_sponsorship;
}

function renderResume(resume, session, onboardingBusy) {
  const idle = session === 'idle' && !onboardingBusy;
  const master = resume.master;
  document.getElementById('import-master').disabled = !idle;
  document.getElementById('import-supporting').disabled = !idle;
  document.getElementById('install-tectonic').disabled = !idle || resume.tectonic.installed;
  document.getElementById('compile-cached').disabled = !idle || !master || !resume.tectonic.installed;
  document.getElementById('compile-network').disabled = !idle || !master || !resume.tectonic.installed;
  document.getElementById('confirm-template-map').disabled = !idle || !master || !resume.regions.length || resume.template_map_status === 'confirmed';

  document.getElementById('master-summary').innerHTML = master
    ? `<div><strong>${escapeHtml(master.original_name)}</strong><span>Integrity: ${escapeHtml(resume.integrity)}</span><span>SHA-256: ${escapeHtml(shortHash(master.sha256))}</span><span>Imported: ${escapeHtml(master.imported_at)}</span></div>`
    : '<p>No master resume imported. Select your actual UTF-8 `.tex` source.</p>';

  const tectonic = resume.tectonic;
  document.getElementById('tectonic-summary').innerHTML = `<div><strong>${tectonic.installed ? 'Installed' : 'Not installed'}</strong><span>Version: ${escapeHtml(tectonic.version)}</span><span>Integrity: ${escapeHtml(tectonic.integrity)}</span><span>App-managed Windows x64 binary</span></div>`;

  const baseline = resume.baseline;
  document.getElementById('baseline-summary').innerHTML = baseline
    ? `<div><strong>Status: ${escapeHtml(baseline.status)}</strong><span>Pages: ${baseline.page_count ?? '—'}</span><span>Compiler: ${escapeHtml(baseline.compiler_version || 'not run')}</span><span>Offline verified: ${baseline.offline_verified ? 'yes' : 'no'}</span>${baseline.compile_error ? `<span class="error-text">${escapeHtml(baseline.compile_error)}</span>` : ''}${baseline.source_metrics?.external_inputs?.length ? `<span>Referenced local files: ${escapeHtml(baseline.source_metrics.external_inputs.join(', '))}</span>` : ''}</div>`
    : '<p>Import a master resume to establish its source baseline.</p>';

  document.getElementById('template-status').textContent = `Mapping status: ${resume.template_map_status}. ${resume.regions.filter(r => Number(r.editable) === 1).length} of ${resume.regions.length} regions marked editable.`;
  document.getElementById('template-regions').innerHTML = resume.regions.length
    ? resume.regions.map(region => `<label class="region-item"><input type="checkbox" data-region-id="${escapeHtml(region.id)}" ${Number(region.editable) === 1 ? 'checked' : ''} ${idle ? '' : 'disabled'}><span><strong>${escapeHtml(region.section_name)}</strong> · lines ${region.line_start}-${region.line_end}<br>${escapeHtml(region.display_text)}</span></label>`).join('')
    : '<p>No candidate bullet regions yet.</p>';

  document.getElementById('fact-bank-status').textContent = onboardingBusy ? `Busy: ${latestState.onboarding_busy}` : `Revision ${resume.fact_bank_revision}`;
  document.getElementById('fact-list').innerHTML = resume.facts.length
    ? resume.facts.map(fact => `<div class="fact-item" data-fact-id="${escapeHtml(fact.id)}"><div class="fact-meta"><code>${escapeHtml(fact.id)}</code><span class="pill ${escapeHtml(fact.current_status)}">${escapeHtml(fact.current_status)} · v${fact.current_version}</span></div><input class="fact-value" type="text" maxlength="2000" value="${escapeAttr(fact.value_text)}" ${idle ? '' : 'disabled'}><select class="fact-category" ${idle ? '' : 'disabled'}>${resume.fact_categories.map(category => `<option value="${escapeHtml(category)}" ${category === fact.current_category ? 'selected' : ''}>${escapeHtml(category)}</option>`).join('')}</select><div class="fact-source">Source: ${escapeHtml(fact.source_name)} · ${escapeHtml(JSON.stringify(fact.source_ref))}</div><div class="button-row"><button data-fact-action="save" ${idle ? '' : 'disabled'}>Save revision</button><button data-fact-action="approved" ${idle ? '' : 'disabled'}>Approve</button><button data-fact-action="rejected" ${idle ? '' : 'disabled'}>Reject</button></div></div>`).join('')
    : '<p>No candidate facts. Import the master resume or add a sourced fact.</p>';

  document.getElementById('supporting-list').innerHTML = resume.supporting_documents.length
    ? resume.supporting_documents.map(doc => `<div><strong>${escapeHtml(doc.original_name)}</strong><span>SHA-256: ${escapeHtml(shortHash(doc.sha256))}</span><span>Integrity at import: ${escapeHtml(doc.integrity_status)}</span></div>`).join('')
    : '<p>No supporting sources registered.</p>';

  const sources = master ? [master, ...resume.supporting_documents] : [...resume.supporting_documents];
  const sourceSelect = document.getElementById('fact-source');
  const currentSource = sourceSelect.value;
  sourceSelect.innerHTML = sources.map(doc => `<option value="${escapeHtml(doc.id)}">${escapeHtml(doc.original_name)}</option>`).join('');
  if (sources.some(doc => doc.id === currentSource)) sourceSelect.value = currentSource;
  sourceSelect.disabled = !idle || sources.length === 0;
  document.getElementById('fact-category').innerHTML = resume.fact_categories.map(category => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`).join('');
  document.querySelector('#fact-form button[type="submit"]').disabled = !idle || sources.length === 0;
}

function targetingFromForm() {
  return {
    ...latestState.targeting,
    roles: csv(document.getElementById('roles').value),
    target_experience_min_years: Number(document.getElementById('min-years').value),
    target_experience_max_years: Number(document.getElementById('max-years').value),
    india_office_cities: csv(document.getElementById('india-cities').value),
    remote_origin_city: document.getElementById('remote-city').value.trim(),
    remote_origin_country: document.getElementById('remote-country').value.trim(),
    remote_must_allow_origin: document.getElementById('remote-origin-required').checked,
    salary_minimum: document.getElementById('salary-minimum').value.trim() === '' ? null : Number(document.getElementById('salary-minimum').value),
    notice_period_days: Number(document.getElementById('notice-days').value),
    employment_types: csv(document.getElementById('employment-types').value),
    excluded_employers: csv(document.getElementById('excluded-employers').value),
    relocation_outside_india: document.getElementById('relocation').checked,
    require_overseas_sponsorship: document.getElementById('sponsorship').checked,
  };
}

function showView(name) {
  document.querySelectorAll('.view').forEach(el => el.classList.toggle('active', el.id === name));
  document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.view === name));
  document.getElementById('page-title').textContent = titles[name];
}

document.getElementById('nav').addEventListener('click', e => { const name = e.target.dataset.view; if (name) showView(name); });
document.getElementById('start-button').addEventListener('click', () => invoke('start'));
document.getElementById('pause-button').addEventListener('click', () => invoke('pause'));
document.getElementById('stop-button').addEventListener('click', () => invoke('stop'));
document.getElementById('reset-sample').addEventListener('click', async () => { await invoke('reset_sample_work'); toast('Sample items reset'); });
document.getElementById('import-master').addEventListener('click', async () => { await invoke('choose_master_resume'); toast('Master resume import finished'); });
document.getElementById('import-supporting').addEventListener('click', async () => { await invoke('choose_supporting_document'); toast('Supporting source import finished'); });
document.getElementById('install-tectonic').addEventListener('click', async () => {
  if (!window.confirm('Download the pinned Tectonic 0.17.0 Windows x64 archive (~20 MB) from its official GitHub release and verify its SHA-256?')) return;
  setBusy('Installing Tectonic…');
  await invoke('install_tectonic');
  toast('Tectonic installed and verified');
});
document.getElementById('compile-cached').addEventListener('click', async () => { setBusy('Compiling from cache…'); await invoke('compile_master_resume', false); toast('Baseline compiled from cached packages'); });
document.getElementById('compile-network').addEventListener('click', async () => {
  if (!window.confirm('Allow Tectonic to access the internet only for missing support packages during this baseline compile? The next cached-only compile must also pass.')) return;
  setBusy('Compiling and populating package cache…');
  await invoke('compile_master_resume', true);
  toast('Baseline compiled; rerun cached-only to verify offline readiness');
});
document.getElementById('confirm-template-map').addEventListener('click', async () => { await invoke('confirm_template_map'); toast('Template mapping confirmed'); });
document.getElementById('template-regions').addEventListener('change', async e => {
  const id = e.target.dataset.regionId;
  if (id) await invoke('set_template_region_editable', id, e.target.checked);
});
document.getElementById('fact-list').addEventListener('click', async e => {
  const action = e.target.dataset.factAction;
  if (!action) return;
  const item = e.target.closest('.fact-item');
  const factId = item.dataset.factId;
  if (action === 'save') {
    await invoke('revise_fact', factId, item.querySelector('.fact-value').value, item.querySelector('.fact-category').value);
    toast('New candidate fact version saved');
  } else {
    await invoke('set_fact_status', factId, action);
    toast(`Fact marked ${action}`);
  }
});
document.getElementById('fact-form').addEventListener('submit', async e => {
  e.preventDefault();
  const payload = {
    source_document_id: document.getElementById('fact-source').value,
    category: document.getElementById('fact-category').value,
    locator: document.getElementById('fact-locator').value.trim(),
    value: document.getElementById('fact-value').value.trim(),
  };
  await invoke('create_fact', payload);
  document.getElementById('fact-locator').value = '';
  document.getElementById('fact-value').value = '';
  toast('Candidate fact added');
});
document.getElementById('targeting-form').addEventListener('submit', async e => {
  e.preventDefault();
  const save = document.getElementById('save-state');
  save.textContent = 'Saving...';
  try { await invoke('save_targeting', targetingFromForm()); save.textContent = 'Saved locally'; toast('Targeting saved'); }
  catch { save.textContent = 'Not saved'; }
});

window.addEventListener('pywebviewready', async () => {
  await invoke('get_state');
  refreshTimer = setInterval(async () => {
    if (latestState && (latestState.session_state === 'running' || latestState.session_state === 'paused' || latestState.onboarding_busy)) {
      try { render(await window.pywebview.api.get_state()); } catch (_) { clearInterval(refreshTimer); }
    }
  }, 500);
});
