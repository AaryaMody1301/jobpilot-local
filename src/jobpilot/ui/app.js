const titles = { dashboard: 'Dashboard', jobs: 'Jobs', settings: 'Targeting', history: 'History', system: 'Local data' };
let latestState = null;
let refreshTimer = null;

function csv(value) { return value.split(',').map(v => v.trim()).filter(Boolean); }
function toast(message) { const el = document.getElementById('toast'); el.textContent = message; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 1800); }
function escapeHtml(value) { const div = document.createElement('div'); div.textContent = String(value ?? ''); return div.innerHTML; }

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
  document.getElementById('start-button').disabled = !(session === 'idle' || session === 'paused');
  document.getElementById('pause-button').disabled = session !== 'running';
  document.getElementById('stop-button').disabled = !(session === 'running' || session === 'paused');
  document.getElementById('reset-sample').disabled = session !== 'idle';

  const total = state.sample_work.length;
  document.getElementById('done-count').textContent = state.sample_counts.done || 0;
  document.getElementById('sample-total').textContent = `of ${total} local checks`;
  document.getElementById('recovery-count').textContent = (state.recovery.requeued_work || 0) + (state.recovery.crashed_sessions || 0);
  document.getElementById('data-root').textContent = state.data_root;

  const work = document.getElementById('sample-work');
  work.innerHTML = state.sample_work.map(item => `<div class="work-item"><span>${escapeHtml(item.label)}</span><span class="pill">${escapeHtml(item.state)}</span></div>`).join('');
  const activity = document.getElementById('activity');
  activity.innerHTML = state.activity.map(item => `<div class="activity-item"><strong>${escapeHtml(item.event_type)}</strong><span>${escapeHtml(item.message)}</span><br><time>${escapeHtml(item.created_at)}</time></div>`).join('');

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
    if (latestState && (latestState.session_state === 'running' || latestState.session_state === 'paused')) {
      try { render(await window.pywebview.api.get_state()); } catch (_) { clearInterval(refreshTimer); }
    }
  }, 500);
});
