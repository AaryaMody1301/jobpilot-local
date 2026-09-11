const titles = { dashboard: 'Dashboard', resume: 'Resume & facts', model: 'Model & resources', tailoring: 'Tailor resume', jobs: 'Jobs', settings: 'Targeting', history: 'History', system: 'Local data' };
let latestState = null;
let refreshTimer = null;
let inspectedRunId = null;

function csv(value) { return value.split(',').map(v => v.trim()).filter(Boolean); }
function toast(message) { const el = document.getElementById('toast'); el.textContent = message; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 2600); }
function escapeHtml(value) { const div = document.createElement('div'); div.textContent = String(value ?? ''); return div.innerHTML; }
function escapeAttr(value) { return escapeHtml(value).replaceAll('"', '&quot;').replaceAll("'", '&#39;'); }
function shortHash(value) { return value ? `${String(value).slice(0, 12)}…` : '—'; }
function formatBytes(value) { const n = Number(value || 0); if (!n) return '0 B'; if (n >= 1024 ** 3) return `${(n / 1024 ** 3).toFixed(2)} GB`; if (n >= 1024 ** 2) return `${(n / 1024 ** 2).toFixed(0)} MB`; return `${Math.round(n / 1024)} KB`; }
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

async function invokeRaw(name, ...args) {
  try {
    return await window.pywebview.api[name](...args);
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
  const busy = Boolean(state.onboarding_busy);
  document.getElementById('start-button').disabled = busy || !(session === 'idle' || session === 'paused');
  document.getElementById('pause-button').disabled = session !== 'running';
  document.getElementById('stop-button').disabled = !(session === 'running' || session === 'paused');
  document.getElementById('reset-sample').disabled = busy || session !== 'idle';

  document.getElementById('sample-work').innerHTML = state.sample_work.map(item => `<div class="work-item"><span>${escapeHtml(item.label)}</span><span class="pill">${escapeHtml(item.state)}</span></div>`).join('');
  document.getElementById('activity').innerHTML = state.activity.map(item => `<div class="activity-item"><strong>${escapeHtml(item.event_type)}</strong><span>${escapeHtml(item.message)}</span><br><time>${escapeHtml(item.created_at)}</time></div>`).join('');
  document.getElementById('data-root').textContent = state.data_root;

  const resume = state.resume;
  document.getElementById('resume-ready').textContent = resume.onboarding_ready ? 'Ready' : 'Not ready';
  document.getElementById('resume-ready-detail').textContent = resume.onboarding_ready ? 'Offline baseline, mapping, and facts resolved' : 'Local private resume onboarding required';
  renderResume(resume, session, busy);
  if (state.model) renderModel(state.model, session, busy);
  if (state.tailoring) renderTailoring(state.tailoring, session, busy, resume, state.model);

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

function renderResume(resume, session, busy) {
  const idle = session === 'idle' && !busy;
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
    ? `<div><strong>Status: ${escapeHtml(baseline.status)}</strong><span>Pages: ${baseline.page_count ?? '—'}</span><span>Compiler: ${escapeHtml(baseline.compiler_version || 'not run')}</span><span>Offline verified: ${baseline.offline_verified ? 'yes' : 'no'}</span>${baseline.compile_error ? `<span class="error-text">${escapeHtml(baseline.compile_error)}</span>` : ''}</div>`
    : '<p>Import a master resume to establish its source baseline.</p>';
  document.getElementById('template-status').textContent = `Mapping status: ${resume.template_map_status}. ${resume.regions.filter(r => Number(r.editable) === 1).length} of ${resume.regions.length} regions marked editable.`;
  document.getElementById('template-regions').innerHTML = resume.regions.length
    ? resume.regions.map(region => `<label class="region-item"><input type="checkbox" data-region-id="${escapeAttr(region.id)}" ${Number(region.editable) === 1 ? 'checked' : ''} ${idle ? '' : 'disabled'}><span><strong>${escapeHtml(region.section_name)}</strong> · lines ${region.line_start}-${region.line_end}<br>${escapeHtml(region.display_text)}</span></label>`).join('')
    : '<p>No candidate bullet regions yet.</p>';
  document.getElementById('fact-bank-status').textContent = busy ? `Busy: ${latestState.onboarding_busy}` : `Revision ${resume.fact_bank_revision}`;
  document.getElementById('fact-list').innerHTML = resume.facts.length
    ? resume.facts.map(fact => `<div class="fact-item" data-fact-id="${escapeAttr(fact.id)}"><div class="fact-meta"><code>${escapeHtml(fact.id)}</code><span class="pill ${escapeAttr(fact.current_status)}">${escapeHtml(fact.current_status)} · v${fact.current_version}</span></div><input class="fact-value" type="text" maxlength="2000" value="${escapeAttr(fact.value_text)}" ${idle ? '' : 'disabled'}><select class="fact-category" ${idle ? '' : 'disabled'}>${resume.fact_categories.map(category => `<option value="${escapeAttr(category)}" ${category === fact.current_category ? 'selected' : ''}>${escapeHtml(category)}</option>`).join('')}</select><div class="fact-source">Source: ${escapeHtml(fact.source_name)} · ${escapeHtml(JSON.stringify(fact.source_ref))}</div><div class="button-row"><button data-fact-action="save" ${idle ? '' : 'disabled'}>Save revision</button><button data-fact-action="approved" ${idle ? '' : 'disabled'}>Approve</button><button data-fact-action="rejected" ${idle ? '' : 'disabled'}>Reject</button></div></div>`).join('')
    : '<p>No candidate facts. Import the master resume or add a sourced fact.</p>';
  document.getElementById('supporting-list').innerHTML = resume.supporting_documents.length
    ? resume.supporting_documents.map(doc => `<div><strong>${escapeHtml(doc.original_name)}</strong><span>SHA-256: ${escapeHtml(shortHash(doc.sha256))}</span><span>Integrity at import: ${escapeHtml(doc.integrity_status)}</span></div>`).join('')
    : '<p>No supporting sources registered.</p>';
  const sources = master ? [master, ...resume.supporting_documents] : [...resume.supporting_documents];
  const sourceSelect = document.getElementById('fact-source');
  const currentSource = sourceSelect.value;
  sourceSelect.innerHTML = sources.map(doc => `<option value="${escapeAttr(doc.id)}">${escapeHtml(doc.original_name)}</option>`).join('');
  if (sources.some(doc => doc.id === currentSource)) sourceSelect.value = currentSource;
  sourceSelect.disabled = !idle || sources.length === 0;
  document.getElementById('fact-category').innerHTML = resume.fact_categories.map(category => `<option value="${escapeAttr(category)}">${escapeHtml(category)}</option>`).join('');
  document.querySelector('#fact-form button[type="submit"]').disabled = !idle || sources.length === 0;
}

function modelConfigurations(model) {
  const configs = [];
  for (const runtime of model.catalogue.runtimes) {
    if (!runtime.install || runtime.install.status !== 'installed') continue;
    if (runtime.backend === 'cpu') {
      configs.push({ runtimeId: runtime.id, deviceId: 'none', label: `${runtime.id} · CPU only` });
      continue;
    }
    for (const device of runtime.devices || []) configs.push({ runtimeId: runtime.id, deviceId: device.id, label: `${runtime.id} · ${device.id} · ${device.name}` });
  }
  return configs;
}

function renderModel(model, session, busy) {
  const idle = session === 'idle' && !busy;
  const hardware = model.hardware;
  const selected = model.selection.selected_model_install_id;
  const gate = model.review_gate;
  document.getElementById('model-ready').textContent = model.auto_tailoring_enabled ? 'Ready' : selected ? 'Selected for review' : 'Not selected';
  document.getElementById('model-ready-detail').textContent = model.auto_tailoring_enabled
    ? 'Automatic local tailoring enabled after persisted review gate'
    : selected ? `${gate?.approved_distinct_resumes || 0}/5 distinct resume approvals · auto-tailoring disabled` : 'Auto-tailoring disabled · device evaluation required';
  document.getElementById('refresh-hardware').disabled = !idle;
  document.getElementById('check-model-updates').disabled = !idle || !model.update_check_due;

  const gpus = hardware.gpus.length
    ? hardware.gpus.map(gpu => `${escapeHtml(gpu.name)} · VRAM ${gpu.total_vram_bytes ? formatBytes(gpu.total_vram_bytes) : 'unknown'} · ${escapeHtml(gpu.evidence)}`).join('<br>')
    : 'No supported GPU evidence detected';
  const runtimeDevices = Object.entries(hardware.runtime_devices || {}).flatMap(([runtimeId, devices]) => (devices || []).map(device => `${runtimeId}: ${device.id} ${device.name} · free ${formatBytes(device.free_memory_bytes)}`));
  document.getElementById('hardware-summary').innerHTML = `<div><strong>${formatBytes(hardware.memory.total_bytes)} RAM</strong><span>Available now: ${formatBytes(hardware.memory.available_bytes)}</span><span>Reserved model RAM budget: ${formatBytes(hardware.budget.model_ram_budget_bytes)}</span><span>Model disk budget: ${formatBytes(hardware.budget.model_disk_budget_bytes)}</span><span>Memory pressure: ${escapeHtml(hardware.budget.memory_pressure)}</span><span>CPU: ${escapeHtml(hardware.cpu.physical_cores)} physical / ${escapeHtml(hardware.cpu.logical_cores)} logical cores · ${escapeHtml((hardware.cpu.features || []).join(', ') || 'features unavailable')}</span><span>OS GPU evidence: ${gpus}</span><span>llama.cpp devices: ${runtimeDevices.length ? runtimeDevices.map(escapeHtml).join('<br>') : 'none discovered from an installed runtime'}</span></div>`;

  const rec = model.recommendation;
  document.getElementById('model-recommendation').innerHTML = `<div><strong>${rec.model_id ? escapeHtml(rec.model_id) : 'No safe candidate'}</strong><span>Compatibility baseline: ${escapeHtml(rec.runtime_id || '—')}</span><span>Optional backend to evaluate: ${escapeHtml(rec.alternative_runtime_id || 'none')}</span><span>${escapeHtml(rec.reason)}</span><span>Catalogue: ${escapeHtml(model.catalogue_version)}</span><span>Update check: ${model.update_check_due ? 'due' : 'checked within seven days'}</span><span>Downloads: explicit approval only</span></div>`;

  document.getElementById('runtime-catalogue').innerHTML = model.catalogue.runtimes.map(runtime => {
    const installed = runtime.install && runtime.install.status === 'installed';
    const devices = runtime.backend === 'cpu' ? 'device none (forced)' : ((runtime.devices || []).map(device => `${device.id}: ${device.name} · ${formatBytes(device.free_memory_bytes)} free`).join('; ') || 'no Vulkan device reported yet');
    return `<div class="fact-item" data-runtime-id="${escapeAttr(runtime.id)}"><div class="fact-meta"><code>${escapeHtml(runtime.id)}</code><span class="pill">${installed ? 'installed' : 'not installed'}</span></div><div class="fact-source">llama.cpp ${escapeHtml(runtime.version)} / ${escapeHtml(runtime.build)} · ${escapeHtml(runtime.backend)} · ${formatBytes(runtime.bytes)} · SHA ${escapeHtml(shortHash(runtime.sha256))}<br>Devices: ${escapeHtml(devices)}</div><div class="button-row"><button data-runtime-action="install" ${idle && !installed ? '' : 'disabled'}>Install verified runtime</button></div></div>`;
  }).join('');

  const configs = modelConfigurations(model);
  document.getElementById('model-catalogue').innerHTML = model.catalogue.models.map(item => {
    const install = item.install;
    const status = install ? install.status : 'not installed';
    const passing = install ? model.evaluations.filter(ev => ev.model_install_id === install.id && ev.overall_pass) : [];
    const canInstall = idle && (!install || status === 'failed' || status === 'retired');
    const canEval = idle && install && ['installed', 'validated', 'failed'].includes(status) && configs.length > 0;
    const canSelect = idle && status === 'validated' && passing.length > 0;
    const configOptions = configs.length
      ? `<select class="model-config" ${canEval ? '' : 'disabled'}>${configs.map(config => `<option value="${escapeAttr(`${config.runtimeId}|${config.deviceId}`)}">${escapeHtml(config.label)}</option>`).join('')}</select>`
      : '<span class="muted">Install a runtime; Vulkan also needs a discovered device.</span>';
    return `<div class="fact-item" data-model-id="${escapeAttr(item.id)}"><div class="fact-meta"><code>${escapeHtml(item.id)}</code><span class="pill ${escapeAttr(status)}">${escapeHtml(status)}</span></div><strong>${escapeHtml(item.display_name)}</strong><div class="fact-source">${escapeHtml(item.quantization)} · exact ${formatBytes(item.bytes)} · ${escapeHtml(item.license)} · revision ${escapeHtml(shortHash(item.source_revision))} · SHA ${escapeHtml(shortHash(item.sha256))}<br>Suitability: ${escapeHtml(item.suitability)}<br>${escapeHtml(item.notes)}</div><div class="button-row">${configOptions}<button data-model-action="install" ${canInstall ? '' : 'disabled'}>Download & verify</button><button data-model-action="evaluate" ${canEval ? '' : 'disabled'}>Evaluate selected config</button><button data-model-action="select" ${canSelect ? '' : 'disabled'}>Select fastest passing config</button></div></div>`;
  }).join('');

  document.getElementById('model-review-gate').innerHTML = selected && gate
    ? `<div><strong>${escapeHtml(selected)}</strong><span>Selected runtime: ${escapeHtml(model.selection.selected_runtime_install_id || '—')}</span><span>Selected device: ${escapeHtml(model.selection.selected_device_id || '—')}</span><span>Distinct approvals: ${gate.approved_distinct_resumes}/${gate.required_distinct_resumes}</span><span>Remaining: ${gate.remaining}</span><span>Status: ${gate.complete ? 'complete' : gate.invalidated ? `invalidated · ${escapeHtml(gate.invalidation_reason || '')}` : 'pending Phase 4 human review'}</span><span>Automatic tailoring: ${model.auto_tailoring_enabled ? 'enabled after gate' : 'disabled'}</span></div>`
    : '<p>No validated configuration has been selected. Phase 4 review cannot begin.</p>';

  document.getElementById('model-evaluations').innerHTML = model.evaluations.length
    ? model.evaluations.map(ev => `<div class="activity-item"><strong>${escapeHtml(ev.model_install_id)} · ${ev.overall_pass ? 'PASS' : 'FAIL'}</strong><span>${escapeHtml(ev.backend)}/${escapeHtml(ev.device_id)} · ctx ${escapeHtml(ev.context_tokens)} · ${(ev.elapsed_ms / 1000).toFixed(1)}s · ${ev.generation_tokens_per_second ? `${Number(ev.generation_tokens_per_second).toFixed(2)} tok/s` : 'speed unavailable'} · peak ${ev.peak_rss_bytes ? formatBytes(ev.peak_rss_bytes) : 'unknown'}</span><br><span>structured ${ev.structured_pass ? '✓' : '✗'} · factual ${ev.factual_pass ? '✓' : '✗'} · tailoring ${ev.tailoring_pass ? '✓' : '✗'} · resource ${ev.resource_pass ? '✓' : '✗'} · pressure ${escapeHtml(ev.pressure?.worst_pressure || 'unknown')}</span><br><time>${escapeHtml(ev.created_at)}</time></div>`).join('')
    : '<p>No local model evaluation has run yet.</p>';
}

function renderTailoring(tailoring, session, busy, resume, model) {
  const idle = session === 'idle' && !busy;
  const selected = Boolean(tailoring.selected_model_install_id);
  const canGenerate = idle && resume.onboarding_ready && selected;
  document.getElementById('save-jd').disabled = !idle;
  const gate = tailoring.review_gate;
  document.getElementById('tailoring-gate').innerHTML = selected && gate
    ? `<div><strong>${escapeHtml(tailoring.selected_model_install_id)}</strong><span>Human-approved distinct resumes: ${gate.approved_distinct_resumes}/${gate.required_distinct_resumes}</span><span>Remaining: ${gate.remaining}</span><span>Automatic local tailoring: ${tailoring.auto_tailoring_enabled ? 'enabled' : 'disabled'}</span><span>Job discovery: disabled until Phase 5</span><span>Employer submission: disabled</span></div>`
    : '<p>Select a validated local model/configuration before beginning the five-resume review gate.</p>';
  document.getElementById('enable-auto-tailoring').disabled = !idle || tailoring.auto_tailoring_enabled || !gate?.complete;

  document.getElementById('manual-jd-list').innerHTML = tailoring.manual_jds.length
    ? tailoring.manual_jds.map(jd => `<div class="fact-item" data-jd-id="${escapeAttr(jd.id)}"><div class="fact-meta"><code>${escapeHtml(jd.id)}</code><span class="pill">${jd.instruction_like ? 'instruction-like text detected' : 'untrusted data'}</span></div><strong>${jd.source_url ? escapeHtml(jd.source_url) : 'Pasted manual JD'}</strong><div class="fact-source">SHA ${escapeHtml(shortHash(jd.jd_sha256))} · ${jd.character_count} characters · stored locally<br>${escapeHtml(jd.preview)}</div><div class="button-row"><button data-jd-action="generate" ${canGenerate ? '' : 'disabled'}>Generate evidence-backed resume</button></div></div>`).join('')
    : '<p>No manual job descriptions saved yet.</p>';

  document.getElementById('tailoring-runs').innerHTML = tailoring.runs.length
    ? tailoring.runs.map(run => {
        const valid = Boolean(run.validation?.overall_pass);
        const canReview = idle && run.status === 'needs_review' && valid;
        const statusDetail = run.failure_message ? `<br><span class="error-text">${escapeHtml(run.failure_message)}</span>` : '';
        return `<div class="fact-item" data-run-id="${escapeAttr(run.id)}"><div class="fact-meta"><code>${escapeHtml(run.id)}</code><span class="pill ${escapeAttr(run.status)}">${escapeHtml(run.status)}</span></div><strong>${escapeHtml(run.jd_id)}</strong><div class="fact-source">Model ${escapeHtml(run.model_install_id)} · ${escapeHtml(run.runtime_install_id)}/${escapeHtml(run.device_id)} · fact revision ${run.fact_bank_revision}<br>Changes: ${(run.diff || []).length} · validation: ${valid ? 'PASS' : 'not passed'} · resume key ${escapeHtml(shortHash(run.resume_key))}${statusDetail}</div><div class="button-row"><button data-run-action="preview" ${run.pdf_relpath ? '' : 'disabled'}>Preview + evidence</button><button data-run-action="approve" ${canReview ? '' : 'disabled'}>Approve</button><button data-run-action="reject" ${canReview ? '' : 'disabled'}>Reject</button></div></div>`;
      }).join('')
    : '<p>No tailored resumes yet.</p>';

  if (inspectedRunId && !tailoring.runs.some(run => run.id === inspectedRunId)) closeTailoringInspector();
}

async function inspectTailoringRun(runId) {
  const run = latestState?.tailoring?.runs.find(item => item.id === runId);
  if (!run) return;
  inspectedRunId = runId;
  const inspector = document.getElementById('tailoring-inspector');
  inspector.classList.remove('hidden');
  document.getElementById('tailoring-inspector-meta').textContent = `${run.id} · ${run.status} · ${run.model_install_id} · fact revision ${run.fact_bank_revision}`;
  document.getElementById('tailoring-diff').innerHTML = (run.diff || []).length
    ? run.diff.map(item => `<div class="activity-item"><strong>${escapeHtml(item.field_id)}</strong><span><b>Before:</b> ${escapeHtml(item.before)}</span><br><span><b>After:</b> ${escapeHtml(item.after)}</span><br><span>Facts: ${escapeHtml((item.fact_ids || []).join(', '))} · JD keywords: ${escapeHtml((item.keywords || []).join(', ') || 'none')}</span></div>`).join('')
    : '<p>No validated wording diff.</p>';
  document.getElementById('tailoring-keywords').innerHTML = (run.keyword_mapping || []).length
    ? run.keyword_mapping.map(item => `<div class="activity-item"><strong>${escapeHtml(item.keyword)}</strong><span>${escapeHtml((item.fact_ids || []).join(', '))}</span></div>`).join('')
    : '<p>No keyword mapping.</p>';
  const validation = run.validation || {};
  document.getElementById('tailoring-validation').innerHTML = `<div><strong>${validation.overall_pass ? 'PASS' : 'NOT PASSED'}</strong><span>Pages: ${validation.page_count ?? '—'} / baseline ${validation.baseline_page_count ?? '—'}</span><span>Offline compile: ${validation.offline_compile ? 'yes' : 'no'}</span><span>Overflow: ${validation.overflow_detected ? 'detected' : 'none'}</span><span>Edited wording in PDF: ${validation.edited_fields_present_in_pdf ? 'yes' : 'no'}</span><span>${escapeHtml((validation.failures || []).join('; ') || 'No deterministic validation failures')}</span></div>`;
  const iframe = document.getElementById('tailored-pdf-preview');
  iframe.removeAttribute('src');
  if (run.pdf_relpath) iframe.src = await invokeRaw('tailored_pdf_data_uri', runId);
  inspector.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function closeTailoringInspector() {
  inspectedRunId = null;
  document.getElementById('tailoring-inspector').classList.add('hidden');
  document.getElementById('tailored-pdf-preview').removeAttribute('src');
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
document.getElementById('install-tectonic').addEventListener('click', async () => { if (!window.confirm('Download the pinned Tectonic 0.17.0 Windows x64 archive from its official GitHub release and verify its SHA-256?')) return; setBusy('Installing Tectonic…'); await invoke('install_tectonic'); toast('Tectonic installed and verified'); });
document.getElementById('compile-cached').addEventListener('click', async () => { setBusy('Compiling from cache…'); await invoke('compile_master_resume', false); toast('Baseline compiled from cached packages'); });
document.getElementById('compile-network').addEventListener('click', async () => { if (!window.confirm('Allow Tectonic to access the internet only for missing support packages during this baseline compile?')) return; setBusy('Compiling and populating package cache…'); await invoke('compile_master_resume', true); toast('Baseline compiled; rerun cached-only to verify offline readiness'); });
document.getElementById('confirm-template-map').addEventListener('click', async () => { await invoke('confirm_template_map'); toast('Template mapping confirmed'); });
document.getElementById('template-regions').addEventListener('change', async e => { const id = e.target.dataset.regionId; if (id) await invoke('set_template_region_editable', id, e.target.checked); });
document.getElementById('fact-list').addEventListener('click', async e => { const action = e.target.dataset.factAction; if (!action) return; const item = e.target.closest('.fact-item'); const factId = item.dataset.factId; if (action === 'save') { await invoke('revise_fact', factId, item.querySelector('.fact-value').value, item.querySelector('.fact-category').value); toast('New candidate fact version saved'); } else { await invoke('set_fact_status', factId, action); toast(`Fact marked ${action}`); } });
document.getElementById('fact-form').addEventListener('submit', async e => { e.preventDefault(); const payload = { source_document_id: document.getElementById('fact-source').value, category: document.getElementById('fact-category').value, locator: document.getElementById('fact-locator').value.trim(), value: document.getElementById('fact-value').value.trim() }; await invoke('create_fact', payload); document.getElementById('fact-locator').value = ''; document.getElementById('fact-value').value = ''; toast('Candidate fact added'); });
document.getElementById('refresh-hardware').addEventListener('click', async () => { await invoke('refresh_model_hardware'); toast('Hardware, resource budget, and runtime devices refreshed'); });
document.getElementById('check-model-updates').addEventListener('click', async () => { if (!window.confirm('Check GitHub and Hugging Face metadata for configured runtime/model revisions? This does not download software or model weights.')) return; await invoke('check_model_updates'); toast('Update metadata checked'); });
document.getElementById('runtime-catalogue').addEventListener('click', async e => { if (e.target.dataset.runtimeAction !== 'install') return; const item = e.target.closest('[data-runtime-id]'); const runtime = latestState.model.catalogue.runtimes.find(r => r.id === item.dataset.runtimeId); if (!runtime) return; if (!window.confirm(`Download ${runtime.id} (${formatBytes(runtime.bytes)}) from the pinned llama.cpp release and verify SHA-256 before installation?`)) return; await invoke('install_model_runtime', runtime.id); toast('Local runtime installed, verified, and device-probed'); });
document.getElementById('model-catalogue').addEventListener('click', async e => { const action = e.target.dataset.modelAction; if (!action) return; const item = e.target.closest('[data-model-id]'); const model = latestState.model.catalogue.models.find(m => m.id === item.dataset.modelId); if (!model) return; if (action === 'install') { if (!window.confirm(`Download ${model.display_name} (${formatBytes(model.bytes)}, ${model.license}) from pinned revision ${shortHash(model.source_revision)} and require its exact SHA-256 and byte size? No cloud inference or vision component is used.`)) return; await invoke('install_local_model', model.id); toast('Local model revision downloaded and checksum verified'); } else if (action === 'evaluate') { if (!model.install) return; const config = item.querySelector('.model-config')?.value || ''; const separator = config.indexOf('|'); if (separator < 1) return; const runtimeId = config.slice(0, separator); const deviceId = config.slice(separator + 1); await invoke('evaluate_local_model', model.install.id, runtimeId, deviceId); toast('Device-local model evaluation finished'); } else if (action === 'select') { if (!model.install) return; await invoke('select_model_for_phase4_review', model.install.id); toast('Fastest passing configuration selected; five-resume review gate remains pending'); } });
document.getElementById('jd-form').addEventListener('submit', async e => { e.preventDefault(); const text = document.getElementById('jd-text').value.trim(); if (!text) { toast('Paste a job description first'); return; } await invoke('import_manual_job_description', text, document.getElementById('jd-source-url').value.trim() || null); document.getElementById('jd-text').value = ''; document.getElementById('jd-source-url').value = ''; toast('Manual JD saved locally as untrusted data'); });
document.getElementById('manual-jd-list').addEventListener('click', async e => { if (e.target.dataset.jdAction !== 'generate') return; const jdId = e.target.closest('[data-jd-id]')?.dataset.jdId; if (!jdId) return; if (!window.confirm('Run the selected validated local model against this untrusted JD using approved facts only, then compile and validate the result locally?')) return; await invoke('generate_tailored_resume', jdId); toast('Local tailoring run finished; review deterministic evidence before approval'); });
document.getElementById('tailoring-runs').addEventListener('click', async e => { const action = e.target.dataset.runAction; if (!action) return; const runId = e.target.closest('[data-run-id]')?.dataset.runId; if (!runId) return; if (action === 'preview') { await inspectTailoringRun(runId); return; } if (action === 'approve') { if (!window.confirm('Approve this exact tailored resume as one distinct human review for the selected local model?')) return; await invoke('approve_tailored_resume', runId, null); toast('Tailored resume approved and persisted in the five-resume gate'); } else if (action === 'reject') { if (!window.confirm('Reject this tailored resume? It will not count toward the five-resume gate.')) return; await invoke('reject_tailored_resume', runId, null); toast('Tailored resume rejected'); } });
document.getElementById('enable-auto-tailoring').addEventListener('click', async () => { if (!window.confirm('Enable automatic local resume tailoring for this exact validated model/configuration? This does not enable job discovery or employer submission.')) return; await invoke('enable_automatic_tailoring', false); toast('Automatic local tailoring enabled; Phase 5 discovery is still disabled'); });
document.getElementById('close-tailoring-inspector').addEventListener('click', closeTailoringInspector);
document.getElementById('targeting-form').addEventListener('submit', async e => { e.preventDefault(); const save = document.getElementById('save-state'); save.textContent = 'Saving...'; try { await invoke('save_targeting', targetingFromForm()); save.textContent = 'Saved locally'; toast('Targeting saved'); } catch { save.textContent = 'Not saved'; } });

window.addEventListener('pywebviewready', async () => {
  await invoke('get_state');
  refreshTimer = setInterval(async () => {
    if (latestState && (latestState.session_state === 'running' || latestState.session_state === 'paused' || latestState.onboarding_busy)) {
      try { render(await window.pywebview.api.get_state()); } catch (_) { clearInterval(refreshTimer); }
    }
  }, 500);
});
