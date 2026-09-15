# Key Manager

**Key Manager 1.0.1** 是一套專為 Windows 設計的 SSH 與 GPG 金鑰管理工具，使用 Python + pywebview 提供桌面圖形介面，整合 Git for Windows 的 SSH、GPG 與 Git 全域簽章設定。

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

### SSH Agent 管理

- 查看 SSH Agent 是否啟動及目前載入的 Key 數量。
- 將指定 Private Key 加入 Agent。
- 有 Passphrase 的 SSH Key 會透過 Git for Windows AskPass 視窗要求輸入密碼。
- Key Manager 啟動的 Agent 連線資訊會保存於本機設定；重新開啟程式後會嘗試重新連回仍在執行的 Agent。
- 可查看、移除、清空 Agent 內的 Key。
- 僅允許停止由 Key Manager 自行啟動的 Agent。

### GPG Key 管理

- 使用 Git for Windows 內建的 GnuPG 環境列出 Secret/Public Key。
- 建立 **RSA 4096** 或 ED25519 GPG Key。
- 預設演算法為 **RSA 4096**。
- GPG Passphrase 完全交由 GnuPG 原生 Pinentry 視窗處理。
- 複製或匯出 ASCII Armor Public Key。
- 刪除 Secret/Public Key。

### Git GPG Signing

啟用「Git GPG 簽章」後，Commit 與 Tag 都會使用指定的完整 GPG Fingerprint 簽章：

```text
gpg.format=openpgp
gpg.program=C:\Program Files\Git\usr\bin\gpg.exe
user.signingkey=<完整 Fingerprint>
commit.gpgsign=true
tag.gpgSign=true
```

### 介面主題

支援淺色與深色模式。主題設定會保存於：

```text
%LOCALAPPDATA%\KeyManager\settings.json
```

重新開啟 Key Manager 後會讀回上次使用的主題。

## 系統需求

Key Manager 以 **Windows 10 / Windows 11** 為主要執行環境。

正式 EXE 使用者需要：

1. **Git for Windows**，預期安裝於 `C:\Program Files\Git`。
2. **Microsoft Edge WebView2 Runtime**。

自行建置另外需要 Python 3.11 以上，建議 Python 3.12。

## 安裝與執行

正式版採單一 EXE：

```text
KeyManager.exe
```

從原始碼執行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
key-manager
```

也可執行：

```text
run_windows.bat
```

## 建置 Windows EXE

在專案根目錄執行：

```text
build_windows_exe.bat
```

1.0.1 正式建置使用 **PyInstaller 單一 EXE**，並停用 UPX。完成後輸出：

```text
dist\KeyManager.exe
dist\KeyManager.exe.sha256
```

SHA-256 檔可用來核對發布後的檔案完整性。

## 使用方法

### 建立 SSH Key

1. 開啟「SSH 金鑰」。
2. 按「建立 SSH 金鑰」。
3. 預設名稱為 `id_rsa`，演算法為 RSA 4096。
4. 可填寫 Email / Comment 與 Passphrase。
5. 建立後可複製或匯出 `.pub` Public Key。

Key Manager 不提供 Private Key 顯示或匯出功能。

### 將 SSH Key 加入 Agent

1. 在 SSH Key 列表按「加入 Agent」。
2. 若 Agent 尚未啟動，Key Manager 會啟動 Git for Windows 的 `ssh-agent.exe`。
3. 若 Private Key 有 Passphrase，由 Git for Windows AskPass GUI 要求輸入。
4. Key Manager 會保存自己啟動的 Agent 連線資訊。重新開啟程式時會先驗證 Agent 是否仍存在，存活時會重新連線；Agent 已退出時舊資訊會自動失效。

### 建立 GPG Key

1. 開啟「GPG 金鑰」。
2. 按「建立 GPG 金鑰」。
3. 輸入 Name 與 Email。
4. 預設演算法為 RSA 4096，也可改用 ED25519。
5. GnuPG 會顯示原生 Pinentry 視窗設定 Passphrase。

Key Manager 不會取得 GPG Passphrase。

### 啟用 Git Commit / Tag GPG Signing

在「Git 設定」填入 `user.name`、`user.email`，選擇完整 GPG Fingerprint 並啟用 Git GPG 簽章即可。

## 安全設計

- UI 不提供 SSH / GPG Private Key 內容顯示。
- UI 不提供 Private Key 匯出。
- SSH Passphrase 不放入外部命令參數。
- SSH Key 加入 Agent 時，Passphrase 由 Git for Windows AskPass 處理。
- GPG Passphrase 由 GnuPG / Pinentry 處理；Key Manager 不讀取、不保存、不轉送。
- Windows 外部 subprocess 使用隱藏 Console 執行。
- Agent 持久化只保存 `SSH_AUTH_SOCK` / `SSH_AGENT_PID`，不保存 Passphrase 或 Private Key。

## Windows Defender 與發布

Key Manager 使用 PyInstaller **單一 EXE** 封裝。未簽章、低下載量或由打包器產生的 Windows 應用程式，有機會被 Microsoft Defender 的機器學習或啟發式偵測誤判。1.0.1 已停用 UPX，以減少額外壓縮特徵，但不能保證完全避免誤判。

若自行建置的 EXE 被偵測為 `Trojan:Win32/Wacatac.C!ml`：

1. 不要直接關閉 Defender 或替整個下載資料夾加入排除。
2. 確認原始碼與建置環境可信並核對 SHA-256。
3. 將檔案提交 Microsoft Security Intelligence 進行誤判分析。
4. 對外正式發布時建議使用 Authenticode Code Signing 憑證簽署 EXE。

## Git for Windows 整合

主要使用：

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

## License / Third-party notices

第三方套件與授權資訊請參閱 `THIRD_PARTY_NOTICES.md`。
