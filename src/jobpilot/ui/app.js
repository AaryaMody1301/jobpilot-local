const titles = { dashboard: 'Dashboard', resume: 'Resume & facts', model: 'Model & resources', tailoring: 'Tailor resume', jobs: 'Jobs', settings: 'Targeting', history: 'History', system: 'Local data' };
let latestState = null;
let refreshTimer = null;
let inspectedRunId = null;
let clientOnboardingBusy = null;
let activeView = 'dashboard';

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

async function invokeOnboarding(name, label, ...args) {
  if (clientOnboardingBusy) {
    toast(`Another onboarding operation is active: ${clientOnboardingBusy}`);
    return null;
  }
  clientOnboardingBusy = label;
  if (latestState) render(latestState);
  try {
    return await invoke(name, ...args);
  } finally {
    clientOnboardingBusy = null;
    if (latestState) render(latestState);
  }
}

function render(state) {
  latestState = state;
  const session = state.session_state;
  const badge = document.getElementById('session-badge');
  badge.textContent = session;
  badge.className = `status ${session}`;
  const busy = Boolean(state.onboarding_busy || clientOnboardingBusy);
  document.getElementById('start-button').disabled = busy || !(session === 'idle' || session === 'paused');
  document.getElementById('pause-button').disabled = session !== 'running';
  document.getElementById('stop-button').disabled = !(session === 'running' || session === 'paused');

  const resume = state.resume;
  document.getElementById('resume-ready').textContent = resume.onboarding_ready ? 'Ready' : 'Not ready';
  document.getElementById('resume-ready-detail').textContent = resume.onboarding_ready
    ? 'Offline baseline, mapping, and facts resolved'
    : 'Local private resume onboarding required';

  const model = state.model;
  const selected = model?.selection?.selected_model_install_id;
  const gate = model?.review_gate;
  document.getElementById('model-ready').textContent = model?.auto_tailoring_enabled ? 'Ready' : selected ? 'Selected for review' : 'Not selected';
  document.getElementById('model-ready-detail').textContent = model?.auto_tailoring_enabled
    ? 'Automatic local tailoring enabled after persisted review gate'
    : selected ? `${gate?.approved_distinct_resumes || 0}/5 distinct resume approvals · auto-tailoring disabled` : 'Auto-tailoring disabled · device evaluation required';

  const daily = state.orchestration?.daily || {};
  document.getElementById('confirmed-today').textContent = Number(daily.confirmed_real ?? state.confirmed_applications_today ?? 0);

  renderActiveView(state, session, busy);
}

function renderActiveView(state, session, busy) {
  if (activeView === 'dashboard') {
    document.getElementById('activity').innerHTML = state.activity.map(item => `<div class="activity-item"><strong>${escapeHtml(item.event_type)}</strong><span>${escapeHtml(item.message)}</span><br><time>${escapeHtml(item.created_at)}</time></div>`).join('');
    return;
  }
  if (activeView === 'resume') {
    renderResume(state.resume, session, busy);
    return;
  }
  if (activeView === 'model' && state.model) {
    renderModel(state.model, session, busy);
    return;
  }
  if (activeView === 'tailoring' && state.tailoring) {
    renderTailoring(state.tailoring, session, busy, state.resume, state.model);
    return;
  }
  if (activeView === 'jobs') {
    renderJobs(state, session, busy);
    return;
  }
  if (activeView === 'settings') {
    renderTargeting(state.targeting);
    return;
  }
  if (activeView === 'history') {
    renderOrchestration(state);
    return;
  }
  if (activeView === 'system') {
    document.getElementById('data-root').textContent = state.data_root;
    renderDistribution(state);
  }
}

