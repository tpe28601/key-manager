# Key Manager

**Key Manager 1.0.0** 是一套專為 Windows 設計的 SSH 與 GPG 金鑰管理工具，使用 Python + pywebview 提供桌面圖形介面，整合 Git for Windows 的 SSH、GPG 與 Git 全域簽章設定。

Key Manager 的目標是把常見的 SSH Key、GPG Key、SSH Agent 與 Git Commit / Tag Signing 操作集中到同一個介面，同時避免在 UI 中顯示或匯出 Private Key。

## 功能總覽

### SSH Key 管理

- 掃描目前設定的 SSH Key 目錄。
- 建立 **RSA 4096** 或 ED25519 SSH Key。
- 預設建立名稱為 `id_rsa`，演算法為 **RSA 4096**。
- 支援 SSH Private Key Passphrase。
- 複製或匯出 Public Key。
- 刪除 SSH Key Pair。
- 可自訂本機 SSH Key 儲存目錄。
- 可開啟目前 SSH Key 資料夾。

### SSH Agent 管理

- 查看 SSH Agent 是否啟動及目前載入的 Key 數量。
- 將指定 Private Key 加入 Agent。
- 有 Passphrase 的 SSH Key 會透過 Git for Windows AskPass 視窗要求輸入密碼。
- 列出 Agent 內已載入的 Key。
- 移除單一 Key。
- 清空 Agent 內所有 Key。
- 可啟動 Key Manager 管理的 `ssh-agent`。
- 僅允許停止由 Key Manager 自行啟動的 Agent，避免誤停外部 Agent。

### GPG Key 管理

- 使用 Git for Windows 內建的 GnuPG 環境列出 Secret/Public Key。
- 建立 **RSA 4096** 或 ED25519 GPG Key。
- 預設演算法為 **RSA 4096**。
- GPG Passphrase 完全交由 GnuPG 原生 Pinentry 視窗處理。
- 複製或匯出 ASCII Armor Public Key。
- 刪除 Secret/Public Key。

### Git GPG Signing

可直接管理 Git 全域身份與 GPG Signing 設定：

```text
git config --global user.name
git config --global user.email
git config --global user.signingkey
git config --global gpg.format openpgp
git config --global gpg.program
git config --global commit.gpgsign
git config --global tag.gpgSign
```

啟用「Git GPG 簽章」後，Commit 與 Tag 都會使用選定的完整 GPG Fingerprint 簽章。

## 系統需求

Key Manager 目前以 **Windows 10 / Windows 11** 為主要執行環境。

正式打包後的使用者電腦不需要另外安裝 Python，但需要：

1. **Git for Windows**
   - 預期安裝於：`C:\Program Files\Git`
   - Key Manager 使用其中的 Git、Git Bash、OpenSSH、GnuPG、Pinentry / AskPass 元件。
2. **Microsoft Edge WebView2 Runtime**
   - 多數 Windows 10 / 11 已隨 Microsoft Edge 提供。
   - 精簡版或企業映像若移除了 WebView2，需要另外安裝 Runtime。

開發與自行建置時另外需要：

- Python 3.11 以上，建議 Python 3.12。
- PowerShell。

## 安裝與執行

### 使用正式 EXE

在 Windows 上完成建置後，直接執行：

```text
dist\KeyManager.exe
```

Key Manager 會使用本機 Git for Windows 的 SSH / GPG 環境，不需要額外建立獨立的 GPG Home。

### 從原始碼執行

PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
key-manager
```

也可以執行專案提供的：

```text
run_windows.bat
```

## 建置 Windows EXE

專案已包含 PyInstaller 設定與 Windows 建置腳本。

在專案根目錄執行：

```text
build_windows_exe.bat
```

建置腳本會建立虛擬環境、安裝建置依賴並執行 PyInstaller。完成後輸出：

```text
dist\KeyManager.exe
```

`key_manager.spec` 會將 Web UI 靜態檔、應用程式圖示與 Windows 版本資訊一起封裝。

若要手動準備建置環境：

```powershell
py -3.12 -m venv .build-venv
.\.build-venv\Scripts\Activate.ps1
pip install -e ".[build]"
pyinstaller --clean --noconfirm key_manager.spec
```

## 使用方法

### 建立 SSH Key

1. 開啟「SSH 金鑰」。
2. 按「建立 SSH 金鑰」。
3. 預設名稱為 `id_rsa`，演算法為 RSA 4096。
4. 可填寫 Email / Comment。
5. Passphrase 可留空；若設定 Passphrase，Private Key 會以加密 OpenSSH 格式儲存。
6. 建立後可以複製或匯出 `.pub` Public Key。

Key Manager 不提供 Private Key 顯示或匯出功能。

### 自訂 SSH Key 路徑

SSH 頁面可選擇其他本機資料夾作為 Key 目錄。設定會保存於：

```text
%LOCALAPPDATA%\KeyManager\settings.json
```

未自訂時使用：

```text
%USERPROFILE%\.ssh
```

「恢復預設」會重新使用 `%USERPROFILE%\.ssh`。

### 將 SSH Key 加入 Agent

1. 在 SSH Key 列表選擇要使用的 Key。
2. 按「加入 Agent」。
3. 如果 Agent 尚未啟動，Key Manager 會啟動 Git for Windows 的 `ssh-agent.exe`。
4. 如果 Private Key 有 Passphrase，會由 Git for Windows AskPass GUI 要求輸入密碼。
5. 成功後狀態會顯示已載入的 Key 數量。

「管理 Agent」可查看、移除或清空目前 Agent 內的 Key。

### 建立 GPG Key

1. 開啟「GPG 金鑰」。
2. 按「建立 GPG 金鑰」。
3. 輸入 Name 與 Email。
4. 預設演算法為 RSA 4096，也可改用 ED25519。
5. 選擇有效期限。
6. GnuPG 會顯示原生 Pinentry 視窗設定 Passphrase。

Key Manager 不會取得 GPG Passphrase。GPG Key 使用 Git Bash 中的 GnuPG 環境，因此和 Git for Windows 使用的 GPG Key 保持一致。

### 啟用 Git Commit / Tag GPG Signing

1. 先建立或確認已有可用的 GPG Secret Key。
2. 到「Git 設定」填入 `user.name` 與 `user.email`。
3. 選擇完整的 GPG Fingerprint。
4. 啟用 Git GPG 簽章。

Key Manager 會同步設定：

```text
gpg.format=openpgp
gpg.program=C:\Program Files\Git\usr\bin\gpg.exe
user.signingkey=<完整 Fingerprint>
commit.gpgsign=true
tag.gpgSign=true
```

之後一般 `git commit` 與 annotated/signed tag 流程即可使用同一把 GPG Key。

## 安全設計

Key Manager 對 Private Key 與 Passphrase 採取以下原則：

- UI 不提供 SSH / GPG Private Key 內容顯示。
- UI 不提供 Private Key 匯出。
- SSH Passphrase 只在建立 Private Key 時交給 Python `cryptography` 加密，不放入外部命令參數。
- SSH Key 加入 Agent 時，Passphrase 由 Git for Windows AskPass 視窗處理。
- GPG Passphrase 由 GnuPG / Pinentry 處理；Key Manager 不讀取、不保存、不轉送。
- Windows 外部 subprocess 使用隱藏 Console 的方式執行。
- GPG 操作固定透過 Git Bash，避免使用另一套 GPG Home 造成 Git 與 Key Manager 看到不同 Key。
- 刪除 SSH Key 時只允許操作目前設定的 SSH Key 目錄內已掃描到的 Key。

## Git for Windows 整合

Key Manager 預期使用以下 Git for Windows 元件：

```text
C:\Program Files\Git\cmd\git.exe
C:\Program Files\Git\bin\bash.exe
C:\Program Files\Git\usr\bin\gpg.exe
C:\Program Files\Git\usr\bin\ssh.exe
C:\Program Files\Git\usr\bin\ssh-add.exe
C:\Program Files\Git\usr\bin\ssh-agent.exe
```

SSH AskPass 會從 Git for Windows 的常見安裝位置偵測，例如：

```text
C:\Program Files\Git\mingw64\libexec\git-core\git-gui--askpass.exe
```

GPG 指令由 Git Bash 轉發：

```text
C:\Program Files\Git\bin\bash.exe -lc 'exec gpg "$@"'
```

因此 Key Manager 的 GPG Key 列表和 Git Bash 中執行下列指令時使用的是同一個 GnuPG 環境：

```bash
gpg --list-secret-keys --keyid-format LONG
```

## 專案結構

```text
key-manager/
├── assets/
│   └── key_manager.ico
├── docs/
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

安裝開發依賴後執行：

```powershell
pip install -e ".[dev]"
pytest -q
```

也建議在提交或發布前檢查 Python 與前端 JavaScript 語法。

## License / Third-party notices

第三方套件與授權資訊請參閱：

```text
THIRD_PARTY_NOTICES.md
```
