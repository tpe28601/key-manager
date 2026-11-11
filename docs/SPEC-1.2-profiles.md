# Key Manager 1.2.0 規格：資料夾 Git 設定 ＋ Key 使用位置

> 對象：`Dev-Toolbox\tools\Key-Manager\`（現行 1.1.1）。本檔放到 `tools\Key-Manager\docs\SPEC-1.2-profiles.md`。
> 共通規則仍以 `spec\TOOL-SPEC.md` 為準。repo 會公開到 github.com，**任何範例都只能用假名**（`D:/Work/ClientA/`、`alice@example.com`）。

---

## 1. 目標

1. **資料夾 Git 設定（Profile）**：指定某些資料夾底下的所有 repo（包含 submodule）不用全域的 `user.name`、`user.email`、簽章設定、SSH key，改用另一組。
2. **Key 使用位置**：SSH／GPG 列表每把 key 顯示「用在哪裡」（全域、哪些資料夾、`~/.ssh/config` 的哪些 Host），刪除時若仍在使用要警告。

不做：單一 repo 的 `.git/config`（local）編輯、`onbranch:`／`hasconfig:` 條件、自動改寫 repo 內的 remote URL。

---

## 2. 原理（實作者必讀）

使用 Git 內建的條件引入。全域設定檔（`%USERPROFILE%\.gitconfig`）裡加：

```ini
[includeIf "gitdir/i:D:/Work/ClientA/"]
    path = C:/Users/alice/AppData/Local/DevToolbox/key-manager/profiles/client-a.gitconfig
```

`client-a.gitconfig` 內容（Profile 檔）：

```ini
[user]
    name = Alice Chen
    email = alice@client-a.example.com
    signingkey = 0123456789ABCDEF0123456789ABCDEF01234567
[commit]
    gpgsign = true
[tag]
    gpgSign = true
[core]
    sshCommand = ssh -i \"C:/Users/alice/.ssh/id_client_a\" -o IdentitiesOnly=yes