function renderTargeting(t) {
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
  const hasEditableRegion = resume.regions.some(region => Number(region.editable) === 1);
  document.getElementById('import-master').disabled = !idle;
  document.getElementById('import-supporting').disabled = !idle;
  document.getElementById('install-tectonic').disabled = !idle || resume.tectonic.installed;
  document.getElementById('compile-cached').disabled = !idle || !master || !resume.tectonic.installed;
  document.getElementById('compile-network').disabled = !idle || !master || !resume.tectonic.installed;
  document.getElementById('confirm-template-map').disabled = !idle || !master || !resume.regions.length || !hasEditableRegion || resume.template_map_status === 'confirmed';

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
  document.getElementById('fact-bank-status').textContent = busy ? `Busy: ${clientOnboardingBusy || latestState.onboarding_busy}` : `Revision ${resume.fact_bank_revision}`;
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
    ? `<div><strong>${escapeHtml(selected)}</strong><span>Selected runtime: ${escapeHtml(model.selection.selected_runtime_install_id || '—')}</span><span>Selected device: ${escapeHtml(model.selection.selected_device_id || '—')}</span><span>Distinct approvals: ${gate.approved_distinct_resumes}/${gate.required_distinct_resumes}</span><span>Remaining: ${gate.remaining}</span><span>Status: ${gate.complete ? 'complete' : gate.invalidated ? `invalidated · ${escapeHtml(gate.invalidation_reason || '')}` : 'pending human review'}</span><span>Automatic tailoring: ${model.auto_tailoring_enabled ? 'enabled after gate' : 'disabled'}</span></div>`
    : '<p>No validated configuration has been selected. Human review cannot begin.</p>';

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
    ? `<div><strong>${escapeHtml(tailoring.selected_model_install_id)}</strong><span>Human-approved distinct resumes: ${gate.approved_distinct_resumes}/${gate.required_distinct_resumes}</span><span>Remaining: ${gate.remaining}</span><span>Automatic local tailoring: ${tailoring.auto_tailoring_enabled ? 'enabled' : 'disabled'}</span><span>Job discovery: ${tailoring.phase5_discovery_enabled ? 'enabled' : 'disabled'}</span><span>Employer submission: disabled</span></div>`
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
  document.getElementById('tailoring-validation').innerHTML = `<div><strong>${validation.overall_pass ? 'PASS' : 'NOT PASSED'}</strong><span>Pages: ${validation.page_count ?? '—'} / baseline ${validation.baseline_page_count ?? '—'}</span><span>Offline compile: ${validation.offline_compile ? 'yes' : 'no'}</span><span>Overflow: ${validation.overflow_detected ? 'detected' : 'none'}</span><span>Expected baseline + tailored content: ${validation.expected_content_tokens_present ? 'present' : 'missing'}</span><span>${escapeHtml((validation.failures || []).join('; ') || 'No deterministic validation failures')}</span></div>`;
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
  activeView = name;
  document.querySelectorAll('.view').forEach(el => el.classList.toggle('active', el.id === name));
  document.querySelectorAll('.nav-item').forEach(el => {
    const current = el.dataset.view === name;
    el.classList.toggle('active', current);
    if (current) el.setAttribute('aria-current', 'page');
    else el.removeAttribute('aria-current');
  });
  document.getElementById('page-title').textContent = titles[name];
  if (latestState) render(latestState);
}

