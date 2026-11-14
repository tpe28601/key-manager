# Key Manager

**Key Manager 1.2.4** 是一套專為 Windows 打造的 SSH／GPG 金鑰管理工具，把散落在指令列裡的 `ssh-keygen`、`ssh-agent`、`gpg`、`git config` 操作，收進一個原生桌面視窗（pywebview）或本機瀏覽器頁面（Dev-Toolbox Web 模式）裡。不管是要生一把新的 SSH Key、把 Key 丟進 Agent、建立簽章用的 GPG Key，還是幫 Git commit 打開簽章，都可以在介面上點幾下完成，不用再背指令。

它是 Git for Windows 內建工具（`ssh.exe`、`ssh-agent.exe`、`ssh-keygen.exe`、`gpg.exe`）的前台介面，本身不做任何加密運算，也**不會顯示或匯出 Private Key**——Passphrase 一律交給 Git for Windows AskPass（SSH）或 GnuPG Pinentry（GPG）的原生視窗處理。

作者：**Mike Lin**

## 功能總覽

一打開 Key Manager，你可以做到：

### SSH Key 管理
- 掃描目前設定的 SSH Key 目錄，一眼看到所有 Key 的演算法與 Fingerprint。
- 建立 **RSA 4096** 或 **ED25519** SSH Key（預設名稱 `id_rsa`、演算法 RSA 4096）。
- 幫 Key 加上 Passphrase。
- 複製或匯出 Public Key。
- 刪除不用的 Key Pair。
- 自訂 SSH Key 的本機儲存目錄。

### SSH Agent 管理
- 一眼看出 Agent 是否啟動、目前載入了幾把 Key。
- 把指定的 Private Key 加入 Agent；有 Passphrase 的話會跳出 Git for Windows AskPass 視窗輸入。
- Key Manager 自己啟動的 Agent，連線資訊會存起來，下次開程式會自動接回去。
- 可以單獨移除、或一次清空 Agent 裡的 Key。
- 只能停掉由 Key Manager 自己啟動的 Agent，不會誤殺你手動啟動的 Agent。

### GPG Key 管理
- 透過 Git for Windows 內建的 GnuPG 環境列出 Secret / Public Key。
- 建立 **RSA 4096** 或 **ED25519** GPG Key。
- Passphrase 全程由 GnuPG 原生的 Pinentry 視窗處理，Key Manager 完全碰不到。
- 複製或匯出 ASCII Armor 格式的 Public Key。
- 刪除不需要的 Secret / Public Key。

### Git Commit / Tag GPG Signing
一鍵套用簽章設定，Key Manager 會幫你把下面這些全域 Git 設定寫好：

```text
gpg.format=openpgp
gpg.program=C:\Program Files\Git\usr\bin\gpg.exe
user.signingkey=<完整 Fingerprint>
commit.gpgsign=true
tag.gpgSign=true
```

### 資料夾 Git 設定（Profiles）
不同案子要用不同的 name／email／簽章 Key？在左側「資料夾設定」頁建立 Profile：每個 Profile 對應一個专属設定檔與一或多個資料夾，Key Manager 用全域 `.gitconfig` 的 `includeIf.gitdir/i:` 讓這些資料夾（含子資料夾）裡的 repo 自動套用對應設定，離開資料夾就回到全域預設。

- 每個欄位都可以選「沿用全域」：不寫入該設定，繼續吃全域值；SSH Key 可以從清單選，也可以貼自訂 `sshCommand`
- 所有讀寫都透過 git 指令完成，你自己在 `.gitconfig` 寫的註解、排版與其他設定完全不會被改動；每次寫入前都會先備份到 `backups/`（每個檔案各保留最近 20 份），在「備份與還原…」視窗可瀏覽清單、預覽任何一份的內容並一鍵還原（還原前同樣先備份目前的檔案，可反悔），也能開資料夾手動處理
- 「檢查實際生效值」會在指定資料夾跑 `git config --show-origin --show-scope`，列出真正生效的值與來源檔案；Profile 設定被全域值蓋掉、資料夾巢狀重疊或資料夾不见了都會在卡片上示警，並提供一鍵「修正順序」
- 你手寫 `includeIf` 指向的既有設定檔也會被辨識出來（標示為外部檔案），可以直接在介面上編輯，刪除 Profile 時只移除了 `includeIf` 行，檔案本身保留

