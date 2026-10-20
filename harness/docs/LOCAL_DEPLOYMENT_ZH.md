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

## 六、Ultron 品牌与 OpenAI 模型（验收分支）

**适用分支：** `feature/ultron-branding-openai`。当前只是分支提交，未经用户验收不会创建 PR/MR，更不会改动线上 Render 服务。

### 1. 获取代码

```bash
cd ~/Downloads/ultron-web
git fetch origin
git switch feature/ultron-branding-openai
git pull --ff-only origin feature/ultron-branding-openai
cd harness
```

如果项目不在上述目录，请换成自己的路径。如果本地存在未提交修改，先保存或提交，避免切换分支冲突。

### 2. 配置 ChatGPT AI（实际使用 OpenAI API）

```bash
bash configure-openai.sh
```

如果提示新建了 `$DSH_HOME/profiles/web/cordis.patch.yml`，说明新注册了名称为 **ChatGPT AI** 的 OpenAI Provider（未写入密钥）。如果提示 `Existing dsh profile detected`，说明本地已有自定义配置，**为保护已有数据脚本不会覆盖它**；直接到运行中的 dsh 页面 **Settings → Models → Add model provider → Third-party → openai**，输入 OpenAI Platform 的 API Key，保存并选择 `gpt-4.1-mini` 等支持的模型。用户此前 Render 的 API Key 不会自动迁移到本地 dsh。

不要把 API Key 粘贴进 Git 文件。ChatGPT Plus 订阅不等于 OpenAI API 余额。

### 3. 在 Chrome 加载 Ultron 品牌

浏览器打开 `chrome://extensions`，启用右上角“开发者模式”，点击“加载已解压的扩展程序”，选中仓库中 `harness/branding/chrome-extension` 文件夹。刷新本机 `http://127.0.0.1:3080` 页面：标签页标题将尝试改为 Ultron、网页 favicon 切换为原创 Ultron 图标，顶部品牌文案与图标根据当前 DOM 调整。若上游页面更改，可能退化成左下角 Ultron 标记。这是**本地浏览器呈现层覆盖**，不修改官方 npm 包的源代码；其他浏览器不会同步更改。

### 4. 启动与验收

```bash
bash start-local.sh
```

在 Chrome 中验收：① 标签标题不显示 DeepSeek Harness；② Ultron 图标出现；③ Settings → Models 里有 OpenAI 提供方（新 Profile 应显示 ChatGPT AI，已有 Profile 按第 2 步手动配置）；④ 选择模型后完成一条真正的 Agent 对话，并在 OpenAI Platform 查看 API 用量。如果失败，不要把 API Key 或认证 URL 发给他人。

### 5. 回退

- 视觉：在 `chrome://extensions` 里停用“Ultron Local Branding”并刷新网页。
- 模型：在 dsh Settings → Models 删除或修改 OpenAI Provider。只在明确了解原配置情况下才手工处理 `$DSH_HOME/profiles/web/cordis.patch.yml`；不要删除 `.credentials.yaml` 中其他已有密钥。
- 代码：`git switch main`。切换代码分支不会自动清除本地 dsh 配置、会话或凭据。

> 安全：浏览器扩展只在 localhost / 127.0.0.1 的 3080 端口执行 UI 逻辑；Harness 不得未经认证公开到互联网。这里的 Logo 是原创机器人元素，不使用电影版 Ultron 官方素材。


## 七、OpenAI API 直连超时，系统代理可以访问（7890）

**已确认的案例**：`curl https://api.openai.com/v1/models` 连接超时；`curl --proxy http://127.0.0.1:7890 https://api.openai.com/v1/models` 返回 HTTP 401。这说明代理通道到达 OpenAI，401 是因为诊断请求没有带 API Key，不是网络错误。

最新 `start-local.sh` 在 macOS 上会检查系统 HTTPS 代理；仅在未手动指定 HTTPS_PROXY/ALL_PROXY，且系统代理目标为 `127.0.0.1` 或 `localhost`、端口在监听时，才把它转成 `HTTP_PROXY` 与 `HTTPS_PROXY` 供官方 dsh 使用。**不会修改 macOS 网络设置或 Git 中的凭据。**

### 拉取并重启

```bash
cd ~/Downloads/ultron-web
git switch feature/ultron-branding-openai
git pull --ff-only origin feature/ultron-branding-openai
cd harness
# 在运行 dsh 的旧终端 Ctrl+C 停止，再执行：
bash start-local.sh
```

期望日志显示：`[Ultron] Using macOS local HTTP proxy for dsh: 127.0.0.1:7890`。保持终端运行；浏览器打开 `http://127.0.0.1:3080`，选择 OpenAI 模型，新建 Session 发送一条简短测试消息。

### 单次手动指定 / 不使用自动代理

```bash
HTTPS_PROXY=http://127.0.0.1:7890 HTTP_PROXY=http://127.0.0.1:7890 bash start-local.sh
# 不检测 macOS 系统代理：
ULTRON_PROXY_AUTO=0 bash start-local.sh
```

若自动检测没有识别到代理，用第一条手动命令。**不要在终端输出或仓库中粘贴 API Key。**

### 验收

1. 终端显示代理已配置（或已自动检测 7890）；
2. dsh 能打开本地 Web UI；
3. Settings → Models 显示 OpenAI provider，选择实际可用模型；
4. 新建 Session 请求 `Reply exactly OK`，得到模型响应；
5. 如收到 `401 invalid_api_key`、`429 insufficient_quota`，说明请求已经进入 API 认证/计费阶段，需要分别检查 Key 或余额。只有获得真实回复才算端到端验收。

官方参考：https://deepseek-harness.github.io/deepseek-harness/en/guide/network-proxy

说明：代理支持由 dsh 的实际安装版本决定。若设置后仍不能连接，先检查启动日志及该版本的代理支持；不要通过关闭 TLS 证书验证来“解决”。
