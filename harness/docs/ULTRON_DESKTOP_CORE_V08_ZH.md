# Ultron Desktop Core V0.8 — macOS 安装与验收

## 本版功能

- 原生透明悬浮面板，内含 900 个 WebGL 3D 点；点击展开原有 5,750 点的大型 Neural Cortex。
- 全局快捷键 Option + Space 显示或隐藏主窗口，不需要 macOS 辅助功能权限；快捷键冲突时可继续通过 Dock / 菜单栏操作。
- 默认麦克风 OFF，只有明确选择 Start Listening 才启动 VoiceOS 和持续语音采集。
- Pause Microphone 停止 Python 语音进程；Restart Agent 先清理旧进程再启动新进程。
- 后台进程启动 45 秒仍未创建 HTTP Dashboard 时超时退出并显示状态。
- Dock 重新打开关闭过的窗口，主窗口置顶开关、悬浮球显示开关；原 GLACIAL / DSH / 工具图谱不变。
- 不安装 Kokoro、不自动开麦、不修改 main。

## 代码级验收说明

已审查原生桌面封装，重点修复默认开麦、没有全局快捷键、启动挂起无反馈、重启旧进程尚未退出、关闭窗口和麦克风状态不明确等问题。Orb.html 内联 JavaScript 已过语法检查，新增 Python 静态测试覆盖要求。但当前执行环境不是 macOS，无法运行 Swift 编译、WebKit 和麦克风实机验收，不能将代码提交当作已安装成功。

## 安装

先从菜单栏 Quit 退出之前的 Ultron App（仅关闭主窗口并不会退出），再运行：

```bash
cd ~/Downloads/ultron-web
git fetch origin
git switch feature/ultron-desktop-core-v08
git pull --ff-only origin feature/ultron-desktop-core-v08
cd harness
source .venv-voiceos312/bin/activate
python -m unittest discover -s voiceos/tests -v
python -m unittest discover -s desktop/tests -v
bash desktop/build-macos-app.sh
```

如果缺少 Swift 编译器，在 Mac 执行 xcode-select --install。安装完成后 Finder 打开 ~/Applications/Ultron VoiceOS.app，或者拖进 Dock。应用为本地编译、ad-hoc 签名，依然需要项目目录和原 Python 虚拟环境，不能直接在其他电脑分发。

## 使用

1. 双击应用：主窗口及悬浮球可见，麦克风保持 OFF。
2. 点击菜单栏 Start Listening：必要时在原生 Keychain 密码框填写 OpenAI API Key，并允许麦克风权限。
3. GLACIAL 开始免回车对话；主窗口展示原有 3D 语音振幅联动。
4. Option + Space 收起或展开主窗口；也可以点击悬浮核心展开。
5. Pause Microphone 可关闭持续录音；重启会先停止旧进程再启动新进程。
6. Toggle Mini Orb 隐藏/显示悬浮球；Toggle Always on Top 控制主窗口置顶。
7. Quit Ultron 完全退出应用。

## Mac 验收清单

- Swift 构建成功，Finder 双击可以启动。
- 应用首次打开不访问麦克风，不自动开始监听。
- Start Listening 后授权成功，语音和 DSH SDK 正常运行。
- Option + Space 正确切换窗口；无热键权限弹窗。
- 悬浮核心点阵绘制正常，可移动、单击展开。
- GLACIAL 播报和完整 3D 音频联动继续正常。
- Pause、Restart、Quit 后无重叠或遗留 Python 监听进程。
- 配错 SDK 或遇到启动卡顿后能看到超时状态，而不是无限假在线。

## 限制

- 仍不支持播报中途打断、系统唤醒词或屏幕感知。
- 悬浮球根据 VoiceOS 的已知状态输出变化，暂未独立接入每 50ms RMS 音量；主 3D 窗口的真实音频同步仍保留。
- 没有生成通用安装包或经过 Apple notarization。
- 只修改 feature/ultron-desktop-core-v08；未合并或修改 main。