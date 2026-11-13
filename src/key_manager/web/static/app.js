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
    profiles: [],
    profileEditId: '',
    keyUsage: { ssh: {}, gpg: {}, notes: [] },
    usageLoaded: false,
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  const mockData = {
    app: { name: 'Key Manager', version: '1.2.0', version_label: '1.2.0', author: 'Mike Lin', system: 'Windows', home: 'C:\\Users\\Mike' },
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
    profiles: [
      {
        id: 'client-a', kind: 'managed', name: 'Client A', note: '公司案場', path: 'C:\\Users\\Mike\\AppData\\Local\\DevToolbox\\key-manager\\profiles\\client-a.gitconfig',
        folders: [{ folder: 'D:/Work/ClientA/', condition: 'gitdir/i:D:/Work/ClientA/', overridden_keys: [], position: 3 }],
        fields: { 'user.name': 'Alice Chen', 'user.email': 'alice@client-a.example.com', 'user.signingkey': null, 'commit.gpgsign': 'true', 'tag.gpgSign': null, 'core.sshCommand': 'ssh -i "D:/Keys/SSH/github_work" -o IdentitiesOnly=yes' },
        warnings: [], ssh_command_custom: false,
      },
      {
        id: 'ext-2f6b8c1a90', kind: 'external', name: 'personal-gitconfig', note: '', path: 'C:\\Users\\Mike\\.gitconfig-personal',
        folders: [{ folder: 'D:/Personal/SideProject/', condition: 'gitdir/i:D:/Personal/SideProject/', overridden_keys: ['user.email'], position: 1 }],
        fields: { 'user.name': 'Alice Personal', 'user.email': 'alice@personal.example.com', 'user.signingkey': null, 'commit.gpgsign': null, 'tag.gpgSign': null, 'core.sshCommand': null },
        warnings: ['external：這是使用者手寫 includeIf 指向的檔案，第一次編輯前請先確認', 'D:/Personal/SideProject/ 的 user.email 在全域檔中位於 includeIf 之後，會被蓋掉'], ssh_command_custom: false,
      },
      {
        id: 'cond-9a8b7c6d5e', kind: 'unsupported', name: '不支援的條件：onbranch:main', note: '', path: 'C:/x.gitconfig',
        folders: [{ folder: '', condition: 'onbranch:main', overridden_keys: [], position: 5 }],
        fields: {}, warnings: ['不支援的條件（唯讀，Key Manager 不會修改它）'], ssh_command_custom: false,
      },
    ],
    usage: {
      ssh: {
        id_rsa: [{ scope: 'global', label: '全域' }],
        github_work: [
          { scope: 'profile', label: '資料夾：D:/Work/ClientA/', profile: 'Client A', profile_id: 'client-a' },
          { scope: 'ssh-host', label: 'SSH Host：github（github.com）', host: 'github' },
        ],
      },
      gpg: { '92FA301C58210000000000000000ABCD12345678': [{ scope: 'global', label: '全域' }] },
      notes: [],
    },
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
    if (method === 'get_ssh_public_key_text') return { ok: true, filename: `${args[0]}.pub`, text: 'ssh-ed25519 AAAAPREVIEW preview@example.com\n' };
    if (method === 'get_gpg_public_key_text') return { ok: true, filename: 'gpg-public-key.asc', text: '-----BEGIN PGP PUBLIC KEY BLOCK-----\nPREVIEW\n-----END PGP PUBLIC KEY BLOCK-----\n' };
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
    // ---- 1.2 資料夾設定（Profiles）與使用位置：預覽模式的記憶體假資料 ----
    if (method === 'list_git_profiles') return { ok: true, profiles: mockData.profiles, global_path: 'C:\\Users\\Mike\\.gitconfig' };
    if (method === 'save_git_profile') {
      const payload = args[0] || {};
      const fields = payload.fields || {};
      const incoming = { 'user.name': null, 'user.email': null, 'user.signingkey': null, 'commit.gpgsign': null, 'tag.gpgSign': null, 'core.sshCommand': null };
      Object.keys(incoming).forEach(key => { if (fields[key] != null) incoming[key] = String(fields[key]); });
      if (fields.ssh_key) incoming['core.sshCommand'] = `ssh -i "D:/Keys/SSH/${fields.ssh_key}" -o IdentitiesOnly=yes`;
      else if (fields.ssh_command) incoming['core.sshCommand'] = String(fields.ssh_command);
      const id = payload.id || String(payload.name || 'profile').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
      let profile = mockData.profiles.find(item => item.id === id);
      if (!profile) { profile = { id, kind: 'managed', name: '', note: '', path: `C:\\Users\\Mike\\AppData\\Local\\DevToolbox\\key-manager\\profiles\\${id}.gitconfig`, folders: [], fields: { ...incoming }, warnings: [], ssh_command_custom: false }; mockData.profiles.push(profile); }
      profile.name = String(payload.name || '');
      profile.note = String(payload.note || '');
      profile.fields = { ...profile.fields, ...incoming };
      if (fields.ssh_command) profile.ssh_command_custom = true;
      if (!fields.ssh_key && !fields.ssh_command && fields['core.sshCommand'] == null && !profile.ssh_command_custom) profile.fields['core.sshCommand'] = null;
      profile.folders = (payload.folders || []).filter(Boolean).map(folder => ({ folder: String(folder).replace(/\\/g, '/').replace(/\/+$/, '') + '/', condition: `gitdir/i:${String(folder).replace(/\\/g, '/').replace(/\/+$/, '')}/`, overridden_keys: [], position: 0 }));
      return { ok: true, profile, message: `Preview：資料夾設定「${profile.name}」已儲存` };
    }
    if (method === 'delete_git_profile') {
      const target = mockData.profiles.find(item => item.id === args[0]);
      mockData.profiles = mockData.profiles.filter(item => item.id !== args[0]);
      return { ok: true, message: 'Preview：已移除資料夾設定', removed: (target?.folders || []).map(folder => folder.folder) };
    }
    if (method === 'fix_profile_order') return { ok: true, message: 'Preview：已將 includeIf 移到全域檔最後', fixed: [] };
    if (method === 'check_effective_git_config') {
      const folder = String(args[0] || '');
      const hit = mockData.profiles.find(profile => profile.kind !== 'unsupported'
        && profile.folders.some(item => folder.replace(/\\/g, '/').toLowerCase().startsWith(item.folder.toLowerCase())));
      const base = { ok: true, folder, rows: [
        { key: 'user.name', value: hit?.fields['user.name'] || 'Mike Lin', scope: hit ? 'local' : 'global', origin: hit ? hit.path : 'C:\\Users\\Mike\\.gitconfig' },
        { key: 'user.email', value: hit?.fields['user.email'] || 'mike@example.com', scope: hit ? 'local' : 'global', origin: hit ? hit.path : 'C:\\Users\\Mike\\.gitconfig' },
        { key: 'user.signingkey', value: hit?.fields['user.signingkey'] || '', scope: '', origin: '' },
        { key: 'commit.gpgsign', value: hit?.fields['commit.gpgsign'] || 'true', scope: 'global', origin: 'C:\\Users\\Mike\\.gitconfig' },
        { key: 'tag.gpgSign', value: hit?.fields['tag.gpgSign'] || 'true', scope: 'global', origin: 'C:\\Users\\Mike\\.gitconfig' },
        { key: 'core.sshCommand', value: hit?.fields['core.sshCommand'] || '', scope: '', origin: '' },
      ], note: '' };
      return base;
    }
    if (method === 'get_key_usage') return { ok: true, ...mockData.usage };
    if (method === 'open_backup_folder') return { ok: true, path: 'C:\\Users\\Mike\\AppData\\Local\\DevToolbox\\key-manager\\backups' };
    if (method === 'list_config_backups') return { ok: true, backups: [
      { name: '.gitconfig.20261113-093012', base: '.gitconfig', target: 'global', profile_id: '', profile_name: '', path: 'C:\\Users\\Mike\\.gitconfig', restorable: true, size: 812, modified: '2026-11-13 09:30:12' },
      { name: 'client-a.gitconfig.20261112-175540', base: 'client-a.gitconfig', target: 'profile', profile_id: 'client-a', profile_name: 'Client A', path: 'C:\\Users\\Mike\\AppData\\Local\\DevToolbox\\key-manager\\profiles\\client-a.gitconfig', restorable: true, size: 233, modified: '2026-11-12 17:55:40' },
      { name: 'old-notes.gitconfig.20261101-081203', base: 'old-notes.gitconfig', target: 'unknown', profile_id: '', profile_name: '', path: '', restorable: false, size: 96, modified: '2026-11-01 08:12:03' },
    ] };
    if (method === 'read_config_backup') return { ok: true, name: String(args[0] || ''), size: 78, truncated: false, text: '[user]\n\tname = Mike Lin\n\temail = mike@example.com\n[commit]\n\tgpgSign = true\n' };
    if (method === 'restore_config_backup') return { ok: true, message: `Preview：已還原 ${args[0]}（未實際寫入檔案）`, name: String(args[0] || ''), target: 'C:\\Users\\Mike\\.gitconfig', kind: 'global', size: 78 };
    if (method === 'select_folder') return { ok: true, path: 'D:/Work/ProjectA' };
    return { ok: false, error: `Preview API 未實作：${method} ${args.length}` };
  }

  function switchPage(page, refresh = true) {
    state.page = page;
    $$('.nav-list .tb-tab').forEach(btn => btn.classList.toggle('is-active', btn.dataset.page === page));
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
    const profileResult = await api('list_git_profiles');
    if (profileResult.ok) {
      const list = profileResult.profiles || [];
      const folderCount = list.reduce((sum, item) => sum + (item.folders || []).length, 0);
      const warningCount = list.reduce((sum, item) => sum + (item.warnings || []).length, 0);
      $('#dash-profiles').textContent = `${list.length} 個設定 / ${folderCount} 個資料夾\n${warningCount ? `⚠ ${warningCount} 個警告` : '無警告'}`;
    } else {
      $('#dash-profiles').textContent = '讀取失敗';
    }
  }

  async function loadSsh() {
    const [result] = await Promise.all([api('list_ssh_keys'), loadKeyUsage()]);
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
      tr.append(usageCell('ssh', key.name));
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
    const [result] = await Promise.all([api('list_gpg_keys'), loadKeyUsage()]);
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
      tr.append(usageCell('gpg', key.fingerprint));
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
    if (state.page === 'profiles') await loadGitProfiles();
    } finally {
      setLoading(false);
    }
  }

  async function copySsh(name) { showResult(await api('copy_ssh_public_key', name)); }
  // Web 模式沒有存檔對話框：取得 Public Key 文字後交給瀏覽器下載
  function downloadText(filename, text) {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function exportByDownload(method, arg) {
    const result = await api(method, arg);
    if (!showResult(result)) return;
    downloadText(result.filename, result.text);
    toast(`已下載 ${result.filename}（存到瀏覽器的下載資料夾）`);
  }
  async function exportSsh(name) {
    if (window.KM_WEB_MODE) return exportByDownload('get_ssh_public_key_text', name);
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
    await loadKeyUsage();
    const usage = usageSummaryText('ssh', name);
    const usageNote = usage ? `\n\n📍 目前的使用位置：${usage}\n刪除後這些設定會失效。` : '';
    if (!window.confirm(`確定要刪除 SSH Key「${name}」？\n\n這會刪除 Private Key 與 .pub，且無法復原。${warning}${usageNote}`)) return;
    if (showResult(await api('delete_ssh_key', name))) await loadSsh();
  }
  async function copyGpg(fingerprint) { showResult(await api('copy_gpg_public_key', fingerprint)); }
  async function exportGpg(fingerprint) {
    if (window.KM_WEB_MODE) return exportByDownload('get_gpg_public_key_text', fingerprint);
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
    await loadKeyUsage();
    const usage = usageSummaryText('gpg', fingerprint);
    const usageNote = usage && !inUse ? `\n\n📍 目前的使用位置：${usage}\n刪除後這些設定會失效。` : '';
    if (!window.confirm(`確定要刪除 GPG Key「${label}」？\n\nSecret Key 與 Public Key 都會刪除，且無法復原。${warning}${usageNote}`)) return;
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

  // ---------------- 資料夾設定（Profiles，1.2） ----------------

  function pickFolder(startPath = '') {
    if (window.KM_WEB_MODE && !state.mock && window.KmDirBrowser) {
      return new Promise(resolve => {
        window.KmDirBrowser.open(state.bridge || window.pywebview?.api, {
          startPath,
          title: '選擇資料夾',
          subtitle: '點資料夾進入，確認後加入目前的清單',
          onPick: path => resolve(path),
        });
      });
    }
    return api('select_folder', startPath).then(result => {
      if (!result?.ok) { toast(result?.error || '選擇資料夾失敗', 'error'); return null; }
      return result.cancelled ? null : (result.path || null);
    });
  }

  async function loadKeyUsage(force = false) {
    if (state.usageLoaded && !force) return state.keyUsage;
    const result = await api('get_key_usage');
    state.keyUsage = result.ok
      ? { ssh: result.ssh || {}, gpg: result.gpg || {}, notes: result.notes || [] }
      : { ssh: {}, gpg: {}, notes: [] };
    state.usageLoaded = true;
    return state.keyUsage;
  }

  function usageEntries(kind, key) {
    return (state.keyUsage[kind] || {})[key] || [];
  }

  function usageSummaryText(kind, key) {
    return usageEntries(kind, key).map(entry => entry.label).join('、');
  }

  function usageCell(kind, key) {
    const entries = usageEntries(kind, key);
    const td = document.createElement('td');
    if (!entries.length) { td.textContent = '—'; td.className = 'muted'; return td; }
    const wrap = document.createElement('div');
    wrap.className = 'usage-chips';
    entries.slice(0, 3).forEach(entry => {
      const chip = document.createElement('span');
      const variant = entry.scope === 'profile' ? 'profile' : entry.scope === 'global' ? 'global' : 'host';
      chip.className = `usage-chip usage-${variant}`;
      chip.textContent = entry.label;
      chip.title = entry.label;
      wrap.append(chip);
    });
    if (entries.length > 3) {
      const more = document.createElement('span');
      more.className = 'usage-chip usage-more';
      more.textContent = `+${entries.length - 3}`;
      more.title = entries.map(entry => entry.label).join('\n');
      wrap.append(more);
    }
    td.append(wrap);
    return td;
  }

  function sshKeyName(command) {
    const match = /-i\s+"([^"]+)"|-i\s+([^\s"]+)/i.exec(command || '');
    const raw = (match && (match[1] || match[2])) || '';
    return raw.replace(/\\/g, '/').split('/').pop() || '';
  }

  function kindChip(kind) {
    const chip = document.createElement('span');
    chip.className = `pf-kind pf-kind-${kind}`;
    chip.textContent = kind === 'managed' ? 'Key Manager' : kind === 'external' ? '外部檔案' : '唯讀';
    return chip;
  }

  function profileSummary(profile) {
    const fields = profile.fields || {};
    const items = [];
    if (fields['user.name']) items.push(`name：${fields['user.name']}`);
    if (fields['user.email']) items.push(`email：${fields['user.email']}`);
    if (fields['user.signingkey']) items.push(`signingkey：…${String(fields['user.signingkey']).slice(-16)}`);
    if (fields['commit.gpgsign']) items.push(`commit.gpgsign：${fields['commit.gpgsign']}`);
    if (fields['tag.gpgSign']) items.push(`tag.gpgSign：${fields['tag.gpgSign']}`);
    const ssh = fields['core.sshCommand'];
    if (ssh) items.push(profile.ssh_command_custom ? 'sshCommand：自訂指令' : `sshKey：${sshKeyName(ssh) || '未知'}`);
    return items;
  }

  function profileCard(profile) {
    const card = document.createElement('article');
    card.className = `profile-card pf-${profile.kind}`;
    const head = document.createElement('div');
    head.className = 'profile-card-head';
    const title = document.createElement('div');
    title.className = 'profile-card-title';
    const strong = document.createElement('strong');
    strong.textContent = profile.name;
    title.append(strong, kindChip(profile.kind));
    const actions = document.createElement('div');
    actions.className = 'row-actions';
    const readOnly = profile.kind === 'unsupported';
    const editBtn = actionButton('編輯', 'tabler:pencil', () => openProfileDialog(profile));
    const deleteBtn = actionButton('刪除', 'tabler:trash', () => deleteGitProfile(profile));
    if (readOnly) { editBtn.disabled = true; deleteBtn.disabled = true; }
    actions.append(editBtn, deleteBtn);
    if (profile.folders.some(folder => (folder.overridden_keys || []).length)) {
      actions.append(actionButton('修正順序', 'tabler:arrow-bar-to-down', () => fixGitProfileOrder(profile)));
    }
    head.append(title, actions);
    card.append(head);
    if (profile.note) {
      const note = document.createElement('div');
      note.className = 'profile-note muted';
      note.textContent = profile.note;
      card.append(note);
    }
    const folders = document.createElement('div');
    folders.className = 'profile-folders';
    profile.folders.forEach(folder => {
      const chip = document.createElement('span');
      chip.className = `pf-folder${(folder.overridden_keys || []).length ? ' pf-folder-override' : ''}`;
      chip.textContent = folder.folder || folder.condition;
      chip.title = (folder.overridden_keys || []).length
        ? `會被全域值蓋掉：${folder.overridden_keys.join('、')}`
        : folder.condition;
      folders.append(chip);
    });
    card.append(folders);
    const summary = profileSummary(profile);
    if (summary.length) {
      const summaryEl = document.createElement('div');
      summaryEl.className = 'profile-summary';
      summary.forEach(item => {
        const chip = document.createElement('span');
        chip.className = 'pf-field-chip';
        chip.textContent = item;
        summaryEl.append(chip);
      });
      card.append(summaryEl);
    }
    (profile.warnings || []).forEach(warning => {
      const line = document.createElement('div');
      line.className = 'pf-warning';
      const text = document.createElement('span');
      text.textContent = warning;
      line.append(icon('tabler:alert-triangle'), text);
      card.append(line);
    });
    return card;
  }

  function renderProfiles() {
    const list = $('#profile-list');
    list.replaceChildren(...state.profiles.map(profileCard));
    $('#profile-empty').classList.toggle('visible', state.profiles.length === 0);
  }

  async function loadGitProfiles() {
    const result = await api('list_git_profiles');
    if (!result.ok) {
      state.profiles = [];
      $('#profile-global-path').textContent = result.error || '資料夾設定讀取失敗';
      renderProfiles();
      return;
    }
    state.profiles = result.profiles || [];
    $('#profile-global-path').textContent = `全域檔案：${result.global_path || ''}`;
    renderProfiles();
  }

  function fillSelect(select, entries) {
    select.replaceChildren();
    entries.forEach(([value, label]) => {
      const opt = document.createElement('option');
      opt.value = value;
      opt.textContent = label;
      select.append(opt);
    });
  }

  function setInheritField(inputSel, checkSel, value) {
    const input = $(inputSel);
    const check = $(checkSel);
    check.checked = value == null;
    input.disabled = check.checked;
    input.value = value == null ? '' : value;
  }

  function addFolderRow(pathValue) {
    const list = $('#pf-folders');
    const li = document.createElement('li');
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'pf-folder-input';
    input.value = pathValue || '';
    input.placeholder = '例如 D:/Work/ClientA';
    input.spellcheck = false;
    const browse = actionButton('瀏覽', 'tabler:folder-open', async () => {
      const picked = await pickFolder(input.value.trim());
      if (picked) input.value = picked;
    });
    const remove = actionButton('移除', 'tabler:x', () => {
      if ($$('#pf-folders li').length <= 1) { input.value = ''; return; }
      li.remove();
    });
    li.append(input, browse, remove);
    list.append(li);
    window.IconifyLocal?.renderIcons(li);
  }

  async function openProfileDialog(profile) {
    state.profileEditId = profile ? profile.id : '';
    $('#profile-dialog-title').textContent = profile ? `編輯資料夾設定 — ${profile.name}` : '新增資料夾設定';
    $('#pf-name').value = profile ? profile.name : '';
    $('#pf-note').value = profile ? profile.note : '';

    const [gpgResult, sshResult] = await Promise.all([api('list_gpg_keys'), api('list_ssh_keys')]);
    const gpgKeys = gpgResult.keys || [];
    const sshKeys = sshResult.keys || [];
    fillSelect($('#pf-signing-key'), [
      ['', '沿用全域（未設定）'],
      ...gpgKeys.map(key => [key.fingerprint, `${key.user_id || key.email || key.name} — …${key.fingerprint.slice(-8)}`]),
      ['__custom', '自訂 Fingerprint…'],
    ]);
    fillSelect($('#pf-ssh-key'), [
      ['', '沿用全域（不定義 sshCommand）'],
      ...sshKeys.map(key => [key.name, `${key.name}（${key.algorithm}）`]),
      ['__custom', '自訂 sshCommand…'],
    ]);

    const fields = profile ? profile.fields || {} : {};
    setInheritField('#pf-user-name', '#pf-inherit-name', fields['user.name']);
    setInheritField('#pf-user-email', '#pf-inherit-email', fields['user.email']);

    const signing = fields['user.signingkey'] || '';
    if (!signing) $('#pf-signing-key').value = '';
    else if (gpgKeys.some(key => key.fingerprint === signing)) $('#pf-signing-key').value = signing;
    else { $('#pf-signing-key').value = '__custom'; $('#pf-signing-custom').value = signing; }
    $('#pf-signing-custom').hidden = $('#pf-signing-key').value !== '__custom';

    $('#pf-commit-gpgsign').value = fields['commit.gpgsign'] || '';
    $('#pf-tag-gpgsign').value = fields['tag.gpgSign'] || '';

    const ssh = fields['core.sshCommand'] || '';
    const matched = sshKeys.find(key => key.name.toLowerCase() === sshKeyName(ssh).toLowerCase());
    if (!ssh) $('#pf-ssh-key').value = '';
    else if (matched && !profile.ssh_command_custom) $('#pf-ssh-key').value = matched.name;
    else { $('#pf-ssh-key').value = '__custom'; $('#pf-ssh-custom').value = ssh; }
    $('#pf-ssh-custom').hidden = $('#pf-ssh-key').value !== '__custom';

    const banner = $('#pf-note-banner');
    if (profile && profile.kind === 'external') {
      $('#pf-note-banner-text').textContent = `這是你在 .gitconfig 手寫 includeIf 指向的檔案（${profile.path}）。儲存前會先備份，再直接編輯原檔案，不會搬移或改名。`;
      banner.hidden = false;
    } else if (profile && profile.ssh_command_custom) {
      $('#pf-note-banner-text').textContent = '目前的 core.sshCommand 不是 Key Manager 產存的格式；改選「沿用全域」不會清除它，除非選一把新的 SSH Key 或新指令。';
      banner.hidden = false;
    } else {
      banner.hidden = true;
    }

    const list = $('#pf-folders');
    list.replaceChildren();
    const folders = profile ? profile.folders.map(folder => folder.folder) : [];
    (folders.length ? folders : ['']).forEach(addFolderRow);
    $('#profile-dialog').showModal();
  }

  async function submitProfile(event) {
    event.preventDefault();
    const folders = $$('#pf-folders input').map(input => input.value.trim()).filter(Boolean);
    if (!folders.length) { toast('請至少加一個資料夾', 'error'); return; }
    const sshChoice = $('#pf-ssh-key').value;
    const fields = {
      'user.name': $('#pf-inherit-name').checked ? null : $('#pf-user-name').value.trim(),
      'user.email': $('#pf-inherit-email').checked ? null : $('#pf-user-email').value.trim(),
      'user.signingkey': $('#pf-signing-key').value === '__custom'
        ? $('#pf-signing-custom').value.trim().replace(/\s/g, '')
        : ($('#pf-signing-key').value || null),
      'commit.gpgsign': $('#pf-commit-gpgsign').value || null,
      'tag.gpgSign': $('#pf-tag-gpgsign').value || null,
    };
    if ($('#pf-signing-key').value === '__custom' && !fields['user.signingkey']) {
      toast('請貼上完整的 GPG Fingerprint，或改選其他 Signing Key', 'error');
      return;
    }
    if (sshChoice === '__custom') {
      const command = $('#pf-ssh-custom').value.trim();
      if (!command) { toast('請輸入自訂 sshCommand，或改選其他選項', 'error'); return; }
      fields.ssh_command = command;
    } else if (sshChoice) {
      fields.ssh_key = sshChoice;
    }
    const payload = { name: $('#pf-name').value.trim(), note: $('#pf-note').value.trim(), folders, fields };
    if (state.profileEditId) payload.id = state.profileEditId;
    $('#profile-submit').disabled = true;
    const result = await api('save_git_profile', payload);
    $('#profile-submit').disabled = false;
    if (!showResult(result)) return;
    $('#profile-dialog').close();
    state.usageLoaded = false;
    await loadGitProfiles();
  }

  async function deleteGitProfile(profile) {
    const folderText = profile.folders.map(folder => folder.folder || folder.condition).join('\n  ');
    const fileNote = profile.kind === 'managed'
      ? 'Profile 檔會移到 backups/ 備份，不會直接刪除。'
      : '只移除 includeIf 設定，外部檔案本身保留。';
    if (!window.confirm(`確定要移除資料夾設定「${profile.name}」？\n\n影響的資料夾：\n  ${folderText}\n\n${fileNote}\n全域檔的註解與其他設定不會被改動。`)) return;
    const result = await api('delete_git_profile', profile.id);
    if (showResult(result)) {
      state.usageLoaded = false;
      await loadGitProfiles();
    }
  }

  async function fixGitProfileOrder(profile) {
    const result = await api('fix_profile_order', profile.id);
    if (showResult(result)) await loadGitProfiles();
  }

  async function openBackupFolder() {
    const result = await api('open_backup_folder');
    if (!result.ok) { toast(result.error || '無法開啟備份資料夾', 'error'); return; }
    if (window.KM_WEB_MODE) toast(`備份資料夾：${result.path}`);
    else toast('已開啟備份資料夾');
  }

  // ---------------- 備份與還原（1.2.2） ----------------

  let backupSelected = null;

  function backupTargetLabel(entry) {
    if (entry.target === 'global') return '全域 .gitconfig';
    if (entry.target === 'profile') return `Profile：${entry.profile_name || entry.profile_id}`;
    return `未知目標（${entry.base}）`;
  }

  function backupSizeLabel(bytes) {
    const size = Number(bytes) || 0;
    if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${size} B`;
  }

  async function openBackupDialog() {
    backupSelected = null;
    $('#backup-restore').disabled = true;
    $('#backup-preview').textContent = '選擇左列的備份即可預覽內容';
    $('#backup-dialog').showModal();
    await loadBackups();
  }

  async function loadBackups() {
    const result = await api('list_config_backups');
    const list = $('#backup-list');
    const empty = $('#backup-empty');
    list.replaceChildren();
    if (!showResult(result)) {
      empty.textContent = '備份清單載入失敗，關閉後再開啟可重試';
      empty.classList.add('visible');
      return;
    }
    const backups = result.backups || [];
    empty.textContent = '還沒有備份；修改 Git 設定後會自動出現在這裡';
    empty.classList.toggle('visible', backups.length === 0);
    backups.forEach(entry => list.append(backupRow(entry)));
    if (backupSelected) {
      // keep the selection across refreshes (e.g. a restore added a new backup),
      // but always re-target the freshest data so labels/disabled match reality
      const stillThere = backups.find(item => item.name === backupSelected.name);
      if (stillThere) {
        backupSelected = stillThere;
        markBackupRow(stillThere);
        $('#backup-restore').disabled = !stillThere.restorable;
      } else {
        backupSelected = null;
        $('#backup-restore').disabled = true;
      }
    }
  }

  function backupRow(entry) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'backup-item';
    row.dataset.backupName = entry.name;
    const when = document.createElement('span');
    when.className = 'backup-when';
    when.textContent = entry.modified || '—';
    const what = document.createElement('span');
    what.className = 'backup-what';
    what.textContent = backupTargetLabel(entry);
    const size = document.createElement('span');
    size.className = 'backup-size';
    size.textContent = backupSizeLabel(entry.size);
    row.append(when, what, size);
    if (!entry.restorable) row.classList.add('is-foreign');
    row.addEventListener('click', () => selectBackup(entry));
    return row;
  }

  function markBackupRow(entry) {
    $$('.backup-item').forEach(item => item.classList.toggle('is-selected', item.dataset.backupName === entry.name));
  }

  async function selectBackup(entry) {
    backupSelected = entry;
    markBackupRow(entry);
    $('#backup-restore').disabled = !entry.restorable;
    const preview = $('#backup-preview');
    preview.textContent = '讀取中…';
    const result = await api('read_config_backup', entry.name);
    if (backupSelected !== entry) {
      // user switched rows (or the list refresh dropped it) - drop this preview
      if (!backupSelected) preview.textContent = '選擇左列的備份即可預覽內容';
      return;
    }
    if (!result?.ok) { preview.textContent = result?.error || '預覽載入失敗'; return; }
    preview.textContent = (result.text || '（空檔案）') + (result.truncated ? '\n…內容過長，預覽已截斷' : '');
  }

  async function restoreSelectedBackup() {
    const entry = backupSelected;
    if (!entry || !entry.restorable) return;
    if (!window.confirm(`要還原備份「${entry.name}」嗎？\n\n將覆蓋：${backupTargetLabel(entry)}\n  ${entry.path}\n\n目前檔案會先自動備份，反悔時可回到這裡還原那一份。`)) return;
    const button = $('#backup-restore');
    button.disabled = true; // no double firing while the restore runs
    let result;
    try {
      result = await api('restore_config_backup', entry.name);
    } finally {
      button.disabled = !backupSelected?.restorable;
    }
    if (showResult(result, `已還原 ${entry.name}`)) {
      await loadBackups();
      await loadGitProfiles();
    }
  }

  function scopeLabel(scope) {
    return { local: 'Repo（local）', global: '全域', system: '系統', worktree: 'Worktree', command: '指令列 -c' }[scope] || scope || '—';
  }

  function resetCheckDialog() {
    // open with a fresh slate: no stale note/table, compact width until results exist
    $('#check-note').hidden = true;
    $('#check-note-text').textContent = '';
    $('#check-result').hidden = true;
    $('#profile-check-dialog').classList.remove('has-result');
  }

  async function runEffectiveCheck() {
    const folder = $('#check-path').value.trim();
    if (!folder) { toast('請先輸入資料夾路徑', 'error'); return; }
    const result = await api('check_effective_git_config', folder);
    if (!showResult(result)) { $('#check-result').hidden = true; $('#profile-check-dialog').classList.remove('has-result'); return; }
    $('#check-note').hidden = !result.note;
    $('#check-note-text').textContent = result.note || '';
    const tbody = $('#check-body');
    tbody.replaceChildren();
    (result.rows || []).forEach(row => {
      const tr = document.createElement('tr');
      tr.append(cell(row.key, 'mono'));
      tr.append(cell(row.value || '（未設定）', row.value ? '' : 'muted'));
      tr.append(cell(scopeLabel(row.scope)));
      tr.append(cell(row.origin || '—', 'muted'));
      tbody.append(tr);
    });
    $('#check-result').hidden = false;
    $('#profile-check-dialog').classList.add('has-result');
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

  // 主題由 ui-kit 的 tb-theme.js 套用（light／dark／system）；這裡只負責按鈕與循環切換
  const THEME_ORDER = ['light', 'dark', 'system'];
  const THEME_LABEL = { light: '淺色', dark: '深色', system: '跟隨系統' };
  const THEME_ICON = { light: 'tabler:sun', dark: 'tabler:moon', system: 'tabler:device-desktop' };
  function currentThemeMode() {
    return window.TbTheme ? window.TbTheme.get().mode : (document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light');
  }
  function paintThemeButton() {
    const mode = currentThemeMode();
    $('#theme-text').textContent = THEME_LABEL[mode] || mode;
    $('#theme-btn .icon').dataset.icon = THEME_ICON[mode] || 'tabler:sun';
    window.IconifyLocal.renderIcons($('#theme-btn'));
  }
  function setTheme(mode) {
    if (window.TbTheme) window.TbTheme.set(mode);
    else document.documentElement.dataset.theme = mode === 'dark' ? 'dark' : 'light';
    paintThemeButton();
  }

  function bindEvents() {
    $$('.nav-list .tb-tab').forEach(btn => btn.addEventListener('click', () => switchPage(btn.dataset.page)));
    $('#refresh-btn').addEventListener('click', refreshCurrent);
    $('#theme-btn').addEventListener('click', () => setTheme(THEME_ORDER[(THEME_ORDER.indexOf(currentThemeMode()) + 1) % THEME_ORDER.length]));
    document.addEventListener('tb-theme-change', paintThemeButton);
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
    $('#profile-add-btn').addEventListener('click', () => openProfileDialog(null));
    $('#profile-check-btn').addEventListener('click', () => { resetCheckDialog(); $('#profile-check-dialog').showModal(); });
    $('#profile-backup-btn').addEventListener('click', openBackupDialog);
    $('#backup-open-folder').addEventListener('click', openBackupFolder);
    $('#backup-restore').addEventListener('click', restoreSelectedBackup);
    $('#backup-cancel-x').addEventListener('click', () => $('#backup-dialog').close());
    $('#backup-close').addEventListener('click', () => $('#backup-dialog').close());
    $('#profile-cancel').addEventListener('click', () => $('#profile-dialog').close());
    $('#profile-cancel-x').addEventListener('click', () => $('#profile-dialog').close());
    $('#profile-form').addEventListener('submit', submitProfile);
    $('#pf-add-folder').addEventListener('click', () => addFolderRow(''));
    $('#pf-inherit-name').addEventListener('change', () => { $('#pf-user-name').disabled = $('#pf-inherit-name').checked; });
    $('#pf-inherit-email').addEventListener('change', () => { $('#pf-user-email').disabled = $('#pf-inherit-email').checked; });
    $('#pf-signing-key').addEventListener('change', () => { $('#pf-signing-custom').hidden = $('#pf-signing-key').value !== '__custom'; });
    $('#pf-ssh-key').addEventListener('change', () => { $('#pf-ssh-custom').hidden = $('#pf-ssh-key').value !== '__custom'; });
    $('#check-cancel-x').addEventListener('click', () => $('#profile-check-dialog').close());
    $('#check-close').addEventListener('click', () => $('#profile-check-dialog').close());
    $('#check-run').addEventListener('click', runEffectiveCheck);
    $('#check-browse').addEventListener('click', async () => {
      const picked = await pickFolder($('#check-path').value.trim());
      if (picked) $('#check-path').value = picked;
    });
    $('#check-path').addEventListener('keydown', event => {
      if (event.key === 'Enter') { event.preventDefault(); runEffectiveCheck(); }
    });
    $$('[data-action="open-ssh-create"]').forEach(btn => btn.addEventListener('click', () => { switchPage('ssh', false); $('#ssh-dialog').showModal(); }));
    $$('[data-action="open-gpg-create"]').forEach(btn => btn.addEventListener('click', () => { switchPage('gpg', false); $('#gpg-dialog').showModal(); }));
    $$('[data-action="open-git"]').forEach(btn => btn.addEventListener('click', () => switchPage('git')));
    $$('[data-action="open-profiles"]').forEach(btn => btn.addEventListener('click', () => switchPage('profiles')));
    $('#dash-profiles-card').addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); switchPage('profiles'); }
    });
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
    paintThemeButton();
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