> ⚠️ 限制：`includeIf.gitdir/i:` 是以 repo 的 `.git` 位置判斷。`git worktree` 開到資料夾外面時照常套用（`.git` 在主 repo），但**主 repo 在 Profile 資料夾外的 worktree 不會套用**該 Profile；「檢查實際生效值」遇到這種情況會明確提示。

### 金鑰使用位置
SSH／GPG 列表新增「使用位置」欄位，顯示每把 Key 目前被全域設定、哪些資料夾 Profile 或 `~/.ssh/config` 的 Host 引用；刪除金鑰前，確認對話框也會完整列出這些位置，避免誤刪正在使用的 Key。

### 介面主題
支援淺色／深色模式，設定會存在本機，下次開啟自動套用上次用的主題。

## 安全設計

Key Manager 是拿來管理金鑰的工具，安全性是第一原則：

- UI **不提供** SSH / GPG Private Key 內容顯示，也不提供匯出。
- SSH Passphrase 不會被當成外部命令的參數傳遞。
- SSH Key 加入 Agent 時，Passphrase 由 Git for Windows AskPass 原生視窗處理。
- GPG Passphrase 全程交給 GnuPG / Pinentry，Key Manager 不讀取、不保存、不轉送。
- 所有 Windows 外部 subprocess 呼叫都以隱藏 Console 視窗執行。
- 本機保存的 SSH Agent 連線資訊只有 `SSH_AUTH_SOCK` / `SSH_AGENT_PID`，不含 Passphrase 或金鑰內容。

## 系統需求

Key Manager 以 **Windows 10 / Windows 11** 為主要執行環境。

使用正式 EXE 需要：

1. **Git for Windows**，預期安裝於 `C:\Program Files\Git`。
2. **Microsoft Edge WebView2 Runtime**。

想自行從原始碼建置，需要 Python 3.11 以上（建議 3.12）。

## 安裝與執行

**一般使用者**：下載 `KeyManager.exe`，直接雙擊執行即可，不需要安裝步驟。