document.getElementById('nav').addEventListener('click', e => { const name = e.target.dataset.view; if (name) showView(name); });
document.getElementById('start-button').addEventListener('click', () => invoke('start'));
document.getElementById('pause-button').addEventListener('click', () => invoke('pause'));
document.getElementById('stop-button').addEventListener('click', () => invoke('stop'));
document.getElementById('import-master').addEventListener('click', async () => { await invoke('choose_master_resume'); toast('Master resume import finished'); });
document.getElementById('import-supporting').addEventListener('click', async () => { await invoke('choose_supporting_document'); toast('Supporting source import finished'); });
document.getElementById('install-tectonic').addEventListener('click', async () => { if (!window.confirm('Download the pinned Tectonic 0.17.0 Windows x64 archive from its official GitHub release and verify its SHA-256?')) return; setBusy('Installing Tectonic…'); await invokeOnboarding('install_tectonic', 'Tectonic installation'); toast('Tectonic installed and verified'); });
document.getElementById('compile-cached').addEventListener('click', async () => { setBusy('Compiling from cache…'); await invokeOnboarding('compile_master_resume', 'resume baseline compilation', false); toast('Baseline compiled from cached packages'); });
document.getElementById('compile-network').addEventListener('click', async () => { if (!window.confirm('Allow Tectonic to access the internet only for missing support packages during this baseline compile?')) return; setBusy('Compiling and populating package cache…'); await invokeOnboarding('compile_master_resume', 'resume baseline compilation', true); toast('Baseline compiled; rerun cached-only to verify offline readiness'); });
document.getElementById('confirm-template-map').addEventListener('click', async () => { await invoke('confirm_template_map'); toast('Template mapping confirmed'); });
document.getElementById('template-regions').addEventListener('change', async e => { const id = e.target.dataset.regionId; if (id) await invoke('set_template_region_editable', id, e.target.checked); });
document.getElementById('fact-list').addEventListener('click', async e => { const action = e.target.dataset.factAction; if (!action) return; const item = e.target.closest('.fact-item'); const factId = item.dataset.factId; if (action === 'save') { await invoke('revise_fact', factId, item.querySelector('.fact-value').value, item.querySelector('.fact-category').value); toast('New candidate fact version saved'); } else { await invoke('set_fact_status', factId, action); toast(`Fact marked ${action}`); } });
document.getElementById('fact-form').addEventListener('submit', async e => { e.preventDefault(); const payload = { source_document_id: document.getElementById('fact-source').value, category: document.getElementById('fact-category').value, locator: document.getElementById('fact-locator').value.trim(), value: document.getElementById('fact-value').value.trim() }; await invoke('create_fact', payload); document.getElementById('fact-locator').value = ''; document.getElementById('fact-value').value = ''; toast('Candidate fact added'); });
document.getElementById('refresh-hardware').addEventListener('click', async () => { await invoke('refresh_model_hardware'); toast('Hardware, resource budget, and runtime devices refreshed'); });
document.getElementById('check-model-updates').addEventListener('click', async () => { if (!window.confirm('Check GitHub and Hugging Face metadata for configured runtime/model revisions? This does not download software or model weights.')) return; await invokeOnboarding('check_model_updates', 'weekly model catalogue update check'); toast('Update metadata checked'); });
document.getElementById('runtime-catalogue').addEventListener('click', async e => { if (e.target.dataset.runtimeAction !== 'install') return; const item = e.target.closest('[data-runtime-id]'); const runtime = latestState.model.catalogue.runtimes.find(r => r.id === item.dataset.runtimeId); if (!runtime) return; if (!window.confirm(`Download ${runtime.id} (${formatBytes(runtime.bytes)}) from the pinned llama.cpp release and verify SHA-256 before installation?`)) return; await invokeOnboarding('install_model_runtime', 'llama.cpp runtime installation', runtime.id); toast('Local runtime installed, verified, and device-probed'); });
document.getElementById('model-catalogue').addEventListener('click', async e => { const action = e.target.dataset.modelAction; if (!action) return; const item = e.target.closest('[data-model-id]'); const model = latestState.model.catalogue.models.find(m => m.id === item.dataset.modelId); if (!model) return; if (action === 'install') { if (!window.confirm(`Download ${model.display_name} (${formatBytes(model.bytes)}, ${model.license}) from pinned revision ${shortHash(model.source_revision)} and require its exact SHA-256 and byte size? No cloud inference or vision component is used.`)) return; await invokeOnboarding('install_local_model', 'local model installation', model.id); toast('Local model revision downloaded and checksum verified'); } else if (action === 'evaluate') { if (!model.install) return; const config = item.querySelector('.model-config')?.value || ''; const separator = config.indexOf('|'); if (separator < 1) return; const runtimeId = config.slice(0, separator); const deviceId = config.slice(separator + 1); await invokeOnboarding('evaluate_local_model', 'local model evaluation', model.install.id, runtimeId, deviceId); toast('Device-local model evaluation finished'); } else if (action === 'select') { if (!model.install) return; await invoke('select_model_for_phase4_review', model.install.id); toast('Fastest passing configuration selected; five-resume review gate remains pending'); } });
document.getElementById('jd-form').addEventListener('submit', async e => { e.preventDefault(); const text = document.getElementById('jd-text').value.trim(); if (!text) { toast('Paste a job description first'); return; } await invoke('import_manual_job_description', text, document.getElementById('jd-source-url').value.trim() || null); document.getElementById('jd-text').value = ''; document.getElementById('jd-source-url').value = ''; toast('Manual JD saved locally as untrusted data'); });
document.getElementById('manual-jd-list').addEventListener('click', async e => { if (e.target.dataset.jdAction !== 'generate') return; const jdId = e.target.closest('[data-jd-id]')?.dataset.jdId; if (!jdId) return; if (!window.confirm('Run the selected validated local model against this untrusted JD using approved facts only, then compile and validate the result locally?')) return; await invoke('generate_tailored_resume', jdId); toast('Local tailoring run finished; review deterministic evidence before approval'); });
document.getElementById('tailoring-runs').addEventListener('click', async e => { const action = e.target.dataset.runAction; if (!action) return; const runId = e.target.closest('[data-run-id]')?.dataset.runId; if (!runId) return; if (action === 'preview') { await inspectTailoringRun(runId); return; } if (action === 'approve') { if (!window.confirm('Approve this exact tailored resume as one distinct human review for the selected local model?')) return; await invoke('approve_tailored_resume', runId, null); toast('Tailored resume approved and persisted in the five-resume gate'); } else if (action === 'reject') { if (!window.confirm('Reject this tailored resume? It will not count toward the five-resume gate.')) return; await invoke('reject_tailored_resume', runId, null); toast('Tailored resume rejected'); } });
document.getElementById('enable-auto-tailoring').addEventListener('click', async () => { if (!window.confirm('Enable automatic local resume tailoring for this exact validated model/configuration? This does not enable job discovery or employer submission.')) return; await invoke('enable_automatic_tailoring', false); toast('Automatic local tailoring enabled for the validated local configuration'); });
document.getElementById('close-tailoring-inspector').addEventListener('click', closeTailoringInspector);
document.getElementById('targeting-form').addEventListener('submit', async e => { e.preventDefault(); const save = document.getElementById('save-state'); save.textContent = 'Saving...'; try { await invoke('save_targeting', targetingFromForm()); save.textContent = 'Saved locally'; toast('Targeting saved'); } catch { save.textContent = 'Not saved'; } });

