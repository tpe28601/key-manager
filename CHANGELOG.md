# Changelog — Key Manager

## v1.2.4

- 提供適用於已備妥 Python 及相依套件的輕量 ZIP，可由 Dev-Toolbox Hub 0.4.3 安裝。

## v1.2.2 (2026-11-13)

- 「開啟備份資料夾」升級為「備份與還原…」：彈窗直接列出最近備份（每個檔案各保留 20 份、由新到舊），
  顯示建立時間、大小與還原目標（全域 `.gitconfig` 或某 Profile 設定檔）；點選任何備份可立即
  預覽內容，確認後一鍵還原；還原前會先把「目前檔案」自動備份一份，反悔可在同一清單還原回去
- 備份的原檔已不存在、或屬於外部 `includeIf` 設定檔時標示為「未知目標」，僅供預覽，
  仍可按「開啟資料夾」手動複製
- 「檢查實際生效值」彈窗版面調整：路徑輸入、瀏覽、檢查整合為同一列；檢查前不再為結果表格
  預留大片空白（緊湊寬度開啟，查出結果才展開成寬表格），每次開啟都會清掉上次的提示與結果

## v1.2.1 (2026-11-13)

- 「資料夾設定（Profiles）」從「Git 設定」頁獨立為側欄單獨一欄：新分頁「資料夾設定」
  承接 Profiles 清單與工具列；總覽的「資料夾設定」狀態卡改往新分頁；「Git 設定」頁
  保留 Identity 與 Signing 兩區塊
- 修正 Web 版彈窗內按「瀏覽…」後資料夾挑選層在彈窗背後、且整個畫面無法操作的問題：
  `showModal()` 的 `<dialog>` 繪於 top layer 並讓畫面其餘部分失效（inert），改為把
  挑選器掛入彈窗內（與 toast 相同的 top-layer 做法），挑選期間 Esc 只關挑選器不關彈窗

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