```

已在 Git 2.43 實測確認的行為：

| 情況 | 是否套用 |
|---|---|
| `D:/Work/ClientA/` 底下的 repo | ✅ |
| 上面 repo 的 submodule（gitdir 在 `<主repo>/.git/modules/…`） | ✅ |
| 主 repo 在資料夾內，worktree 開在資料夾外 | ✅（gitdir 在主 repo 的 `.git/worktrees/…`） |
| 主 repo 在資料夾外，worktree 開在資料夾內 | ❌ 不套用 |
| 資料夾本身不是 git repo、也不在 repo 內 | ❌（只有 git 指令在 repo 內執行才生效） |

規則：

- 條件一律寫 `gitdir/i:`（Windows 不分大小寫），路徑用 `/`，**結尾一定要 `/`**（代表底下全部）。
- includeIf 的值會蓋過**檔案中位置在它前面**的全域值；repo 自己的 `.git/config` 仍會蓋過它。若全域檔裡在 includeIf 區段**之後**又設了同一個 key，Profile 會被蓋掉 → 要偵測並警告（見 4.4）。
- 寫入一律呼叫 git CLI，不要自己改 ini 文字，才能保留使用者原本的註解與排版：
  - 新增：`git config --global "includeIf.gitdir/i:D:/Work/ClientA/.path" "<profile 路徑>"`
  - 移除：`git config --global --unset "includeIf.gitdir/i:D:/Work/ClientA/.path" "<profile 路徑，用正規式跳脫>"`，區段空了再 `--remove-section`。
  - 讀取：`git config --global --get-regexp "^includeif\."`（區段名會變小寫，**子區段大小寫保留**）。
  - Profile 檔：`git config --file <profile> user.email ...`、`--unset`。
- 全域檔路徑：`GIT_CONFIG_GLOBAL` 環境變數優先，否則 `%USERPROFILE%\.gitconfig`。（測試時用 `GIT_CONFIG_GLOBAL` 指到暫存檔，不碰真的設定。）

---

## 3. 資料

### 3.1 Profile 種類

| 種類 | Profile 檔位置 | 說明 |
|---|---|---|
| managed | `%LOCALAPPDATA%\DevToolbox\key-manager\profiles\<id>.gitconfig` | Key Manager 建立 |
| external | 全域檔裡使用者手寫的 includeIf 所指向的任何檔案 | 照樣列出、**可以編輯**；第一次編輯前提醒「這是你手動建立的檔案」 |

`gitdir:`（無 `/i`）與 `gitdir/i:` 都要讀得懂；其他條件（`onbranch:` 等）列出但唯讀，標「不支援的條件」。

### 3.2 `profiles.json`（只存顯示用資訊）

`%LOCALAPPDATA%\DevToolbox\key-manager\profiles.json`：

```json
{ "version": 1, "profiles": { "client-a": { "name": "客戶 A", "note": "" } } }
```

**資料夾清單不存這裡**，一律以全域 `.gitconfig` 裡的 includeIf 為準（避免兩邊不一致）。一個 Profile 可對應多個資料夾。

### 3.3 Profile 欄位

每個欄位都有「沿用全域」（＝ Profile 檔裡沒有這個 key）。

| 欄位 | git key | 說明 |
|---|---|---|
| 名稱 | `user.name` | |
| Email | `user.email` | 需含 `@` |
| 簽章 Key | `user.signingkey` | 從 GPG 列表選，存完整 fingerprint |
| Commit 簽章 | `commit.gpgsign` | 三態：沿用全域／開／關 |
| Tag 簽章 | `tag.gpgSign` | 三態 |
| SSH Key | `core.sshCommand` | 從 SSH 列表選；產生 `ssh -i "<private key 路徑，/ 分隔>" -o IdentitiesOnly=yes` |

`core.sshCommand` 若不是 Key Manager 產生的格式（例如使用者自己寫了 `-F`），顯示原文、標「自訂指令」，不要覆寫，除非使用者明確選了新的 key。

### 3.4 備份

每次寫入全域 `.gitconfig` 或 external Profile 檔之前，先複製到 `%LOCALAPPDATA%\DevToolbox\key-manager\backups\<檔名>.<yyyyMMdd-HHmmss>`，每個檔案保留最近 20 份。介面上有「開啟備份資料夾」。

---

## 4. 功能

### 4.1 Profile 管理（Git 設定頁的新區塊「資料夾設定」）

- 卡片列表：Profile 名稱、資料夾 chips、各欄位摘要（沿用全域的欄位顯示灰字「全域」）、種類標籤（managed／external）。
- 新增／編輯對話框：名稱、欄位（3.3）、資料夾清單（新增／移除）。
- 選資料夾：桌面版用 pywebview 資料夾對話框；Web 版用已經做好的瀏覽器資料夾選擇器（`browse_directories`，同 SSH 路徑選擇）。也可直接貼路徑。
- 路徑正規化：轉 `/`、補結尾 `/`、去掉重複的 `/`；不存在的資料夾允許但顯示警告。
- 刪除 Profile：移除所有對應的 includeIf；managed 的 Profile 檔移到 backups（不直接刪）；external 只移除 includeIf，不動檔案。

### 4.2 衝突與提醒

- 同一個資料夾已經在別的 Profile → 拒絕，請使用者先移除。
- 巢狀資料夾（`D:/Work/` 和 `D:/Work/ClientA/` 分屬不同 Profile）→ 允許，但顯示警告「兩個都會套用，全域檔中位置較後面的那個優先」，並顯示目前誰優先。
- 4.4 檢查到被全域蓋掉的值 → 卡片上顯示警告。

### 4.3 檢查實際生效值

對話框：選一個資料夾（通常是某個 repo 或 submodule），執行
`git -C <資料夾> config --show-origin --show-scope --get <key>`（每個 key 一次），顯示表格：key、值、來源檔、scope。
- 資料夾不是 git repo → 顯示「這裡不是 git repo，設定只會在 repo 內生效」。
- 是 worktree 且主 repo 不在任何 Profile 資料夾內 → 顯示 2 節表格最後一列的說明。

### 4.4 被全域蓋掉的偵測

讀 `git config --global --no-includes --list`（不展開 include，輸出順序＝檔案中的順序，includeIf 本身也會以 `includeif.<條件>.path=...` 出現在對應位置）。對每個 Profile 的 key，若在全域檔中該 includeIf 那一行之後還出現同 key → 標記。提供「修正」按鈕：把該 includeIf 區段移到檔案最後（先 `--unset` 再重新新增，新增的區段會在檔尾）。

### 4.5 Key 使用位置

SSH 和 GPG 列表新增「使用位置」欄，點開顯示明細：

**SSH key**（以 private key 路徑比對，大小寫不分、`\` 與 `/` 視為相同、展開 `~`）：
- 全域 `core.sshCommand` 用到 → 「全域」
- Profile 的 `core.sshCommand` 用到 → 每個資料夾一筆
- `~/.ssh/config`（及 SSH 路徑設定裡的 `config`）中 `IdentityFile` 指到 → 「SSH Host：<Host>（<HostName>）」
  - 解析範圍：`Host`、`HostName`、`IdentityFile`；支援 `~` 與 `%d`；`Include` 讀一層，讀不到就顯示「有 Include 未解析」；`Match` 區塊略過並標示。

**GPG key**（比對完整 fingerprint，或 `user.signingkey` 存的是 16／8 碼 key id 時比對結尾）：
- 全域 `user.signingkey` → 「全域」
- Profile 的 `user.signingkey` → 每個資料夾一筆

**刪除警告**：刪 key 前若有任何使用位置，確認框列出全部位置（取代現在只檢查全域簽章的警告）。

### 4.6 總覽頁

新增一張卡片「資料夾設定」：Profile 數、資料夾數、有警告的數量，點擊跳到 Git 設定頁。

---

## 5. 程式結構

| 檔案 | 內容 |
|---|---|
| `src/key_manager/git/profiles.py`（新） | 讀寫 includeIf、Profile 檔、profiles.json、備份、正規化、衝突／覆蓋偵測、生效值檢查 |
| `src/key_manager/ssh/sshconfig.py`（新） | `~/.ssh/config` 解析（4.5 範圍） |
| `src/key_manager/usage.py`（新） | 組合出每把 SSH／GPG key 的使用位置 |
| `src/key_manager/web/api_beta3.py` | 新 API 方法（見下），沿用 `_ok`／`_error` 回傳格式 |
| `static/index.html`、`app.js`、`app.css` | Git 頁新區塊、對話框、使用位置欄 |
| `tests/test_profiles.py`、`test_sshconfig.py`、`test_usage.py`（新） | |

API 方法（server.py 的 `build_api_map` 會自動公開 public 方法，不必改 server.py）：

- `list_git_profiles()` → `{profiles:[{id, kind, name, path, folders:[{folder, condition, overridden_keys:[]}], fields:{...}, warnings:[]}], global_path}`
- `save_git_profile(profile)`（新增或更新，含資料夾清單）
- `delete_git_profile(id)`
- `check_effective_git_config(folder)`
- `fix_profile_order(id)`
- `get_key_usage()` → `{ssh:{<key name>:[...]}, gpg:{<fingerprint>:[...]}}`
- `open_backup_folder()`（Web 版回傳路徑讓前端顯示即可）

`get_*` 不寫檔；所有寫入的 API 都要先做備份。

---

## 6. 驗收

- 用 `GIT_CONFIG_GLOBAL` 指到暫存檔，自動測試涵蓋：新增／修改／刪除 Profile、多資料夾、巢狀警告、同資料夾拒絕、被全域蓋掉偵測與修正、external Profile 讀取、備份數量上限。
- 真的 git 測試：在暫存資料夾建立主 repo＋submodule＋worktree，確認 4.3 的結果與第 2 節表格一致。
- `sshconfig.py` 測 `Host` 多個別名、`~`、`Include`、`Match`。
- 使用者原本 `.gitconfig` 的註解在操作後仍然存在。
- 現有測試全部通過（已知 6 個與本次無關的失敗除外：打包腳本相關 4 個、`test_ssh_agent` 2 個）。
- 版本改 1.2.0（`metadata.py`、`tool.json`、CHANGELOG）。