window.addEventListener('pywebviewready', async () => {
  await invoke('get_state');
  refreshTimer = setInterval(async () => {
    if (latestState && (latestState.session_state === 'running' || latestState.session_state === 'paused' || latestState.onboarding_busy)) {
      try { render(await window.pywebview.api.get_state()); } catch (_) { clearInterval(refreshTimer); }
    }
  }, 1000);
});

// Jobs, application orchestration, backup, and measured-pilot UI are part of the single production shell.
const jobsView = document.getElementById('jobs');
  if (!jobsView || document.getElementById('job-discover')) return;

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

  function renderJobs(state, session, busy) {
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
      const missingRequired = job.required_requirements.filter(item => !job.matched_required.includes(item));
      const missingPreferred = job.preferred_requirements.filter(item => !job.matched_preferred.includes(item));
      const score = job.score_reasons || {};
      return `<div class="fact-item"><div class="fact-meta"><span class="pill ${escapeAttr(job.eligibility)}">${escapeHtml(job.eligibility)}</span><strong>${Number(job.score)}/100</strong></div><strong>${escapeHtml(job.title)}</strong><div class="fact-source">${escapeHtml(job.employer)} · ${escapeHtml(job.location)} · ${escapeHtml(job.workplace_type || 'workplace unknown')} · ${escapeHtml(job.employment_type || 'employment unknown')}<br>Source: ${escapeHtml(job.source_url)}</div>${reasons.length ? `<div class="fact-source">${reasons.map(escapeHtml).join('<br>')}</div>` : ''}<div class="fact-source">Evidence terms: ${job.supported_terms.length ? job.supported_terms.map(escapeHtml).join(', ') : 'none'}<br>Required evidence: ${job.matched_required.length}/${job.required_requirements.length} · Preferred: ${job.matched_preferred.length}/${job.preferred_requirements.length}<br>Ranking: role ${Number(score.role || 0)} · required evidence ${Number(score.required_evidence || 0)} · preferred evidence ${Number(score.preferred_evidence || 0)} · eligibility clarity ${Number(score.eligibility_clarity || 0)}</div>${missingRequired.length ? `<div class="fact-source"><strong>Missing required evidence</strong><br>${missingRequired.map(escapeHtml).join('<br>')}</div>` : ''}${missingPreferred.length ? `<div class="fact-source"><strong>Missing preferred evidence</strong><br>${missingPreferred.map(escapeHtml).join('<br>')}</div>` : ''}</div>`;
    }).join('') : '<p>No jobs imported yet. Run discovery or add a manual job.</p>';
  }

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


