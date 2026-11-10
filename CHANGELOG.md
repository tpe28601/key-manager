# Changelog — Key Manager

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
