(() => {
  'use strict';

  const state = {
    bridge: null,
    mock: false,
    page: 'dashboard',
    sshKeys: [],
    gpgKeys: [],
    selectedSsh: '',
    selectedGpg: '',
    gitConfig: null,
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  const mockData = {
    app: { name: 'Key Manager', version: '1.0.2', version_label: '1.0.2', author: 'Mike Lin', system: 'Windows', home: 'C:\\Users\\Mike' },
    dashboard: { ok: true, ssh_count: 2, agent_status: '已載入 1 組 Key', gpg_count: 1, git_installed: true, git_name: 'Mike Lin', git_email: 'mike@example.com', signing_enabled: true, signing_key: '92FA301C58210000000000000000ABCD12345678' },
    ssh: { ok: true, agent_status: '已載入 1 組 Key', keys: [
      { name: 'id_rsa', algorithm: 'ssh-rsa', fingerprint: 'SHA256:sV8Y3sMZ5nJ0z8Q4qJX1uN2L7vO3xI4b', comment: 'mike@example.com', has_private_key: true, agent_loaded: true },
      { name: 'github_work', algorithm: 'ssh-ed25519', fingerprint: 'SHA256:b7Q9nV2pL4mA8xD1cF6sK3wR5tY0uH9e', comment: 'work@example.com', has_private_key: true, agent_loaded: false },
    ]},
    gpg: { ok: true, keys: [
      { fingerprint: '92FA301C58210000000000000000ABCD12345678', user_id: 'Mike Lin <mike@example.com>', name: 'Mike Lin', email: 'mike@example.com', algorithm: 'rsa4096', created_at: '2026-09-14T00:00:00+00:00', expires_at: '2028-09-14T00:00:00+00:00', has_secret_key: true },
    ]},
    agent: { ok: true, available: true, managed: true, status: '已載入 1 組 Key', identities: [{ fingerprint: 'SHA256:sV8Y3sMZ5nJ0z8Q4qJX1uN2L7vO3xI4b', comment: 'mike@example.com', algorithm: 'ssh-ed25519', local_name: 'id_rsa' }] },
    git: { ok: true, config: { name: 'Mike Lin', email: 'mike@example.com', signing_key: '92FA301C58210000000000000000ABCD12345678', commit_gpgsign: true, tag_gpgsign: true, gpg_format: 'openpgp', gpg_program: 'C:\\Program Files\\Git\\usr\\bin\\gpg.exe' } },
  };

  function icon(name) {
    const span = document.createElement('span');
    span.className = 'icon';
    span.dataset.icon = name;
    span.innerHTML = window.IconifyLocal.svgFor(name);
    span.dataset.renderedIcon = name;
    return span;
  }

  function actionButton(label, iconName, handler, { primary = false } = {}) {
    const btn = document.createElement('button');
    btn.className = `button small${primary ? ' primary' : ''}`;
    btn.type = 'button';
    btn.append(icon(iconName), document.createTextNode(label));
    btn.addEventListener('click', event => {
      event.stopPropagation();
      handler();
    });
    return btn;
  }

  function cell(text, className = '') {
    const td = document.createElement('td');
    td.textContent = text ?? '';
    if (className) td.className = className;
    return td;
  }

  function formatDate(value) {
    if (!value) return '不過期';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(date);
  }

  function shortFingerprint(value) {
    if (!value) return '-';
    return value.length > 22 ? `${value.slice(0, 10)}…${value.slice(-10)}` : value;
  }

  function setLoading(on) {
    $('.content-scroll').classList.toggle('loading', on);
    $('#refresh-btn').disabled = on;
  }

  // <dialog> opened with showModal() renders in the browser's top layer, above
  // every normal element regardless of z-index. Re-parent the toast stack into
  // the frontmost open dialog so toasts stay visible above its backdrop.
  function toastHost() {
    const dialogs = $$('dialog[open]');
    return dialogs.length ? dialogs[dialogs.length - 1] : document.body;
  }

  function toast(message, type = 'success', timeout = 3300) {
    const stack = $('#toasts');
    const host = toastHost();
    if (stack.parentElement !== host) host.append(stack);
    const item = document.createElement('div');
    item.className = `toast ${type}`;
    item.append(icon(type === 'error' ? 'tabler:alert-circle' : 'tabler:check'));
    const text = document.createElement('div');
    text.textContent = message;
    item.append(text);
    stack.append(item);
    window.setTimeout(() => item.remove(), timeout);
  }

  function showResult(result, successMessage = '') {
    if (!result || !result.ok) {
      toast(result?.error || '操作失敗', 'error', 5200);
      return false;
    }
    if (successMessage || result.message) toast(result.message || successMessage, 'success');
    return true;
  }

  async function api(method, ...args) {
    if (state.mock || !state.bridge) return mockApi(method, ...args);
    try {
      return await state.bridge[method](...args);
    } catch (error) {
      return { ok: false, error: error?.message || String(error) };
    }
  }

  async function mockApi(method, ...args) {
    await new Promise(resolve => setTimeout(resolve, 80));
    if (method === 'get_app_info') return mockData.app;
    if (method === 'dashboard') return mockData.dashboard;
    if (method === 'list_ssh_keys') return mockData.ssh;
    if (method === 'list_gpg_keys') return mockData.gpg;
    if (method === 'read_git_config') return mockData.git;
    if (method.startsWith('copy_')) return { ok: true, message: 'Preview：已模擬複製 Public Key' };
    if (method.startsWith('export_')) return { ok: true, path: 'C:\\Users\\Mike\\Desktop\\public-key.pub' };
    if (method === 'list_ssh_agent') return mockData.agent;
    if (method === 'start_ssh_agent') { mockData.agent.available = true; mockData.agent.managed = true; mockData.agent.status = mockData.agent.identities.length ? `已載入 ${mockData.agent.identities.length} 組 Key` : '已啟動但未載入 Key'; return { ok: true, message: 'Preview：已啟動 Agent' }; }
    if (method === 'add_ssh_key_to_agent') return { ok: true, message: 'Preview：已模擬加入 SSH Agent' };
    if (method === 'remove_ssh_agent_key') { mockData.agent.identities = mockData.agent.identities.filter(item => item.fingerprint !== args[0]); return { ok: true, message: 'Preview：已從 Agent 移除 Key' }; }
    if (method === 'clear_ssh_agent') { mockData.agent.identities = []; mockData.agent.status = '已啟動但未載入 Key'; return { ok: true, message: 'Preview：Agent 已清空' }; }
    if (method === 'stop_ssh_agent') { mockData.agent.available = false; mockData.agent.managed = false; mockData.agent.identities = []; mockData.agent.status = '未啟動'; return { ok: true, message: 'Preview：Agent 已停止' }; }
    if (method === 'create_ssh_key' || method === 'create_gpg_key') return { ok: true, message: 'Preview：建立成功' };
    if (method === 'delete_ssh_key' || method === 'delete_gpg_key') return { ok: true, message: 'Preview：刪除成功' };
    if (method === 'save_git_identity' || method === 'save_git_signing') return { ok: true, message: 'Preview：設定已儲存' };
    if (method === 'open_ssh_folder') return { ok: true };
    return { ok: false, error: `Preview API 未實作：${method} ${args.length}` };
  }

  function switchPage(page, refresh = true) {
    state.page = page;
    $$('.nav-item').forEach(btn => btn.classList.toggle('active', btn.dataset.page === page));
    $$('.page').forEach(section => section.classList.toggle('active', section.id === `page-${page}`));
    if (refresh) refreshCurrent();
  }

  async function loadAppInfo() {
    const info = await api('get_app_info');
    $('#footer-version').textContent = `v${info.version_label || info.version || '1.0 Preview'}`;
    $('#footer-author').textContent = info.author || 'Mike Lin';
    $('#environment').textContent = `環境：${info.system || 'Windows'}\n${info.home || ''}`;
  }

  async function loadDashboard() {
    const result = await api('dashboard');
    if (!result.ok) {
      ['dash-ssh', 'dash-gpg', 'dash-git', 'dash-signing'].forEach(id => document.getElementById(id).textContent = '讀取失敗');
      toast(result.error || '總覽讀取失敗', 'error');
      return;
    }
    $('#dash-ssh').textContent = `${result.ssh_count} 組公開金鑰\nAgent：${result.agent_status}`;
    $('#dash-gpg').textContent = `${result.gpg_count} 組 Secret Key\nGit Bash GPG`;
    $('#dash-git').textContent = result.git_installed ? `${result.git_name || '尚未設定'}\n${result.git_email || '尚未設定 email'}` : '找不到 Git for Windows';
    const signingPartial = !!result.commit_signing_enabled !== !!result.tag_signing_enabled;
    $('#dash-signing').textContent = result.signing_enabled
      ? `Commit + Tag 已啟用\n${shortFingerprint(result.signing_key)}`
      : signingPartial ? 'Commit / Tag 設定不一致' : '未啟用';
  }

  async function loadSsh() {
    const result = await api('list_ssh_keys');
    const tbody = $('#ssh-body');
    tbody.replaceChildren();
    state.sshKeys = result.keys || [];
    $('#ssh-status').textContent = result.ok ? `SSH Agent：${result.agent_status || '未知'} · ${state.sshKeys.length} 組 Public Key` : result.error || 'SSH 讀取失敗';
    $('#ssh-empty').classList.toggle('visible', state.sshKeys.length === 0);
    state.sshKeys.forEach(key => {
      const tr = document.createElement('tr');
      tr.className = 'key-row';
      tr.dataset.key = key.name;
      tr.classList.toggle('selected', state.selectedSsh === key.name);
      tr.addEventListener('click', () => {
        state.selectedSsh = key.name;
        $$('#ssh-body .key-row').forEach(row => row.classList.toggle('selected', row === tr));
      });
      tr.append(cell(key.name));
      tr.append(cell(key.algorithm));
      tr.append(cell(key.fingerprint, 'mono'));
      tr.append(cell(key.comment || '-', 'muted'));
      const actions = document.createElement('td');
      actions.className = 'right';
      const wrap = document.createElement('div');
      wrap.className = 'row-actions';
      const agentButton = actionButton(key.agent_loaded ? '已載入' : '加入 Agent', key.agent_loaded ? 'tabler:check' : 'tabler:key', () => addAgent(key.name));
      agentButton.disabled = !!key.agent_loaded;
      wrap.append(
        actionButton('複製', 'tabler:copy', () => copySsh(key.name)),
        actionButton('匯出', 'tabler:download', () => exportSsh(key.name)),
        agentButton,
        actionButton('刪除', 'tabler:trash', () => deleteSsh(key.name))
      );
      actions.append(wrap);
      tr.append(actions);
      tbody.append(tr);
    });
  }

  async function loadGpg() {
    const result = await api('list_gpg_keys');
    const tbody = $('#gpg-body');
    tbody.replaceChildren();
    state.gpgKeys = result.keys || [];
    $('#gpg-status').textContent = result.ok ? `Git Bash GPG · ${state.gpgKeys.length} 組 Secret Key` : result.error || 'GPG 讀取失敗';
    $('#gpg-empty').classList.toggle('visible', state.gpgKeys.length === 0);
    state.gpgKeys.forEach(key => {
      const tr = document.createElement('tr');
      tr.className = 'key-row';
      tr.dataset.key = key.fingerprint;
      tr.classList.toggle('selected', state.selectedGpg === key.fingerprint);
      tr.addEventListener('click', () => {
        state.selectedGpg = key.fingerprint;
        $$('#gpg-body .key-row').forEach(row => row.classList.toggle('selected', row === tr));
      });
      tr.append(cell(key.user_id || `${key.name} <${key.email}>`));
      tr.append(cell(key.algorithm));
      tr.append(cell(shortFingerprint(key.fingerprint), 'mono'));
      tr.append(cell(formatDate(key.expires_at), 'muted'));
      const actions = document.createElement('td');
      actions.className = 'right';
      const wrap = document.createElement('div');
      wrap.className = 'row-actions';
      wrap.append(
        actionButton('複製', 'tabler:copy', () => copyGpg(key.fingerprint)),
        actionButton('匯出', 'tabler:download', () => exportGpg(key.fingerprint)),
        actionButton('刪除', 'tabler:trash', () => deleteGpg(key.fingerprint, key.user_id || key.email || key.name))
      );
      actions.append(wrap);
      tr.append(actions);
      tbody.append(tr);
    });
  }

  async function loadGit() {
    const [configResult, keysResult] = await Promise.all([api('read_git_config'), api('list_gpg_keys')]);
    if (!configResult.ok) {
      $('#git-status').textContent = configResult.error || 'Git 設定讀取失敗';
      return;
    }
    state.gitConfig = configResult.config;
    state.gpgKeys = keysResult.keys || [];
    const cfg = state.gitConfig;
    $('#git-name').value = cfg.name || '';
    $('#git-email').value = cfg.email || '';
    $('#git-signing-enabled').checked = !!cfg.commit_gpgsign && !!cfg.tag_gpgsign;
    $('#git-format').value = cfg.gpg_format || 'openpgp';
    $('#git-program').value = cfg.gpg_program || 'C:\\Program Files\\Git\\usr\\bin\\gpg.exe';
    const select = $('#git-signing-key');
    select.replaceChildren();
    if (state.gpgKeys.length === 0) {
      const opt = document.createElement('option'); opt.value = ''; opt.textContent = '找不到可用的 GPG Key'; select.append(opt);
    } else {
      state.gpgKeys.forEach(key => {
        const opt = document.createElement('option');
        opt.value = key.fingerprint;
        opt.textContent = `${key.user_id || key.email || key.name} — …${key.fingerprint.slice(-16)}`;
        select.append(opt);
      });
    }
    if (cfg.signing_key && state.gpgKeys.some(key => key.fingerprint === cfg.signing_key)) select.value = cfg.signing_key;
    updateGitFingerprint();
    const signingMismatch = !!cfg.commit_gpgsign !== !!cfg.tag_gpgsign;
    $('#git-status').textContent = signingMismatch ? 'Commit / Tag 簽章設定目前不一致；重新套用可同步兩者' : '已載入 Git for Windows 全域設定；Commit + Tag 使用同一組 GPG Key';
  }

  async function refreshCurrent() {
    setLoading(true);
    try {
      if (state.page === 'dashboard') await loadDashboard();
      if (state.page === 'ssh') await loadSsh();
      if (state.page === 'gpg') await loadGpg();
      if (state.page === 'git') await loadGit();
    } finally {
      setLoading(false);
    }
  }

  async function copySsh(name) { showResult(await api('copy_ssh_public_key', name)); }
  async function exportSsh(name) {
    const result = await api('export_ssh_public_key', name);
    if (showResult(result) && result.path) toast(`已匯出至 ${result.path}`);
  }
  async function addAgent(name) { if (showResult(await api('add_ssh_key_to_agent', name))) await loadSsh(); }

  async function loadAgentManager() {
    const result = await api('list_ssh_agent');
    const body = $('#agent-body');
    body.replaceChildren();
    const identities = result.identities || [];
    const available = !!result.available;
    $('#agent-manager-status').textContent = result.ok ? `Agent：${result.status || (available ? '已啟動' : '未啟動')}` : result.error || 'Agent 狀態讀取失敗';
    $('#agent-empty').textContent = available ? 'Agent 目前沒有載入 Key' : 'Agent 尚未啟動';
    $('#agent-empty').classList.toggle('visible', identities.length === 0);
    $('#agent-start').hidden = available;
    $('#agent-clear').disabled = !available || identities.length === 0;
    $('#agent-stop').disabled = !available || !result.managed;
    identities.forEach(identity => {
      const tr = document.createElement('tr');
      tr.className = 'key-row';
      tr.append(cell(identity.local_name || identity.comment || 'Agent Key'));
      tr.append(cell(identity.algorithm || '-'));
      tr.append(cell(identity.fingerprint || '-', 'mono'));
      const actions = document.createElement('td');
      actions.className = 'right';
      const wrap = document.createElement('div');
      wrap.className = 'row-actions';
      wrap.append(actionButton('移除', 'tabler:trash', () => removeAgentIdentity(identity.fingerprint, identity.local_name || identity.comment || identity.fingerprint)));
      actions.append(wrap);
      tr.append(actions);
      body.append(tr);
    });
  }

  async function openAgentManager() {
    $('#agent-dialog').showModal();
    await loadAgentManager();
  }

  async function startAgent() {
    if (showResult(await api('start_ssh_agent'))) await Promise.all([loadAgentManager(), loadSsh()]);
  }

  async function removeAgentIdentity(fingerprint, label) {
    if (!window.confirm(`確定要從 SSH Agent 移除「${label}」？

硬碟上的 Key 檔案不會被刪除。`)) return;
    if (showResult(await api('remove_ssh_agent_key', fingerprint))) await Promise.all([loadAgentManager(), loadSsh()]);
  }

  async function clearAgent() {
    if (!window.confirm(`確定要清空 SSH Agent 內的所有 Key？

硬碟上的 Key 檔案不會被刪除。`)) return;
    if (showResult(await api('clear_ssh_agent'))) await Promise.all([loadAgentManager(), loadSsh()]);
  }

  async function stopAgent() {
    if (!window.confirm('確定要停止由 Key Manager 啟動的 SSH Agent？')) return;
    if (showResult(await api('stop_ssh_agent'))) await Promise.all([loadAgentManager(), loadSsh()]);
  }
  async function deleteSsh(name) {
    const key = state.sshKeys.find(item => item.name === name);
    const warning = key?.agent_loaded
      ? '\n\n⚠️ 此 Key 目前已載入 SSH Agent，刪除檔案不會自動從 Agent 移除，之後使用可能出現找不到檔案的錯誤。'
      : '';
    if (!window.confirm(`確定要刪除 SSH Key「${name}」？\n\n這會刪除 Private Key 與 .pub，且無法復原。${warning}`)) return;
    if (showResult(await api('delete_ssh_key', name))) await loadSsh();
  }
  async function copyGpg(fingerprint) { showResult(await api('copy_gpg_public_key', fingerprint)); }
  async function exportGpg(fingerprint) {
    const result = await api('export_gpg_public_key', fingerprint);
    if (showResult(result) && result.path) toast(`已匯出至 ${result.path}`);
  }
  async function deleteGpg(fingerprint, label) {
    const cfg = await api('read_git_config');
    const inUse = !!cfg.ok && cfg.config?.signing_key === fingerprint
      && (!!cfg.config?.commit_gpgsign || !!cfg.config?.tag_gpgsign);
    const warning = inUse
      ? '\n\n⚠️ 此 Key 目前是 Git Commit / Tag 簽章使用的 Signing Key，刪除後簽章設定會失效，之後 commit/tag 會簽章失敗。'
      : '';
    if (!window.confirm(`確定要刪除 GPG Key「${label}」？\n\nSecret Key 與 Public Key 都會刪除，且無法復原。${warning}`)) return;
    if (showResult(await api('delete_gpg_key', fingerprint))) {
      state.selectedGpg = '';
      await loadGpg();
    }
  }

  function updateGitFingerprint() { $('#git-fingerprint').value = $('#git-signing-key').value || ''; }

  async function saveGitIdentity() {
    const result = await api('save_git_identity', $('#git-name').value.trim(), $('#git-email').value.trim());
    if (showResult(result)) await loadGit();
  }

  async function saveGitSigning() {
    const result = await api('save_git_signing', $('#git-signing-key').value || '', $('#git-signing-enabled').checked);
    if (showResult(result)) await loadGit();
  }

  async function submitSsh(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    if (data.passphrase !== data.confirm) { toast('兩次 Passphrase 不一致', 'error'); return; }
    $('#ssh-submit').disabled = true;
    const result = await api('create_ssh_key', { filename: data.filename, comment: data.comment, algorithm: data.algorithm, passphrase: data.passphrase });
    $('#ssh-submit').disabled = false;
    if (showResult(result, 'SSH Key 建立完成')) { $('#ssh-dialog').close(); form.reset(); form.elements.filename.value = 'id_rsa'; await loadSsh(); }
  }

  async function submitGpg(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    $('#gpg-submit').disabled = true;
    const result = await api('create_gpg_key', { name: data.name, email: data.email, algorithm: data.algorithm, expire: data.expire });
    $('#gpg-submit').disabled = false;
    if (showResult(result, 'GPG Key 建立完成')) { $('#gpg-dialog').close(); form.reset(); await loadGpg(); }
  }

  function setTheme(theme) {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('key-manager-theme', theme); } catch (_) {}
    const dark = theme === 'dark';
    $('#theme-text').textContent = dark ? '淺色模式' : '深色模式';
    $('#theme-btn .icon').dataset.icon = dark ? 'tabler:sun' : 'tabler:moon';
    window.IconifyLocal.renderIcons($('#theme-btn'));
  }

  function bindEvents() {
    $$('.nav-item').forEach(btn => btn.addEventListener('click', () => switchPage(btn.dataset.page)));
    $('#refresh-btn').addEventListener('click', refreshCurrent);
    $('#theme-btn').addEventListener('click', () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'));
    $('#ssh-create-btn').addEventListener('click', () => $('#ssh-dialog').showModal());
    $('#agent-manage-btn').addEventListener('click', openAgentManager);
    $('#agent-cancel-x').addEventListener('click', () => $('#agent-dialog').close());
    $('#agent-close').addEventListener('click', () => $('#agent-dialog').close());
    $('#agent-start').addEventListener('click', startAgent);
    $('#agent-clear').addEventListener('click', clearAgent);
    $('#agent-stop').addEventListener('click', stopAgent);
    $('#gpg-create-btn').addEventListener('click', () => $('#gpg-dialog').showModal());
    $('#ssh-cancel').addEventListener('click', () => $('#ssh-dialog').close());
    $('#ssh-cancel-x').addEventListener('click', () => $('#ssh-dialog').close());
    $('#gpg-cancel').addEventListener('click', () => $('#gpg-dialog').close());
    $('#gpg-cancel-x').addEventListener('click', () => $('#gpg-dialog').close());
    $('#ssh-form').addEventListener('submit', submitSsh);
    $('#gpg-form').addEventListener('submit', submitGpg);
    $('#git-signing-key').addEventListener('change', updateGitFingerprint);
    $('#git-save-identity').addEventListener('click', saveGitIdentity);
    $('#git-save-signing').addEventListener('click', saveGitSigning);
    $$('[data-action="open-ssh-create"]').forEach(btn => btn.addEventListener('click', () => { switchPage('ssh', false); $('#ssh-dialog').showModal(); }));
    $$('[data-action="open-gpg-create"]').forEach(btn => btn.addEventListener('click', () => { switchPage('gpg', false); $('#gpg-dialog').showModal(); }));
    $$('[data-action="open-git"]').forEach(btn => btn.addEventListener('click', () => switchPage('git')));
  }

  async function bootRealBridge() {
    state.bridge = window.pywebview.api;
    state.mock = false;
    await loadAppInfo();
    await refreshCurrent();
  }

  async function loadMockData() {
    if (state.bridge) return;
    state.mock = true;
    await loadAppInfo();
    await refreshCurrent();
    toast('瀏覽器預覽模式：目前顯示範例資料', 'success', 2400);
  }

  function boot() {
    window.IconifyLocal.renderIcons();
    bindEvents();
    let theme = 'light';
    try { theme = localStorage.getItem('key-manager-theme') || 'light'; } catch (_) {}
    setTheme(theme);
    // pywebview's WebView2 bridge can take a while to come up on a cold start;
    // wait generously before assuming we're in a plain browser preview so the
    // real app never has to show fabricated key data.
    let fallbackTimer = window.setTimeout(loadMockData, 2500);
    window.addEventListener('pywebviewready', async () => {
      window.clearTimeout(fallbackTimer);
      await bootRealBridge();
    });
  }

  window.loadMockData = loadMockData;
  document.addEventListener('DOMContentLoaded', boot);
})();