if (document.getElementById('orchestration-panel')) return;

  const history = document.getElementById('history');
  const section = document.createElement('div');
  section.id = 'orchestration-panel';
  section.innerHTML = `
    <div class="banner"><strong>Submission activation boundary.</strong> Prepared real-employer applications remain read-only. Live form inspection can recognize supported fields and blockers, and JobPilot does not write to an employer page until the measured pilot is explicitly activated and the application is individually armed.</div>
    <div class="grid two">
      <article class="card">
        <h2>Local-day objective</h2>
        <div id="orchestration-daily" class="detail-list"></div>
        <p class="muted">50 confirmed, well-matched real applications is a target, not a ceiling. Controlled fixtures never count toward it.</p>
      </article>
      <article class="card">
        <h2>Orchestration worker</h2>
        <div id="orchestration-worker" class="detail-list"></div>
        <p class="muted">Discovery and tailoring run only during an explicit session. Critical resource pressure pauses new tailoring at a safe boundary.</p>
      </article>
    </div>
    <article class="card section-card">
      <div class="card-heading"><div><h2>Attention lane</h2><p>Eligibility unknowns, first-five resume reviews, stale packages, blockers and pilot activation waits stay visible without blocking unrelated work.</p></div><span id="orchestration-attention-count" class="muted"></span></div>
      <div id="orchestration-attention" class="fact-list"></div>
    </article>
    <article class="card section-card">
      <div class="card-heading"><div><h2>Application history</h2><p>Discovery, eligibility, tailoring, package, controlled submission and terminal outcomes are persisted in the existing application journal.</p></div><span id="orchestration-counts" class="muted"></span></div>
      <div id="orchestration-history" class="fact-list"></div>
    </article>`;
  history.prepend(section);

  function identity(item) {
    if (item.employer || item.title) return `${item.employer || 'Unknown employer'} · ${item.title || 'Unknown role'}`;
    return item.job_identity || item.id;
  }

  function attentionAction(item) {
    if (item.attention_kind === 'eligibility_review') {
      return `<div class="form-row"><label>Review note<input data-orchestration-eligibility-note="${escapeAttr(item.id)}" maxlength="1000" placeholder="Record the evidence/decision" required></label><button data-orchestration-eligibility="approved" data-id="${escapeAttr(item.id)}" class="primary" disabled>Mark eligible</button><button data-orchestration-eligibility="rejected" data-id="${escapeAttr(item.id)}" disabled>Mark ineligible</button></div>`;
    }
    if (item.attention_kind === 'tailoring_prerequisite') {
      return `<button data-orchestration-retry-tailoring="${escapeAttr(item.id)}" class="primary">Retry tailoring</button>`;
    }
    if (item.attention_kind === 'pilot_activation_required' || item.attention_kind === 'live_form_blocked') {
      const live = item.live_form || {};
      const blockers = (live.blockers || []).length ? `<br>Live blockers: ${escapeHtml(live.blockers.join(', '))}` : '';
      return `<div class="fact-source">Read-only recognition: ${live.read_only ? (live.supported ? 'supported form shape' : 'unsupported/blocking form shape') : 'not checked'}${blockers}</div><button data-orchestration-inspect="${escapeAttr(item.id)}">Inspect live form read-only</button>`;
    }
    return '';
  }

  function renderOrchestration(state) {
    const orchestration = state.orchestration;
    if (!orchestration) return;
    const daily = orchestration.daily || {};
    document.getElementById('orchestration-daily').innerHTML = `<div><span>Local date</span><strong>${escapeHtml(daily.local_date || '')}</strong></div><div><span>Confirmed real</span><strong>${Number(daily.confirmed_real || 0)} / ${Number(daily.target_confirmed || 50)}</strong></div><div><span>Remaining to target</span><strong>${Number(daily.remaining_to_target || 0)}</strong></div><div><span>Controlled confirmations</span><strong>${Number(daily.confirmed_controlled || 0)} (excluded)</strong></div>`;

    const worker = orchestration.worker || {};
    document.getElementById('orchestration-worker').innerHTML = `<div><span>Status</span><strong>${escapeHtml(worker.status || (worker.alive ? 'Running' : 'Idle'))}</strong></div><div><span>Current application</span><strong>${escapeHtml(worker.current_application_id || 'None')}</strong></div><div><span>Immutable packages</span><strong>${Number(orchestration.packages || 0)}</strong></div>${worker.last_error ? `<div><span>Last worker error</span><strong class="error-text">${escapeHtml(worker.last_error)}</strong></div>` : ''}`;

    const counts = Object.entries(orchestration.counts || {}).sort().map(([key, value]) => `${key}: ${value}`).join(' · ');
    document.getElementById('orchestration-counts').textContent = counts || 'No orchestrated applications yet';
    document.getElementById('orchestration-attention-count').textContent = `${orchestration.attention.length} item${orchestration.attention.length === 1 ? '' : 's'}`;
    document.getElementById('orchestration-attention').innerHTML = orchestration.attention.length ? orchestration.attention.map(item => {
      const eligibility = item.eligibility || {};
      const reasons = [...(eligibility.hard_reasons || []), ...(eligibility.review_reasons || [])];
      return `<div class="fact-item"><div class="fact-meta"><span class="pill ${escapeAttr(item.state)}">${escapeHtml(item.state)}</span><strong>${escapeHtml(identity(item))}</strong></div><div class="fact-source">${escapeHtml(item.attention_kind.replaceAll('_', ' '))}${reasons.length ? `<br>${escapeHtml(reasons.join(' · '))}` : ''}${item.last_reason ? `<br>${escapeHtml(item.last_reason)}` : ''}</div>${attentionAction(item)}</div>`;
    }).join('') : '<p>No orchestration item currently needs attention.</p>';

    document.getElementById('orchestration-history').innerHTML = orchestration.history.length ? orchestration.history.map(item => {
      const packageHash = item.package_manifest_sha256 ? `<br>Package ${escapeHtml(item.package_manifest_sha256.slice(0, 16))}…` : '';
      const controlled = item.controlled_fixture ? ' · controlled fixture' : '';
      return `<div class="fact-item"><div class="fact-meta"><span class="pill ${escapeAttr(item.state)}">${escapeHtml(item.state)}</span><strong>${escapeHtml(identity(item))}</strong></div><div class="fact-source">${escapeHtml(item.provider || 'legacy')}${controlled}${item.location ? ` · ${escapeHtml(item.location)}` : ''}<br>${escapeHtml(item.last_reason || '')}${packageHash}</div></div>`;
    }).join('') : '<p>No application history yet.</p>';
  }

  document.getElementById('orchestration-attention').addEventListener('input', event => {
    const input = event.target.closest('[data-orchestration-eligibility-note]');
    if (!input) return;
    const row = input.closest('.form-row');
    const disabled = !input.value.trim();
    row?.querySelectorAll('[data-orchestration-eligibility]').forEach(button => { button.disabled = disabled; });
  });

  document.getElementById('orchestration-attention').addEventListener('click', event => {
    const eligibility = event.target.dataset.orchestrationEligibility;
    if (eligibility) {
      const id = event.target.dataset.id;
      const input = document.querySelector(`[data-orchestration-eligibility-note="${CSS.escape(id)}"]`);
      const note = input ? input.value.trim() : '';
      if (!note) {
        toast('Enter a review note before resolving eligibility.');
        input?.focus();
        return;
      }
      invoke('resolve_application_eligibility', id, eligibility === 'approved', note);
      return;
    }
    const retry = event.target.dataset.orchestrationRetryTailoring;
    if (retry) {
      invoke('retry_application_tailoring', retry);
      return;
    }
    const inspect = event.target.dataset.orchestrationInspect;
    if (inspect) invoke('inspect_prepared_application', inspect);
  });


