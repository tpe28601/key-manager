(() => {
  'use strict';

  const $ = selector => document.querySelector(selector);

  function icon(name) {
    const span = document.createElement('span');
    span.className = 'icon';
    span.dataset.icon = name;
    if (window.IconifyLocal) {
      span.innerHTML = window.IconifyLocal.svgFor(name);
      span.dataset.renderedIcon = name;
    }
    return span;
  }

  function button(id, label, iconName, extraClass = '') {
    const el = document.createElement('button');
    el.id = id;
    el.type = 'button';
    el.className = `button ${extraClass}`.trim();
    el.append(icon(iconName), document.createTextNode(label));
    return el;
  }

  function installSshPathControls() {
    const page = $('#page-ssh');
    const table = page?.querySelector('.table-wrap');
    if (!page || !table || $('#ssh-local-path')) return;

    const panel = document.createElement('div');
    panel.className = 'path-setting';

    const label = document.createElement('div');
    label.className = 'path-setting-label';
    label.append(icon('tabler:folder-open'));
    const copy = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = '本機 Key 路徑';
    const hint = document.createElement('span');
    hint.textContent = 'SSH 掃描、建立、刪除與 Agent 都使用此資料夾';
    copy.append(title, hint);
    label.append(copy);

    const controls = document.createElement('div');
    controls.className = 'path-setting-controls';
    const input = document.createElement('input');
    input.id = 'ssh-local-path';
    input.readOnly = true;
    input.setAttribute('aria-label', 'SSH Local Key 路徑');
    controls.append(
      input,
      button('ssh-path-browse', '選擇資料夾', 'tabler:folder-open'),
      button('ssh-path-reset', '恢復預設', 'tabler:refresh', 'ghost'),
    );

    panel.append(label, controls);
    table.before(panel);

    $('#ssh-path-browse').addEventListener('click', selectDirectory);
    $('#ssh-path-reset').addEventListener('click', resetDirectory);
  }

  function bridge() {
    return window.pywebview?.api || null;
  }

  function notify(message, type = 'success') {
    const stack = $('#toasts');
    if (!stack) return;
    const item = document.createElement('div');
    item.className = `toast ${type}`;
    item.append(icon(type === 'error' ? 'tabler:alert-circle' : 'tabler:check'));
    const text = document.createElement('div');
    text.textContent = message;
    item.append(text);
    stack.append(item);
    window.setTimeout(() => item.remove(), type === 'error' ? 5200 : 3300);
  }

  async function refreshPath() {
    installSshPathControls();
    const api = bridge();
    if (!api) {
      $('#ssh-local-path').value = 'C:\\Users\\Mike\\.ssh';
      return;
    }
    try {
      const result = await api.get_ssh_directory();
      if (result?.ok) $('#ssh-local-path').value = result.ssh_dir || '';
    } catch (error) {
      notify(error?.message || String(error), 'error');
    }
  }

  async function selectDirectory() {
    const api = bridge();
    if (!api) {
      $('#ssh-local-path').value = 'D:\\Keys\\SSH';
      return;
    }
    try {
      const result = await api.select_ssh_directory();
      if (!result?.ok) return notify(result?.error || '選擇資料夾失敗', 'error');
      if (result.cancelled) return;
      $('#ssh-local-path').value = result.ssh_dir || '';
      notify('SSH Local Key 路徑已更新');
      $('#refresh-btn')?.click();
    } catch (error) {
      notify(error?.message || String(error), 'error');
    }
  }

  async function resetDirectory() {
    const api = bridge();
    if (!api) {
      $('#ssh-local-path').value = 'C:\\Users\\Mike\\.ssh';
      return;
    }
    try {
      const result = await api.reset_ssh_directory();
      if (!result?.ok) return notify(result?.error || '恢復預設失敗', 'error');
      $('#ssh-local-path').value = result.ssh_dir || '';
      notify('已恢復預設 SSH Key 路徑');
      $('#refresh-btn')?.click();
    } catch (error) {
      notify(error?.message || String(error), 'error');
    }
  }

  function applyTheme(theme) {
    const value = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.dataset.theme = value;
    const dark = value === 'dark';
    const text = $('#theme-text');
    const iconEl = $('#theme-btn .icon');
    if (text) text.textContent = dark ? '淺色模式' : '深色模式';
    if (iconEl) {
      iconEl.dataset.icon = dark ? 'tabler:sun' : 'tabler:moon';
      window.IconifyLocal?.renderIcons($('#theme-btn'));
    }
  }

  async function restoreTheme() {
    const api = bridge();
    if (!api?.get_theme) return;
    try {
      const result = await api.get_theme();
      if (result?.ok) applyTheme(result.theme);
    } catch (_) {}
  }

  async function persistCurrentTheme() {
    const api = bridge();
    if (!api?.set_theme) return;
    const value = document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
    try {
      const result = await api.set_theme(value);
      if (!result?.ok) notify(result?.error || '主題設定儲存失敗', 'error');
    } catch (error) {
      notify(error?.message || String(error), 'error');
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    installSshPathControls();
    $('#theme-btn')?.addEventListener('click', () => window.setTimeout(persistCurrentTheme, 0));
    window.setTimeout(refreshPath, 420);
  });
  window.addEventListener('pywebviewready', () => {
    void refreshPath();
    void restoreTheme();
  });
})();
