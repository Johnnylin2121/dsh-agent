# push-guard — Git push 隐私泄露防护（Windows / macOS 通用）

pre-push hook + 扫描引擎：push 前自动扫描待推送内容，拦截 API key/token、
持仓交易记录、本机路径、ASIN、手机号/身份证等敏感信息。

**组件**：

| 文件 | 说明 |
|------|------|
| `pre-push` | git hook，从 stdin 读待推送 ref，调用扫描引擎 |
| `push-scan.ps1` | 扫描引擎：gitleaks（可选）+ 9 条中文场景正则 |

**拦截规则**：价格+动作组合（`X.XXX 入场`）、股票代码×持仓语境、含用户名的本机绝对路径、
OneDrive/Obsidian 真实路径、ASIN、手机号、身份证、资金数字、常见 key 格式回退（sk-/ghp_/AKIA/ntn_/私钥块/雪球cookie）。

---

## 安装

### macOS

```bash
# 1. 依赖（rg 必装；pwsh 必装否则 hook 放行+警告；gitleaks 可选增强）
brew install ripgrep gitleaks
brew install --cask powershell

# 2. 安装 hook 到 ~/.dsh/git-hooks（从本仓库根执行）
mkdir -p ~/.dsh/git-hooks
cp push-guard/pre-push push-guard/push-scan.ps1 ~/.dsh/git-hooks/

# 3. 全局启用（对所有仓库生效, 含未来新 clone）
git config --global core.hooksPath "$HOME/.dsh/git-hooks"

# 4. 验证（随便找个仓库跑全历史扫描）
pwsh -NoProfile -File ~/.dsh/git-hooks/push-scan.ps1 -Full
```

### Windows

```powershell
# 依赖: winget install gitleaks.gitleaks  (rg/pwsh DSH 环境自带)
New-Item -ItemType Directory -Force "$HOME\.dsh\git-hooks" | Out-Null
Copy-Item push-guard\pre-push, push-guard\push-scan.ps1 "$HOME\.dsh\git-hooks\"
git config --global core.hooksPath "$HOME/.dsh/git-hooks"
pwsh -NoProfile -File "$HOME\.dsh\git-hooks\push-scan.ps1" -Full
```

---

## 日常使用

- 手动全历史深扫：`pwsh -NoProfile -File ~/.dsh/git-hooks/push-scan.ps1 -Full`
- 误报白名单：仓库根建 `.pushscan-allow`，每行一条正则（finding 行命中即放行）
- 私有仓库整体跳过：`git config pushscan.skip true`
- 紧急跳过：`git push --no-verify`（人工确认后使用）
- 引擎缺失时 hook **放行并警告**（fail-open）；要改严格模式，编辑 pre-push 把
  WARNING 分支的 `exit 0` 改为 `exit 1`

## 已知限制

- DSH 沙箱会话内 msys sh 无法启动，`git push` 会 fail-closed 报错——正式推送在普通终端执行
- hook 只扫增量提交；已在历史中的内容不受影响（需 git filter-repo 重写）
- gitleaks 未安装时仅靠正则，key 格式覆盖弱一档
