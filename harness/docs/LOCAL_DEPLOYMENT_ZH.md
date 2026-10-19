# Ultron Agent V0.5 本地部署手册（macOS）

**目标**：使用官方 DeepSeek Harness (dsh) Agent Loop + OpenAI API；不是 DeepSeek API，也不是旧的 FastAPI 聊天界面。

## 一、准备环境

需要 Node.js **22.19+ 或 24+**、npm、Git、能访问 npm Registry 和 api.openai.com 的网络。Mac 终端执行：

```bash
node -v
npm -v
npm view @deepseek-ai/dsh version
```

如版本低于要求，使用 nodejs.org 官方 macOS 安装器升级。若 npm 报 EAI_AGAIN / ENOTFOUND，先修复网络或 DNS。

## 二、下载与启动

```bash
git clone --branch migration/deepseek-harness https://github.com/niehmanyo/ultronai.git
cd ultronai/harness
export DSH_HOME="$HOME/.ultron-dsh"
mkdir -p "$DSH_HOME"
chmod 700 "$DSH_HOME"
./start-local.sh
```

终端会打印 dsh 的认证地址，通常使用 127.0.0.1:3080，**以终端输出的完整 URL 为准，不要泄露 token**。停止服务按 Ctrl+C。

**版本固定**：运行 `npm view @deepseek-ai/dsh version` 查询确切发布版本后，建议使用完整版本号安装并锁定依赖。不可假定仓库源码里的版本已发到 npm。

## 三、配置 ChatGPT 所属的 OpenAI API

打开 dsh Web UI，进入 **Settings → Models → Add model provider → Third-party → openai**，输入 OpenAI Platform API Key，保存，然后选择可用的 OpenAI 模型。ChatGPT Plus 与 API 是不同的计费系统，无须设置 DeepSeek Key。

进入 **Choose workspace**，选择 `harness/ultron-workspace` 的完整路径；新建 Session。Skills 位于隐藏目录 `.dsh/skills/`。

## 四、Agent 验收

1. **读取**：「读取 AGENTS.md，并列出你实际调用过的工具」；确认工具调用事件可见。
2. **执行**：「在当前工作区创建 test-report.md，写一段内容后重新读取验证；需要授权先询问」。检查真实文件与审批记录。
3. **重启**：停止 dsh，再次启动，检查 Session 和工具轨迹是否保留。
4. **记忆**：「提议记住一条偏好，但不要保存，直到我明确批准」。检查 `memory/approved.md` 未被擅自修改。
5. **安全**：不得把整个 Home 当作 Workspace，不授予不必要的危险命令权限。

## 五、重要限制

此分支只做本地 Agent Harness 验收，不修改线上 Render。官方 UI 尚未集成 Hello Stark 音频；旧版 PostgreSQL 历史不能直接作为 dsh Session Event 导入；当前 Memory 是需要确认的文件记忆，并非自动检索系统。

不要暴露 dsh 端口到公网，不要上传 `DSH_HOME`、API Key、登录链接或包含私人聊天的日志。独立沙箱、身份认证、持久化备份、成本限制完成之前不做公网部署。

完整版脚本、离线验证和排障章节见随项目交付的 `ultron-harness-v05.zip` 中 `docs/LOCAL_DEPLOYMENT_ZH.md`。

官方安装：https://github.com/deepseek-ai/deepseek-harness#run

OpenAI 模型配置：https://deepseek-harness.github.io/deepseek-harness/en/guide/providers


## 六、3080 拒绝连接且 npx 静默退出

如果 `curl --noproxy '*' http://127.0.0.1:3080/` 返回 Connection refused，而 `npx --yes @deepseek-ai/dsh web --no-open` 什么也不显示就结束，说明 Web 服务未保持运行。不要优先修改 Chrome 代理或关闭防火墙。

更新本分支后运行：

```bash
cd ultronai/harness
bash start-local.sh
```

新版启动器会检查 Node.js 版本，显示 npm/npx 版本，将启动输出记录在 `~/.ultron-dsh/logs/`，并且在 dsh 意外退出后给出诊断命令（不能再把静默退出误认为启动成功）。**注意：此改动提高诊断能力，不代表已经确认并修复 dsh 的实际退出根因。**

如果仍静默退出，在本机执行：

```bash
node -v
npm view @deepseek-ai/dsh version engines bin --json
npm config get registry
npm cache ls @deepseek-ai/dsh
```

然后检查 `~/.npm/_logs/` 下最新 debug 日志。不要上传含 API Key、认证 token 或本机隐私信息的日志。请先检查 Node 是否为 22.19+ 或 24+，再诊断 package 缓存/安装。只有确认 3080 确实被占用时才改端口。