if (document.getElementById('distribution-panel')) return;

  const system = document.getElementById('system');
  const section = document.createElement('div');
  section.id = 'distribution-panel';
  section.innerHTML = `
    <div class="banner"><strong>Real submissions are off by default on every launch.</strong> Activation does not queue anything. A prepared application must pass read-only recognition and then be armed individually before the existing single worker can submit it.</div>
    <div class="grid two">
      <article class="card">
        <h2>Windows distribution</h2>
        <div id="distribution-install" class="detail-list"></div>
        <p class="muted">The release bundle is a verified per-user Windows x64 onedir package. Setup/upgrade replaces program files only; private JobPilot data stays under the separate local data root.</p>
      </article>
      <article class="card">
        <h2>Portable backup</h2>
        <div id="distribution-backup" class="detail-list"></div>
        <div class="button-row"><button id="distribution-create-backup" class="primary">Create backup</button><button id="distribution-restore-backup">Restore backup</button></div>
        <p class="muted">Backups contain SQLite state, private source documents and application artifacts. Models, tools, browser/profile data, caches, runtime files and logs are machine-specific and are not transferred.</p>
      </article>
    </div>
    <article class="card section-card">
      <h2>Measured real-application pilot</h2>
      <div id="pilot-status" class="detail-list"></div>
      <div class="form-row">
        <label>Activation phrase<input id="pilot-confirmation" maxlength="80" autocomplete="off"></label>
        <button id="pilot-activate" class="primary">Activate for this launch</button>
        <button id="pilot-deactivate">Deactivate</button>
      </div>
      <p id="pilot-help" class="muted"></p>
      <p class="muted">Activation resets on restart. It never bypasses the five-resume automatic-tailoring gate, eligibility decisions, immutable-package freshness, exact-context application answers, provider blockers, or terminal UNCERTAIN handling.</p>
    </article>`;
  system.prepend(section);

  function pilotQueueButtons(state) {
    const distribution = state.distribution || {};
    const orchestration = state.orchestration || {};
    const attention = orchestration.attention || [];
    document.querySelectorAll('[data-orchestration-inspect]').forEach(button => {
      const id = button.dataset.orchestrationInspect;
      const item = attention.find(entry => entry.id === id);
      if (!item || item.state !== 'prepared') return;
      const live = item.live_form || {};
      const eligible = distribution.pilot_session_active && live.read_only && live.supported && !(live.blockers || []).length && Number(live.submit_controls || 0) === 1;
      const container = button.parentElement;
      if (!container) return;
      const existing = container.querySelector(`[data-pilot-status-queue="${CSS.escape(id)}"]`);
      if (eligible && !existing) {
        button.insertAdjacentHTML('afterend', `<button data-pilot-status-queue="${escapeAttr(id)}" class="primary">Arm one measured pilot submission</button>`);
      } else if (!eligible && existing) {
        existing.remove();
      }
    });
  }

  function renderDistribution(state) {
    const distribution = state.distribution;
    if (!distribution) return;
    const backup = distribution.backup || {};
    const pending = Boolean(backup.restore_pending);
    const active = Boolean(distribution.pilot_session_active);
    const phrase = distribution.pilot_confirmation_phrase || '';
    document.getElementById('distribution-install').innerHTML = `<div><span>App version</span><strong>${escapeHtml(distribution.app_version || '')}</strong></div><div><span>Target</span><strong>Windows 10/11 x64</strong></div><div><span>Data root</span><strong>Separate from installed program files</strong></div>`;
    document.getElementById('distribution-backup').innerHTML = `<div><span>Backup format</span><strong>v${Number(backup.format_version || 1)}</strong></div><div><span>Local backups</span><strong>${Number(backup.local_backups || 0)}</strong></div><div><span>Restore staged</span><strong>${pending ? 'Yes - restart required' : 'No'}</strong></div>${backup.latest_backup ? `<div><span>Latest backup</span><strong class="path">${escapeHtml(backup.latest_backup)}</strong></div>` : ''}${distribution.restore_applied_on_launch ? `<div><span>Restore applied on launch</span><strong>Yes</strong></div>` : ''}`;
    document.getElementById('pilot-status').innerHTML = `<div><span>Project authorization</span><strong>${distribution.pilot_authorized ? 'Recorded' : 'Not authorized'}</strong></div><div><span>This launch</span><strong>${active ? 'ACTIVE' : 'Inactive'}</strong></div><div><span>Real employer submission lane</span><strong>${distribution.real_employer_submission_enabled ? 'Enabled for individually armed applications' : 'Disabled'}</strong></div><div><span>Armed this launch</span><strong>${Number(distribution.pilot_armed_this_launch || 0)} / ${Number(distribution.pilot_arm_limit || 0)}</strong></div><div><span>Policy</span><strong>${escapeHtml(String(distribution.pilot_policy_revision || '').replace(/^phase9-/, ''))}</strong></div>`;
    const confirmation = document.getElementById('pilot-confirmation');
    confirmation.placeholder = phrase;
    document.getElementById('pilot-help').textContent = active ? 'Pilot is active for this launch. Inspect a prepared application in the Attention lane, then explicitly arm it.' : `To activate, type exactly: ${phrase}`;
    document.getElementById('distribution-create-backup').disabled = pending || state.session_state !== 'idle';
    document.getElementById('distribution-restore-backup').disabled = pending || state.session_state !== 'idle';
    confirmation.disabled = active || pending || state.session_state !== 'idle';
    document.getElementById('pilot-activate').disabled = active || pending || state.session_state !== 'idle' || confirmation.value.trim() !== phrase;
    document.getElementById('pilot-deactivate').disabled = !active || pending || state.session_state !== 'idle';
    pilotQueueButtons(state);
  }

  document.getElementById('distribution-create-backup').addEventListener('click', () => invoke('choose_local_backup'));
  document.getElementById('distribution-restore-backup').addEventListener('click', () => invoke('choose_local_restore'));
  document.getElementById('pilot-confirmation').addEventListener('input', event => {
    const distribution = latestState?.distribution || {};
    const pending = Boolean(distribution.backup?.restore_pending);
    const active = Boolean(distribution.pilot_session_active);
    document.getElementById('pilot-activate').disabled = active || pending || latestState?.session_state !== 'idle' || event.target.value.trim() !== (distribution.pilot_confirmation_phrase || '');
  });
  document.getElementById('pilot-activate').addEventListener('click', () => {
    const confirmation = document.getElementById('pilot-confirmation').value;
    const phrase = latestState?.distribution?.pilot_confirmation_phrase || '';
    if (confirmation.trim() !== phrase) return;
    invoke('activate_real_application_pilot', confirmation);
  });
  document.getElementById('pilot-deactivate').addEventListener('click', () => invoke('deactivate_real_application_pilot'));
  document.getElementById('orchestration-attention').addEventListener('click', event => {
    const id = event.target.dataset.pilotQueue;
    if (id) invoke('queue_prepared_pilot_application', id);
  });

