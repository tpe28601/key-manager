# Changelog — Key Manager

## v1.2.1 (2026-11-13)

- 「資料夾設定（Profiles）」從「Git 設定」頁獨立為側欄單獨一欄：新分頁「資料夾設定」
  承接 Profiles 清單與工具列；總覽的「資料夾設定」狀態卡改往新分頁；「Git 設定」頁
  保留 Identity 與 Signing 兩區塊
- 修正 Web 版彈窗內按「瀏覽…」時資料夾挑選層在彈窗**背後**的問題：`showModal()` 的
  `<dialog>` 繪於 top layer（任何 z-index 都壓不過），改為挑選期間暫時隱藏開啟中的
  彈窗（並暫停其 Esc-cancel 防止誤關）、選完立即恢復，表單內容不受影響

## v1.2.0 (2026-11-11)

- 新增「資料夾 Git 設定（Profiles）」：用全域 `includeIf.gitdir/i:` 依資料夾切換 user.name／user.email／
  signingkey／commit.gpgsign／tag.gpgSign／core.sshCommand；每個欄位可選「沿用全域」，SSH Key 可從清單選或貼自訂指令
- 所有 `.gitconfig` 讀寫一律透過 git 指令（`git config --global/--file/--get-regexp -z`），保留使用者註解與排版；
  寫入前自動備份全域檔與 Profile 檔到 `backups/`（保留 20 份，介面可一鍵開啟）
- 偵測並警示：Profile 設定被後寫的全域值蓋掉（提供「修正順序」一鍵把 includeIf 移到檔案最後）、
  巢狀資料夾重疊與優先序、資料夾不存在、Profile 檔遺失；手寫 `includeIf` 指向的外部設定檔會被辨識為
  「外部檔案」可直接編輯（刪除時只移 includeIf 行，不動檔案）；不支援的條件（如 `onbranch:`）唯讀呈現
- 新增「檢查實際生效值」：在指定資料夾跑 `git config --show-origin --show-scope --get`，列出六項設定的
  生效值、層級與來源檔案，並提示 worktree 的 `gitdir/i` 限制（主 repo 在 Profile 資料夾外的 worktree 不會套用）
- SSH／GPG 列表新增「使用位置」欄位（全域／資料夾 Profile／`~/.ssh/config` Host），刪除金鑰前確認對話框會列出全部引用位置
- 總覽新增「資料夾設定」狀態卡；SSH／GPG 頁、Git 頁與預覽模式（mock）同步支援

## v1.1.1 (2026-11-10)

- 導入 Dev-Toolbox 設計系統：Web 模式承載 `ui-kit.css`（`uiKitTarget` 指向 `src/key_manager/web/static`，
  由 Dev-Toolbox `Sync-UiKit.ps1` 同步），連結於 `app.css` 之前

## v1.1.0 (2026-11-10)

- 新增 Dev-Toolbox Web 模式（`web_server.py`，純標準函式庫 HTTP，僅綁 127.0.0.1、預設 port 8730）：
  `tool.json`、READY 行、`--parent-pid` 跟隨 Hub 結束、`--data-dir` 與
  `%LOCALAPPDATA%\DevToolbox\key-manager`（首次自動複製舊 `%LOCALAPPDATA%\KeyManager\settings.json`）、
  `GET /api/health`、`GET /api/info`、Host／Origin／`X-Toolbox-Request`／Content-Type 檢查與安全標頭
- 前端以 `web-adapter.js` 橋接既有 pywebview API（app.js／beta3.js 不改），並支援 Hub 傳入的
  `?theme=`／`?embedded=`（嵌入時隱藏工具自己的頂部列）
- 沒有 `cryptography` 環境時，產生 SSH Key 自動退回呼叫本機 `ssh-keygen`（桌面版行為不變）
- pywebview 桌面模式與 EXE 打包完全不受影響

## v1.0.2

- 版本與打包修正

## v1.0.1 / v1.0.0

- 初版：pywebview 桌面應用，SSH／GPG 金鑰與 Git 簽章管理
