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
    app: { name: 'Key Manager', version: '1.0.0', version_label: '1.0.0', author: 'Mike Lin', system: 'Windows', home: 'C:\\Users\\Mike' },
    dashboard: { ok: true, ssh_count: 2, agent_status: 'å·²è¼‰å…¥ 1 çµ„ Key', gpg_count: 1, git_installed: true, git_name: 'Mike Lin', git_email: 'mike@example.com', signing_enabled: true, signing_key: '92FA301C58210000000000000000ABCD12345678' },
    ssh: { ok: true, agent_status: 'å·²è¼‰å…¥ 1 çµ„ Key', keys: [
      { name: 'id_rsa', algorithm: 'ssh-rsa', fingerprint: 'SHA256:sV8Y3sMZ5nJ0z8Q4qJX1uN2L7vO3xI4b', comment: 'mike@example.com', has_private_key: true, agent_loaded: true },
      { name: 'github_work', algorithm: 'ssh-ed25519', fingerprint: 'SHA256:b7Q9nV2pL4mA8xD1cF6sK3wR5tY0uH9e', comment: 'work@example.com', has_private_key: true, agent_loaded: false },
    ]},
    gpg: { ok: true, keys: [
      { fingerprint: '92FA301C58210000000000000000ABCD12345678', user_id: 'Mike Lin <mike@example.com>', name: 'Mike Lin', email: 'mike@example.com', algorithm: 'rsa4096', created_at: '2026-09-14T00:00:00+00:00', expires_at: '2028-09-14T00:00:00+00:00', has_secret_key: true },
    ]},
    agent: { ok: true, available: true, managed: true, status: 'å·²è¼‰å…¥ 1 çµ„ Key', identities: [{ fingerprint: 'SHA256:sV8Y3sMZ5nJ0z8Q4qJX1uN2L7vO3xI4b', comment: 'mike@example.com', algorithm: 'ssh-ed25519', local_name: 'id_rsa' }] },
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
    if (!value) return 'ä¸éŽæœŸ';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(date);
  }

  function shortFingerprint(value) {
    if (!value) return '-';
    return value.length > 22 ? `${value.slice(0, 10)}â€¦${value.slice(-10)}` : value;
  }

  function setLoading(on) {
    $('.content-scroll').classList.toggle('loading', on);
    $('#refresh-btn').disabled = on;
  }

  function toast(message, type = 'success', timeout = 3300) {
    const item = document.createElement('div');
    item.className = `toast ${type}`;
    item.append(icon(type === 'error' ? 'tabler:alert-circle' : 'tabler:check'));
    const text = document.createElement('div');
    text.textContent = message;
    item.append(text);
    $('#toasts').append(item);
    window.setTimeout(() => item.remove(), timeout);
  }

  function showResult(result, successMessage = '') {
    if (!result || !result.ok) {
      toast(result?.error || 'æ“ä½œå¤±æ•—', 'error', 5200);
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
    if (method.startsWith('copy_')) return { ok: true, message: 'Previewï¼šå·²æ¨¡æ“¬è¤‡è£½ Public Key' };
    if (method.startsWith('export_')) return { ok: true, path: 'C:\\Users\\Mike\\Desktop\\public-key.pub' };
    if (method === 'list_ssh_agent') return mockData.agent;
    if (method === 'start_ssh_agent') { mockData.agent.available = true; mockData.agent.managed = true; mockData.agent.status = mockData.agent.identities.length ? `å·²è¼‰å…¥ ${mockData.agent.identities.length} çµ„ Key` : 'å·²å•Ÿå‹•ä½†æœªè¼‰å…¥ Key'; return { ok: true, message: 'Previewï¼šå·²å•Ÿå‹• Agent' }; }
    if (method === 'add_ssh_key_to_agent') return { ok: true, message: 'Previewï¼šå·²æ¨¡æ“¬åŠ å…¥ SSH Agent' };
    if (method === 'remove_ssh_agent_key') { mockData.agent.identities = mockData.agent.identities.filter(item => item.fingerprint !== args[0]); return { ok: true, message: 'Previewï¼šå·²å¾ž Agent ç§»é™¤ Key' }; }
    if (method === 'clear_ssh_agent') { mockData.agent.identities = []; mockData.agent.status = 'å·²å•Ÿå‹•ä½†æœªè¼‰å…¥ Key'; return { ok: true, message: 'Previewï¼šAgent å·²æ¸…ç©º' }; }
    if (method === 'stop_ssh_agent') { mockData.agent.available = false; mockData.agent.managed = false; mockData.agent.identities = []; mockData.agent.status = 'æœªå•Ÿå‹•'; return { ok: true, message: 'Previewï¼šAgent å·²åœæ­¢' }; }
    if (method === 'create_ssh_key' || method === 'create_gpg_key') return { ok: true, message: 'Previewï¼šå»ºç«‹æˆåŠŸ' };
    if (method === 'delete_ssh_key' || method === 'delete_gpg_key') return { ok: true, message: 'Previewï¼šåˆªé™¤æˆåŠŸ' };
    if (method === 'save_git_identity' || method === 'save_git_signing') return { ok: true, message: 'Previewï¼šè¨­å®šå·²å„²å­˜' };
    if (method === 'open_ssh_folder') return { ok: true };
    return { ok: false, error: `Preview API æœªå¯¦ä½œï¼š${method} ${args.length}` };
  }

  function switchPage(page, refresh = true) {
    state.page = page;
    $$('.nav-item').forEach(btn => btn.classList.toggle('active', btn.dataset.page === page));
    $$('.page').forEach(section => section.classList.toggle('active', section.id === `page-${page}`));
    if (refresh) refreshCurrent();
  }

  async function loadAppInfo() {
    const info = await api('get_app_info');
    $('#footer-version').textContent = `v${info.version_label || info.version || '1.0.0'}`;
    $('#footer-author').textContent = info.author || 'Mike Lin';
    $('#environment').textContent = `ç’°å¢ƒï¼š${info.system || 'Windows'}\n${info.home || ''}`;
  }

  async function loadDashboard() {
    const result = await api('dashboard');
    if (!result.ok) {
      ['dash-ssh', 'dash-gpg', 'dash-git', 'dash-signing'].forEach(id => document.getElementById(id).textContent = 'è®€å–å¤±æ•—');
      return;
    }
    $('#dash-ssh').textContent = `${result.ssh_count} çµ„ Key\n${result.agent_status}`;
    $('#dash-gpg').textContent = `${result.gpg_count} çµ„ Secret Key`;
    $('#dash-git').textContent = result.git_installed ? `${result.git_name || 'æ‰ßW‰Ü™\Ý[™Ú]Ù[XZ[	ËIßXˆ	ù§*¹k¢z(çHÚ]›ÜˆÚ[™ÝÜÉÎÂˆ	
	ÈÙ\Ú\ÚYÛš[™ÉÊK^ÛÛ[H™\Ý[œÚYÛš[™×Ù[˜X›YÈ9mì¹egùå*‰ÜÚÜš[™Ù\œš[
™\Ý[œÚYÛš[™×ÚÙ^J_Xˆ	ù§*¹egùå*	ÎÂˆB‚ˆ\Þ[˜È[˜Ý[ÛˆØYÜÚ

HÂˆÛÛœÝ™\Ý[H]ØZ]\J	Û\ÝÜÜÚÚÙ^\ÉÊNÂˆYˆ
\™\Ý[›ÚÊHÈÚÝÔ™\Ý[
™\Ý[
NÈ™]\›ŽÈBˆÝ]KœÜÚÙ^\ÈH™\Ý[šÙ^\È×NÂˆ	
	ÈÜÜÚ\Ý]\ÉÊK^ÛÛ[H™\Ý[˜YÙ[ÜÝ]\È	ù§*¹egùbåIÎÂˆ™[™\”ÔÒ

NÂˆB‚ˆ[˜Ý[Ûˆ™[™\”ÔÒ

HÂˆÛÛœÝ›ÙHH	
	ÈÜÜÚX›ÙIÊNÂˆ›ÙKš[›™\’SH	ÉÎÂˆ	
	ÈÜÜÚY[\IÊK˜Û\ÜÓ\ÝÙÙÛJ	Ýš\ÚX›IËÝ]KœÜÚÙ^\Ë›[™ÝOOH
NÂˆÝ]KœÜÚÙ^\Ë™›Ü‘XXÚ
Ù^HOˆÂˆÛÛœÝˆHØÝ[Y[˜Ü™X]Q[[Y[
	Ý‰ÊNÂˆ‹˜Û\ÜÓ˜[YHH	Ù]K\›ÝÉÎÂˆ‹˜\[™
Ù[
Ù^K›˜[YJJNÂˆ‹˜\[™
Ù[
Ù^K˜[ÛÜš]H	ËIÊJNÂˆ‹˜\[™
Ù[
Ù^K™š[™Ù\œš[	ËIË	Û[Û›ÉÊJNÂˆ‹˜\[™
Ù[
Ù^K˜ÛÛ[Y[	ËIÊJNÂˆÛÛœÝXÝ[ÛœÈHØÝ[Y[˜Ü™X]Q[[Y[
	Ý	ÊNÂˆXÝ[ÛœË˜Û\ÜÓ˜[YHH	ÜšYÚ	ÎÂˆÛÛœÝÜ˜\HØÝ[Y[˜Ü™X]Q[[Y[
	Ù]‰ÊNÂˆÜ˜\˜Û\ÜÓ˜[YHH	Ü›ÝËXXÝ[ÛœÉÎÂˆÜ˜\˜\[™
XÝ[Û]ÛŠ	ÚŠH~Š;ÒrÂwF&ÆW#¦6Æ—&ö&BrÂ‚’Óâ6÷•76‚†¶W’ææÖR’’“°¢w&æVæB†7F–öä'WGFöâ‚~XÊþX{¢rÂwF&ÆW#¦F÷væÆöBrÂ‚’ÓâW‡÷'E76‚†¶W’ææÖR’’“°¢–b†¶W’æ†5÷&—fFUö¶W’’°¢6öç7BvVçDÆ&VÂÒ¶W’ævVçEöÆöFVBò~[{.‹ÈžXZRr¢~XªXZRvVçBs°¢6öç7BvVçD'WGFöâÒ7F–öä'WGFöâ†vVçDÆ&VÂÂ¶W’ævVçEöÆöFVBòwF&ÆW#¦6†V6²r¢wF&ÆW#¦¶W’rÂ‚’ÓâFE76…FôvVçB†¶W’ææÖR’Â²&–Ö'“¢¶W’ævVçEöÆöFVBÒ“°¢vVçD'WGFöâæF—6&ÆVBÒ¶W’ævVçEöÆöFVC°¢w&æVæB†vVçD'WGFöâ“°¢Ð¢w&æVæB†7F–öä'WGFöâ‚~XŠ®™šBrÂwF&ÆW#§G&6‚rÂ‚’ÓâFVÆWFU76‚†¶W’ææÖR’’“°¢7F–öç2æVæB‡w&“°¢G"æVæB†7F–öç2“°¢&öG’æVæB‡G"“°¢Ò“°¢Ð ¢7–æ2gVæ7F–öâÆöDwr‚’°¢6öç7B&W7VÇBÒv—B’‚vÆ—7Eöwuö¶W—2r“°¢–b‚&W7VÇBæö²’²6†÷u&W7VÇB‡&W7VÇB“²&WGW&ã²Ð¢7FFRæwt¶W—2Ò&W7VÇBæ¶W—2ÇÂµÓ°¢B‚r6wr×7FGW2r’çFW‡D6öçFVçBÒG·7FFRæwt¶W—2æÆVæwF‡Ò{XB6V7&WB¶W–°¢&VæFW$wr‚“°¢Ð ¢gVæ7F–öâ&VæFW$wr‚’°¢6öç7B&öG’ÒB‚r6wrÖ&öG’r“°¢&öG’æ–ææW$…DÔÂÒrs°¢B‚r6wrÖV×G’r’æ6Æ74Æ—7BçFövvÆR‚wf—6–&ÆRrÂ7FFRæwt¶W—2æÆVæwF‚ÓÓÒ“°¢7FFRæwt¶W—2æf÷$V6‚†¶W’Óâ°¢6öç7BG"ÒFö7VÖVçBæ7&VFTVÆVÖVçB‚wG"r“°¢G"æ6Æ74æÖRÒvFF×&÷rs°¢G"æVæB†6VÆÂ†¶W’çW6W%ö–BÇÂG¶¶W’ææÖWÒÂG¶¶W’æVÖ–ÇÓæ’“°¢G"æVæB†6VÆÂ†¶W’æÆv÷&—F†ÒÇÂrÒr’“°¢G"æVæB†6VÆÂ†¶W’æf–ævW'&–çBÇÂrÒrÂvÖöæòr’“°¢G"æVæB†6VÆÂ†f÷&ÖDFFR†¶W’æW‡—&W5öB’’“°¢6öç7B7F–öç2ÒFö7VÖVçBæ7&VFTVÆVÖVçB‚wFBr“°¢7F–öç2æ6Æ74æÖRÒw&–v‡Bs°¢6öç7Bw&ÒFö7VÖVçBæ7&VFTVÆVÖVçB‚vF—br“°¢w&æ6Æ74æÖRÒw&÷rÖ7F–öç2s°¢w&æVæB†7F–öä'WGFöâ‚~ZHÞŠ;ÒrÂwF&ÆW#¦6Æ—&ö&BrÂ‚’Óâ6÷”wr¶W’æf–ævW'&–çB’“°¢w&æVæB†7F–öä'WGFöâ‚~XÊþX{¢rÂwF&ÆW#¦F÷væÆöBrÂ‚’ÓâW‡÷'Dwr†¶W’æf–ævW'&–çB’’“°¢w&æVæB†7F–öä'WGFöâ‚~XŠ®™šBrÂwF&ÆW#§G&6‚rÂ‚’ÓâFVÆWFTur†¶W’æf–ævW'&–çBÂ¶W’çW6W%ö–BÇÂ¶W’æf–ævW'&–çB’’“°¢7F–öç2æVæB‡w&“°¢G"æVæB†7F–öç2“°¢&öG’æVæB‡G"“°¢Ò“°¢Ð ¢7–æ2gVæ7F–öâÆöDv—B‚’°¢6öç7B&W7VÇBÒv—B’‚w&VEöv—Eö6öæf–rr“°¢–b‚&W7VÇBæö²’²6†÷u&W7VÇB‡&W7VÇB“²&WGW&ã²Ð¢7FFRæv—D6öæf–rÒ&W7VÇBæ6öæf–rÇÂ·Ó°¢B‚r6v—BÖæÖRr’çfÇVRÒ7FFRæv—D6öæf–rææÖRÇÂrs°¢B‚r6v—BÖVÖ–Âr’çfÇVRÒ7FFRæv—D6öæf–ræVÖ–ÂÇÂrs°¢B‚r6v—BÖf–ævW'&–çBr’çfÇVRÒ7FFRæv—D6öæf–rç6–væ–æuö¶W’ÇÂrs°¢B‚r6v—BÖf÷&ÖBr’çfÇVRÒ7FFRæv—D6öæf–ræwuöf÷&ÖBÇÂrs°¢B‚r6v—B×&öw&Òr’çfÇVRÒ7FFRæv—D6öæf–ræwu÷&öw&ÒÇÂrs°¢B‚r6v—B×6–væ–ærÖVæ&ÆVBr’æ6†V6¶VBÒ7FFRæv—D6öæf–ræ6öÖÖ—Eöww6–vâbb7FFRæv—D6öæf–rçFuöww6–vã°¢÷VÆFU6–væ–æt¶W—2‚“°¢Ð ¢gVæ7F–öâ÷VÆFU6–væ–æt¶W—2‚’°¢6öç7B6VÆV7BÒB‚r6v—B×6–væ–ærÖ¶W’r“°¢6VÆV7Bæ–ææW$…DÔÂÒsÆ÷F–öâfÇVSÒ"#îiÊ®˜Ži8sÂö÷F–öãâs°¢7FFRæwt¶W—2æf÷$V6‚†¶W’Óâ°¢6öç7B÷F–öâÒFö7VÖVçBæ7&VFTVÆVÖVçB‚v÷F–öâr“°¢÷F–öâçfÇVRÒ¶W’æf–ævW'&–çC°¢÷F–öâçFW‡D6öçFVçBÒG¶¶W’çW6W%ö–BÇÂtur¶W’wÒ(	BG¶¶W’æf–ævW'&–çGÖ°¢6VÆV7BæVæB†÷F–öâ“°¢Ò“°¢–b‡7FFRæv—D6öæf–sòç6–væ–æuö¶W’’6VÆV7BçfÇVRÒ7FFRæv—D6öæf–rç6–væ–æuö¶W“°¢Ð ¢7–æ2gVæ7F–öâ&Vg&W6„7W'&VçB‚’°¢6WDÆöF–ær‡G'VR“°¢G'’°¢–b‡7FFRçvRÓÓÒvF6†&ö&Br’v—B&öÖ—6RæÆÂ…¶ÆöDF6†&ö&B‚’ÂÆöDwr‚•Ò“°¢–b‡7FFRçvRÓÓÒw76‚r’v—BÆöE76‚‚“°¢–b‡7FFRçvRÓÓÒvwrr’v—BÆöDwr‚“°¢–b‡7FFRçvRÓÓÒvv—Br’²v—BÆöDwr‚“²v—BÆöDv—B‚“²Ð¢Òf–æÆÇ’°¢6WDÆöF–ær†fÇ6R“°¢Ð¢Ð ¢7–æ2gVæ7F–öâ6÷•76‚†æÖR’²6†÷u&W7VÇB†v—B’‚v6÷•÷76…÷V&Æ–5ö¶W’rÂæÖR’“²Ð¢7–æ2gVæ7F–öâW‡÷'E76‚†æÖR’°¢6öç7B&W7VÇBÒv—B’‚vW‡÷'E÷76…÷V&Æ–5ö¶W’rÂæÖR“°¢–b‡6†÷u&W7VÇB‡&W7VÇB’bb&W7VÇBçF‚’Fö7B†[{.XÊþX{®X‹G·&W7VÇBçF‡Ö“°¢Ð¢7–æ2gVæ7F–öâFE76…FôvVçB†æÖR’°¢6öç7B&W7VÇBÒv—B’‚vFE÷76…ö¶W•÷FõövVçBrÂæÖR“°¢–b‡6†÷u&W7VÇB‡&W7VÇB’’°¢v—B&öÖ—6RæÆÂ…¶ÆöE76‚‚’ÂÆöDF6†&ö&B‚•Ò“°¢Ð¢Ð ¢7–æ2gVæ7F–öâÆöDvVçDÖævW"‚’°¢6öç7B&W7VÇBÒv—B’‚vÆ—7E÷76…övVçBr“°¢–b‚&W7VÇBæö²’°¢6†÷u&W7VÇB‡&W7VÇB“°¢&VæFW$vVçDÖævW"‡²f–Æ&ÆS¢fÇ6RÂÖævVC¢fÇ6RÂ7FGW3¢~iÊ®ZZ®X¹RrÂ–FVçF—F–W3¢µÒÒ“°¢&WGW&ã°¢Ð¢&VæFW$vVçDÖævW"‡&W7VÇB“°¢Ð ¢gVæ7F–öâ&VæFW$vVçDÖævW"‡&W7VÇB’°¢B‚r6vVçBÖÖævW"×7FGW2r’çFW‡D6öçFVçBÒ&W7VÇBç7FGW2ÇÂ~iÊ®YYþX¹Rs°¢B‚r6vVçB×7F'Br’æ†–FFVâÒ&W7VÇBæf–Æ&ÆS°¢B‚r6vVçB×7F÷r’æF—6&ÆVBÒ&W7VÇBæÖævVC°¢B‚r6vVçB×7F÷r’çF—FÆRÒ&W7VÇBæÖævVBò~XÎjÚ.yK¶W’ÖævW"YYþX¹^y¨BvVçBr¢~X8^XúþXÎjÚ"¶W’ÖævW"YYþX¹^y¨BvVçBs°¢6öç7B–FVçF—F–W2Ò&W7VÇBæ–FVçF—F–W2ÇÂµÓ°¢B‚r6vVçBÖ6ÆV"r’æF—6&ÆVBÒ–FVçF—F–W2æÆVæwF‚ÓÓÒ°¢B‚r6vVçBÖV×G’r’æ6Æ74Æ—7BçFövvÆR‚wf—6–&ÆRrÂ–FVçF—F–W2æÆVæwF‚ÓÓÒ“°¢6öç7B&öG’ÒB‚r6vVçBÖ&öG’r“°¢&öG’æ–ææW$…DÔÂÒrs°¢–FVçF—F–W2æf÷$V6‚†–FVçF—G’Óâ°¢6öç7BG"ÒFö7VÖVçBæ7&VFTVÆVÖVçB‚wG"r“°¢G"æ6Æ74æÖRÒvFF×&÷rs°¢G"æVæB†6VÆÂ†–FVçF—G’æÆö6ÅöæÖRÇÂ–FVçF—G’æ6öÖÖVçBÇÂtvVçB¶W’r’“°¢G"æVæB†6VÆÂ†–FVçF—G’æÆv÷&—F†ÒÇÂrÒr’“°¢G"æVæB†6VÆÂ†–FVçF—G’æf–ævW'&–çBÇÂrÒrÂvÖöæòr’“°¢6öç7B7F–öç2ÒFö7VÖVçBæ7&VFTVÆVÖVçB‚wFBr“°¢7F–öç2æ6Æ74æÖRÒw&–v‡Bs°¢6öç7Bw&ÒFö7VÖVçBæ7&VFTVÆVÖVçB‚vF—br“°¢w&æ6Æ74æÖRÒw&÷rÖ7F–öç2s°¢w&æVæB†7F–öä'WGFöâ‚~z{¾™šBrÂwF&ÆW#§G&6‚rÂ‚’Óâ&VÖ÷fTvVçD–FVçF—G’†–FVçF—G’æf–ævW'&–çBÂ–FVçF—G’æÆö6ÅöæÖRÇÂ–FVçF—G’æ6öÖÖVçBÇÂ–FVçF—G’æf–ævW'&–çB’’“°¢7F–öç2æVæB‡w&“°¢G"æVæB†7F–öç2“°¢&öG’æVæB‡G"“°¢Ò“°¢Ð ¢7–æ2gVæ7F–öâ÷VävVçDÖævW"‚’°¢B‚r6vVçBÖF–Æörr’ç6†÷tÖöFÂ‚“°¢v—BÆöDvVçDÖævW"‚“°¢Ð ¢7–æ2gVæ7F–öâ7F'DvVçB‚’°¢–b‡6†÷u&W7VÇB†v—B’‚w7F'E÷76…övVçBr’’’²v—B&öÖ—6RæÆÂ…¶ÆöDvVçDÖævW"‚’ÂÆöE76‚‚•Ò“²Ð¢Ð ¢7–æ2gVæ7F–öâ&VÖ÷fTvVçD–FVçF—G’†f–ævW'&–çBÂÆ&VÂ’°¢–b‚v–æF÷ræ6öæf—&Ò†z+®Zé®Šh[éâ54‚vVçBz{¾™šN8ÂG¶Æ&VÇÞ8ÞûÉð ®zÎz)þKˆ®y¨B¶W’j©NjŽKˆÞiÈ>Š*¾XŠ®™šN8&’’&WGW&ã°¢–b‡6†÷u&W7VÇB†v—B’‚w&VÖ÷fU÷76…övVçEö¶W’rÂf–ævW'&–çB’’’v—B&öÖ—6RæÆÂ…¶ÆöDvVçDÖævW"‚’ÂÆöE76‚‚•Ò“°¢Ð ¢7–æ2gVæ7F–öâ6ÆV$vVçB‚’°¢–b‚v–æF÷ræ6öæf—&Ò†z+®Zé®Šhkˆ^z›¢54‚vVçBXZ~y¨Nh˜iÈ’¶WžûÉð ®zÎz)þKˆ®y¨B¶W’j©NjŽKˆÞiÈ>Š*¾XŠ®™šN8&’’&WGW&ã°¢–b‡6†÷u&W7VÇB†v—B’‚v6ÆV%÷76…övVçBr’’’v—B&öÖ—6RæÆÂ…¶ÆöDvVçDÖævW"‚’ÂÆöE76‚‚•Ò“°¢Ð ¢7–æ2gVæ7F–öâ7F÷vVçB‚’°¢–b‚v–æF÷ræ6öæf—&Ò‚~z+®Zé®ŠhXÎjÚ.yK¶W’ÖævW"YYþX¹^y¨B54‚vVçNûÉòr’’&WGW&ã°¢–b‡6†÷u&W7VÇB†v—B’‚w7F÷÷76…övVçBr’’’v—B&öÖ—6RæÆÂ…¶ÆöDvVçDÖævW"‚’ÂÆöE76‚‚•Ò“°¢Ð¢7–æ2gVæ7F–öâFVÆWFU76‚†æÖR’°¢–b‚v–æF÷ræ6öæf—&Ò†z+®Zé®ŠhXŠ®™šB54‚¶Wž8ÂG¶æÖWÞ8ÞûÉõÆåÆî˜	žiÈ>XŠ®™šB&—fFR¶W’ˆˆrçV.ûÈÎK‰NxJk9^[êžXéþ8&’’&WGW&ã°¢–b‡6†÷u&W7VÇB†v—B’‚vFVÆWFU÷76…ö¶W’rÂæÖR’’’v—BÆöE76‚‚“°¢Ð¢7–æ2gVæ7F–öâ6÷”wr†f–ævW'&–çB’²6†÷u&W7VÇB†v—B’‚v6÷•öwu÷V&Æ–5ö¶W’rÂf–ævW'&–çB’“²Ð¢7–æ2gVæ7F–öâW‡÷'Dwr†f–ævW'&–çB’°¢6öç7B&W7VÇBÒv—B’‚vW‡÷'Eöwu÷V&Æ–5ö¶W’rÂf–ævW'&–çB“°¢–b‡6†÷u&W7VÇB‡&W7VÇB’bb&W7VÇBçF‚’Fö7B†[{.XÊþX{®ˆ{2G·&W7VÇBçF‡Ö“°¢Ð¢7–æ2gVæ7F–öâFVÆWFTwr†f–ævW'&–çBÂÆ&VÂ’°¢–b‚v–æF÷ræ6öæf—&Ò†z+®Zé®ŠhXŠ®™šBur¶Wž8ÂG¶Æ&VÇÞ8ÞûÉõÆåÆå6V7&WB¶W’ˆˆrV&Æ–2¶W’˜;ÞiÈ>XŠ®™šNûÈÎK‰NxJk9^[êžXéþ8&’’&WGW&ã°¢–b‡6†÷u&W7VÇB†v—B’‚vFVÆWFUöwuö¶W’rÂf–ævW'&–çB’’’°¢7FFRç6VÆV7FVDwrÒrs°¢v—BÆöDwr‚“°¢Ð¢Ð ¢gVæ7F–öâWFFTv—Df–ævW'&–çB‚’²B‚r6v—BÖf–ævW'&–çBr’çfÇVRÒB‚r6v—B×6–væ–ærÖ¶W’r’çfÇVRÇÂrs²Ð ¢7–æ2gVæ7F–öâ6fTv—D–FVçF—G’‚’°¢6öç7B&W7VÇBÒv—B’‚w6fUöv—Eö–FVçF—G’rÂB‚r6v—BÖæÖRr’çfÇVRçG&–Ò‚’ÂB‚r6v—BÖVÖ–Âr’çfÇVRçG&–Ò‚’“°¢–b‡6†÷u&W7VÇB‡&W7VÇB’’v—BÆöDv—B‚“°¢Ð ¢7–æ2gVæ7F–öâ6fTv—E6–væ–ær‚’°¢6öç7B&W7VÇBÒv—B’‚w6fUöv—E÷6–væ–ærrÂB‚r6v—B×6–væ–ærÖ¶W’r’çfÇVRÇÂrrÂB‚r6v—B×6–væ–ærÖVæ&ÆVBr’æ6†V6¶VB“°¢–b‡6†÷u&W7VÇB‡&W7VÇB’’v—BÆöDv—B‚“°¢Ð ¢7–æ2gVæ7F–öâ7V&Ö—E76‚†WfVçB’°¢WfVçBç&WfVçDFVfVÇB‚“°¢6öç7Bf÷&ÒÒWfVçBæ7W'&VçEF&vWC°¢6öç7BFFÒö&¦V7Bæg&öÔVçG&–W2†æWrf÷&ÔFF†f÷&Ò’“°¢–b†FFç77‡&6RÓÒFFæ6öæf—&Ò’²Fö7B‚~XZžjÊ77‡&6RKˆÞKˆˆ{BrÂvW'&÷"r“²&WGW&ã²Ð¢B‚r776‚×7V&Ö—Br’æF—6&ÆVBÒG'VS°¢6öç7B&W7VÇBÒv—B’‚v7&VFU÷76…ö¶W’rÂ²f–ÆVæÖS¢FFæf–ÆVæÖRÂ6öÖÖVçC¢FFæ6öÖÖVçBÂÆv÷&—F†Ó¢FFæÆv÷&—F†ÒÂ77‡&6S¢FFç77‡&6RÒ“°¢B‚r776‚×7V&Ö—Br’æF—6&ÆVBÒfÇ6S°¢–b‡6†÷u&W7VÇB‡&W7VÇBÂu54‚¶W’[»®z¸¾ZèÎh‰r’’²B‚r776‚ÖF–Æörr’æ6Æ÷6R‚“²f÷&Òç&W6WB‚“²f÷&ÒæVÆVÖVçG2æf–ÆVæÖRçfÇVRÒv–E÷'6s²v—BÆöE76‚‚“²Ð¢Ð ¢7–æ2gVæ7F–öâ7V&Ö—Dwr†WfVçB’°¢WfVçBç&WfVçDFVfVÇB‚“°¢6öç7Bf÷&ÒÒWfVçBæ7W'&VçEF&vWC°¢6öç7BFFÒö&¦V7Bæg&öÔVçG&–W2†æWrf÷&ÔFF†f÷&Ò’“°¢B‚r6wr×7V&Ö—Br’æF—6&ÆVBÒG'VS°¢6öç7B&W7VÇBÒv—B’‚v7&VFUöwuö¶W’rÂ²æÖS¢FFææÖRÂVÖ–Ã¢FFæVÖ–ÂÂÆv÷&—F†Ó¢FFæÆv÷&—F†ÒÂW‡—&S¢FFæW‡—&RÒ“°¢B‚r6wr×7V&Ö—Br’æF—6&ÆVBÒfÇ6S°¢–b‡6†÷u&W7VÇB‡&W7VÇBÂtur¶W’[»®z¸¾ZèÎh‰r’’²B‚r6wrÖF–Æörr’æ6Æ÷6R‚“²f÷&Òç&W6WB‚“²v—BÆöDwr‚“²Ð¢Ð ¢gVæ7F–öâ6WEF†VÖR‡F†VÖR’°¢Fö7VÖVçBæFö7VÖVçDVÆVÖVçBæFF6WBçF†VÖRÒF†VÖS°¢G'’²Æö6Å7F÷&vRç6WD—FVÒ‚v¶W’ÖÖævW"×F†VÖRrÂF†VÖR“²Ò6F6‚…ò’·Ð¢6öç7BF&²ÒF†VÖRÓÓÒvF&²s°¢B‚r7F†VÖR×FW‡Br’çFW‡D6öçFVçBÒF&²ò~k{®ˆ›.jŠ[Èòr¢~k{ˆ›.jŠ[Èòs°¢B‚r7F†VÖRÖ'Fâæ–6öâr’æFF6WBæ–6öâÒF&²òwF&ÆW#§7Vâr¢wF&ÆW#¦Öööâs°¢v–æF÷rä–6öæ–g”Æö6Âç&VæFW$–6öç2‚B‚r7F†VÖRÖ'Fâr’“°¢Ð ¢gVæ7F–öâ&–æDWfVçG2‚’°¢BB‚rææbÖ—FVÒr’æf÷$V6‚†'FâÓâ'FâæFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ‚’Óâ7v—F6…vR†'FâæFF6WBçvR’’“°¢B‚r7&Vg&W6‚Ö'Fâr’æFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ&Vg&W6„7W'&VçB“°¢B‚r7F†VÖRÖ'Fâr’æFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ‚’Óâ6WEF†VÖR†Fö7VÖVçBæFö7VÖVçDVÆVÖVçBæFF6WBçF†VÖRÓÓÒvF&²ròvÆ–v‡Br¢vF&²r’“°¢B‚r776‚Ö7&VFRÖ'Fâr’æFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ‚’ÓâB‚r776‚ÖF–Æörr’ç6†÷tÖöFÂ‚’“°¢B‚r6vVçBÖÖævRÖ'Fâr’æFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ÷VävVçDÖævW"“°¢B‚r6vVçBÖ6æ6VÂ×‚r’æFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ‚’ÓâB‚r6vVçBÖF–Æörr’æ6Æ÷6R‚’“°¢B‚r6vVçBÖ6Æ÷6Rr’æFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ‚’ÓâB‚r6vVçBÖF–Æörr’æ6Æ÷6R‚’“°¢B‚r6vVçB×7F'Br’æFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ7F'DvVçB“°¢B‚r6vVçBÖ6ÆV"r’æFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ6ÆV$vVçB“°¢B‚r6vVçB×7F÷r’æFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ7F÷vVçB“°¢B‚r6wrÖ7&VFRÖ'Fâr’æFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ‚’ÓâB‚r6wrÖF–Æörr’ç6†÷tÖöFÂ‚’“°¢B‚r776‚Ö6æ6VÂr’æFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ‚’ÓâB‚r776‚ÖF–Æörr’æ6Æ÷6R‚’“°¢B‚r776‚Ö6æ6VÂ×‚r’æFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ‚’ÓâB‚r776‚ÖF–Æörr’æ6Æ÷6R‚’“°¢B‚r6wrÖ6æ6VÂr’æFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ‚’ÓâB‚r6wrÖF–Æörr’æ6Æ÷6R‚’“°¢B‚r6wrÖ6æ6VÂ×‚r’æFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ‚’ÓâB‚r6wrÖF–Æörr’æ6Æ÷6R‚’“°¢B‚r776‚Öf÷&Òr’æFDWfVçDÆ—7FVæW"‚w7V&Ö—BrÂ7V&Ö—E76‚“°¢B‚r6wrÖf÷&Òr’æFDWfVçDÆ—7FVæW"‚w7V&Ö—BrÂ7V&Ö—Dwr“°¢B‚r6v—B×6–væ–ærÖ¶W’r’æFDWfVçDÆ—7FVæW"‚v6†ævRrÂWFFTv—Df–ævW'&–çB“°¢B‚r6v—B×6fRÖ–FVçF—G’r’æFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ6fTv—D–FVçF—G’“°¢B‚r6v—B×6fR×6–væ–ærr’æFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ6fTv—E6–væ–ær“°¢BB‚u¶FFÖ7F–öãÒ&÷Vâ×76‚Ö7&VFR%Òr’æf÷$V6‚†'FâÓâ'FâæFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ‚’Óâ²7v—F6…vR‚w76‚rÂfÇ6R“²B‚r776‚ÖF–Æörr’ç6†÷tÖöFÂ‚“²Ò’“°¢BB‚u¶FFÖ7F–öãÒ&÷VâÖwrÖ7&VFR%Òr’æf÷$V6‚†'FâÓâ'FâæFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ‚’Óâ²7v—F6…vR‚vwrrÂfÇ6R“²B‚r6wrÖF–Æörr’ç6†÷tÖöFÂ‚“²Ò’“°¢BB‚u¶FFÖ7F–öãÒ&÷VâÖv—B%Òr’æf÷$V6‚†'FâÓâ'FâæFDWfVçDÆ—7FVæW"‚v6Æ–6²rÂ‚’Óâ7v—F6…vR‚vv—Br’’“°¢Ð ¢7–æ2gVæ7F–öâ&ö÷E&VÄ'&–FvR‚’°¢7FFRæ'&–FvRÒv–æF÷rç—vV'f–Wræ“°¢7FFRæÖö6²ÒfÇ6S°¢v—BÆöD–æfò‚“°¢v—B&Vg&W6„7W'&VçB‚“°¢Ð ¢7–æ2gVæ7F–öâÆöDÖö6´FF‚’°¢–b‡7FFRæ'&–FvR’&WGW&ã°¢7FFRæÖö6²ÒG'VS°¢v—BÆöD–æfò‚“°¢v—B&Vg&W6„7W'&VçB‚“°¢Fö7B‚~xþŠkÞYšŽš	ŠkÞjŠ[ÈþûÉ®yºîX˜ÞšþzK®zøNKè¾‹8~ii’rÂw7V66W72rÂ#C“°¢Ð ¢gVæ7F–öâ&ö÷B‚’°¢v–æF÷rä–6öæ–g”Æö6Âç&VæFW$–6öç2‚“°¢&–æDWfVçG2‚“°¢ÆWBF†VÖRÒvÆ–v‡Bs°¢G'’²F†VÖRÒÆö6Å7F÷&vRævWD—FVÒ‚v¶W’ÖÖævW"×F†VÖRr’ÇÂvÆ–v‡Bs²Ò6F6‚…ò’·Ð¢6WEF†VÖR‡F†VÖR“°¢ÆWBfÆÆ&6µF–ÖW"Òv–æF÷rç6WEF–ÖV÷WB†ÆöDÖö6´FFÂ3S“°¢v–æF÷ræFDWfVçDÆ—7FVæW"‚w—vV'f–Ww&VG’rÂ7–æ2‚’Óâ°¢v–æF÷ræ6ÆV%F–ÖV÷WB†fÆÆ&6µF–ÖW"“°¢v—B&ö÷E&VÄ'&–FvR‚“°¢Ò“°¢Ð ¢v–æF÷ræÆöDÖö6´FFÒÆöDÖö6´FF°¢Fö7VÖVçBæFDWfVçDÆ—7FVæW"‚tDôÔ6öçFVçDÆöFVBrÂ&ö÷B“°§Ò’‚“°