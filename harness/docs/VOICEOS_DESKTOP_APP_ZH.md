# Ultron VoiceOS · macOS 桌面小助手 V0.1

## 你现在可以得到什么

一次性通过构建脚本在 `~/Applications/Ultron VoiceOS.app` 安装原生 macOS 应用。之后直接在 Finder、Launchpad（视 macOS 索引而定）或 Dock 双击打开，无需终端运行 VoiceOS。

- 原生 Cocoa 窗口（默认 560×640，可调整大小）内嵌 WKWebView，直接显示现有 5750 点云的 3D Cognitive Cortex；无需再打开浏览器。
- Dock 图标与菜单栏 `◇ ULTRON` 常驻菜单，可打开窗口、Restart Agent、Pause Microphone、API Key Settings、Quit。
- 保留 DeepSeek Harness SDK Agent、OpenAI 语音识别、GLACIAL 英文语音、自动 VAD 免回车、3D 音量联动和真实工具调用节点。
- 首次启动在原生密码框输入 OpenAI Platform API Key，保存到 macOS Keychain；**不写入 `.app`、仓库、命令行参数或磁盘日志**。
- Finder 启动时自动设置 Python 进程所需的工作目录、用户级 PATH 与 API Key；使用已有 Python venv，关闭/暂停会向 Python 进程发送 SIGINT 使其有机会安全清理。
- UI 的本地 WebKit 只能导航到当前 `127.0.0.1` 的 VoiceOS 端口，禁止进入外部网址。
- **不包含 Kokoro**。这条功能分支是从 `feature/voiceos-neural-dense-ui` 派生的，不需要卡住的 Kokoro 模型安装。

## 第一次安装：只需要这一次打开终端

安装的前提是你此前已经在 Mac 上成功运行过 `harness/voiceos/core.py`（相同本地 Python venv、DSH SDK、已建立的 SDK 模型配置）。在终端执行：

```bash
cd ~/Downloads/ultron-web
git fetch origin
git switch feature/voiceos-desktop-assistant
git pull --ff-only origin feature/voiceos-desktop-assistant
cd harness
source .venv-voiceos312/bin/activate
python -m unittest discover -s voiceos/tests -v
bash desktop/build-macos-app.sh
```

脚本使用 macOS 自带/已安装的 `swiftc` 编译 Swift AppKit + WebKit 程序，临时文件构建成功后才安装至 `~/Applications`，本地 ad-hoc 签名，不会发布到 App Store。若缺少编译器，请先安装 `xcode-select --install`。**不需要 `npm` 或 `pyinstaller` 打包前端。**

脚本末尾会尝试自动打开 `.app`。以后可从 Finder `~/Applications` 双击启动，也可将应用拖到 Dock。

## 第一次打开时

1. 输入原先用于 DSH 和 ASR 的 OpenAI Platform API Key（请勿在聊天中粘贴）。
2. 允许 macOS 对 Python/Ultron 提示的麦克风权限。某些系统会把授权标注给底层 Python 解释器，因为音频采集发生在其子进程中。
3. 启动后显示 `ULTRON · Cognitive Cortex` 原生窗口。待 `[VoiceOS] Cognitive dashboard:` 本地服务器准备好，会自动加载 3D 神经核心。**无需额外浏览器，也无需按回车对话。**
4. 关闭窗口不等于停止监听：应用仍驻留菜单栏。可点击菜单栏 `◇ ULTRON → Pause Microphone` 停止语音，再用 `Restart Agent` 恢复；或 `Quit Ultron` 完全退出。

## 注意事项

- 这是**针对用户当前 Mac 的开发式安装包**，不是脱离仓库/虚拟环境即可运行的独立分发版。不要移动或删除 `~/Downloads/ultron-web`，尤其不要删除 `harness/.venv-voiceos312`；若移动路径，重跑构建脚本。
- 在 Finder 启动后不会继承你在 `.zshrc` 里定义的环境变量，因此 APP 通过 Keychain 安全获取 OPENAI_API_KEY；其它网络参数使用现有 VoiceOS 的系统回环代理检测。如果你此前只依靠特殊 shell 代理环境变量，则需使用 macOS 系统代理或单独添加桌面网络设置。
- `.app` 目前是本地 ad-hoc 签名，未经 Apple Developer ID 公证签名；不要把这个包当作通用可分发安装包。
- Keychain 保存凭据，但本地 `.app` 和 Python 进程仍拥有解密后在内存中使用它的权限；因此仅适合你的受信任设备。
- 用户完整语音内容和 Agent 回复不会主动落盘日志；原网页的最后回复仍会显示在应用窗口中。不要对外公开 127.0.0.1 的服务。
- DSH SDK 可能启动其他子进程；停止时先向 Python 发送 SIGINT，允许清理，之后再强制终止 Python。子进程清理需在你 Mac 的 SDK 环境中确认。
- 打开 Dock/菜单栏 UI 不会改变 Agent 准确率；GLACIAL TTS 仍按原云端接口调用，且会产生原来的 API 费用。

## 本地排障

可以先检查旧的 VoiceOS 是否正常：

```bash
cd ~/Downloads/ultron-web/harness
source .venv-voiceos312/bin/activate
python voiceos/core.py --doctor
```

如果看到 Swift 编译失败、窗口无法加载、权限拒绝或语音无法播放，可检查终端中的构建错误或 VoiceOS 原进程日志，不要上传 API Key。

## 安全验收

- 能从 Finder 双击 `Ultron VoiceOS.app` 打开独立窗口，且没有 Terminal 窗口被启动。
- API Key 首次设置后重启仍可用，设置中可修改；Finder 和 Dock 不会把 Key 打印在命令行中。
- 3D 核心、GLACIAL 语音、VAD 与工具网络与旧终端模式相同。
- 使用菜单栏 Pause Microphone 后实际进程停止；Quit 后不继续监听。
- macOS 14+、Python 3.12 / DSH SDK 的实机编译与测试目前**尚未运行**；提交成功不能冒充安装已经验证。

## GitHub

- Dense UI 的 PR 为 #6，目标分支 `feature/voiceos-agent-graph`。
- 桌面应用独立在 `feature/voiceos-desktop-assistant`，**没有修改 main、合并 PR 或部署**。