**想從原始碼跑**：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
key-manager
```

或直接雙擊執行 `run_windows.bat`。

## 使用方法

### 建立 SSH Key
1. 開啟「SSH 金鑰」頁面。
2. 按「建立 SSH 金鑰」。
3. 預設名稱是 `id_rsa`、演算法是 RSA 4096，兩者都可以改。
4. 依需求填寫 Email / Comment 與 Passphrase。
5. 建立完成後，可以直接複製或匯出 `.pub` Public Key。

> Key Manager 不提供 Private Key 顯示或匯出功能，這是刻意的安全設計，不是漏做。

### 把 SSH Key 加進 Agent
1. 在 SSH Key 列表按「加入 Agent」。
2. Agent 還沒啟動的話，Key Manager 會自動幫你啟動 Git for Windows 的 `ssh-agent.exe`。
3. 有 Passphrase 的 Key，會跳出 Git for Windows 的 AskPass 視窗要你輸入。
4. 重新開啟 Key Manager 時，如果先前啟動的 Agent 還活著，會自動接回去；Agent 已經關掉的話，舊資訊會自動作廢。

### 建立 GPG Key
1. 開啟「GPG 金鑰」頁面。
2. 按「建立 GPG 金鑰」。
3. 輸入 Name 與 Email。
4. 預設演算法是 RSA 4096，也可以改成 ED25519。
5. GnuPG 會跳出原生的 Pinentry 視窗讓你設定 Passphrase（Key Manager 完全看不到這組密碼）。

### 啟用 Git Commit / Tag GPG Signing
1. 到「Git 設定」頁面，填入 `user.name`、`user.email`。
2. 選擇要用來簽章的 GPG Key（完整 Fingerprint）。
3. 打開「Git GPG 簽章」開關即可——Commit 跟 Tag 會一起套用同一組設定。

---

以下是給想要自行建置或參與開發的人看的補充資訊。

## 建置 Windows EXE

在專案根目錄執行：

```text
build_windows_exe.bat
```

正式建置採用 **PyInstaller 單一 EXE**，並停用 UPX。完成後會輸出：

```text
dist\KeyManager.exe
dist\KeyManager.exe.sha256
```

SHA-256 檔可用來核對發布後的檔案完整性。

## Windows Defender 與發布

Key Manager 使用 PyInstaller **單一 EXE** 封裝。未簽章、低下載量或由打包器產生的 Windows 應用程式，有機會被 Microsoft Defender 的機器學習或啟發式偵測誤判；停用 UPX 是為了減少額外的壓縮特徵，但不保證完全避免誤判。

若自行建置的 EXE 被偵測為 `Trojan:Win32/Wacatac.C!ml`：

1. 不要直接關閉 Defender 或替整個下載資料夾加入排除。
2. 確認原始碼與建置環境可信，並核對 SHA-256。
3. 將檔案提交 Microsoft Security Intelligence 進行誤判分析。
4. 對外正式發布時建議使用 Authenticode Code Signing 憑證簽署 EXE。

## Git for Windows 整合

Key Manager 主要呼叫這些固定路徑的執行檔：

```text
C:\Program Files\Git\cmd\git.exe
C:\Program Files\Git\bin\bash.exe
C:\Program Files\Git\usr\bin\gpg.exe
C:\Program Files\Git\usr\bin\ssh.exe
C:\Program Files\Git\usr\bin\ssh-add.exe
C:\Program Files\Git\usr\bin\ssh-agent.exe
```

AskPass 常見位置：

```text
C:\Program Files\Git\mingw64\libexec\git-core\git-gui--askpass.exe
```

## 專案結構

```text
key-manager/
├── assets/
│   └── key_manager.ico
├── src/key_manager/
│   ├── git/              # Git for Windows 與 Git 全域設定
│   ├── gpg/              # GPG 掃描、建立、刪除、匯出與 Git Bash runtime
│   ├── ssh/              # SSH Key 與 SSH Agent
│   ├── web/              # pywebview bridge 與 Web UI
│   ├── command.py        # 安全的外部命令 runner
│   ├── metadata.py       # 應用程式版本與產品資訊
│   └── settings.py       # 本機設定
├── tests/                # pytest 測試
├── build_windows_exe.bat
├── run_windows.bat
├── key_manager.spec
├── pyproject.toml
├── version_info.txt
└── README.md
```

## 測試

```powershell
pip install -e ".[dev]"
pytest -q
```

## Dev-Toolbox Web 模式

除了 pywebview 桌面版，本工具也能以純標準函式庫的 HTTP 服務執行，給 Dev-Toolbox Hub 呼叫（或自行開瀏覽器使用）。此模式**不需要安裝 pywebview**，只要 Python 3.11+：

```powershell
python web_server.py                # 預設 8730，被占用時自動往上找（最多 +20）
python web_server.py --open-browser # 啟動後直接開瀏覽器
```

- 只綁定 `127.0.0.1`；停止按 Ctrl+C，或由 Hub 呼叫 `POST /api/shutdown`。
- 介面與桌面版相同；「選擇資料夾」「匯出存檔」這類原生對話框在 Web 模式無法使用，會提示改用桌面版。
- 若環境沒有 `cryptography` 套件，產生 SSH Key 會自動改用本機 `ssh-keygen`。
- 設定檔存放在 `%LOCALAPPDATA%\DevToolbox\key-manager\settings.json`（首次啟動會從舊的 `%LOCALAPPDATA%\KeyManager\` 複製一份；桌面版仍使用原本位置）。

## License / Third-party notices

第三方套件與授權資訊請參閱 `THIRD_PARTY_NOTICES.md`。
