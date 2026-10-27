# Ultron VoiceOS V0.1 — 终端语音内核（macOS）

**本阶段仅实现内核，不开发 HUD/Web UI。**

数据通路：

\`\`\`text
Mac mic → sounddevice/WAV → OpenAI audio.transcriptions
        → official DSH Python SDK (profile=sdk, separate runtime)
        → DSH agent response → macOS say → Mac speakers
\`\`\`

目标是先验证能通过 Mac 麦克风与真正的 DSH Agent 多轮对话，播报可被打断。不使用自制 Agent Loop，不修改官方 DSH npm 包，不改变 Render 线上站点。

## 1. 拉取代码

\`\`\`bash
cd ~/Downloads/ultron-web
git fetch origin
git switch feature/voiceos-core-mvp
git pull --ff-only origin feature/voiceos-core-mvp
cd harness
\`\`\`

## 2. 准备 Python 环境

需要 macOS 14+ on Apple Silicon，Python 3.10+。Python SDK 提供匹配的 native runtime，**它会启动一个独立的 DSH SDK 进程，不会自动接管已打开的 DSH Web UI Session**。

\`\`\`bash
python3 --version
uname -m
# 必须 Python >= 3.10、arm64；若 Python 太旧，安装新版 Python 后重建虚拟环境
python3 -m venv .venv-voiceos
source .venv-voiceos/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install --pre -r voiceos/requirements.txt
python -m unittest discover -s voiceos/tests -v
\`\`\`

**pip 提示 No matching distribution found for deepseek-harness-sdk 时**：
1. 先运行 `python -V`、`uname -m`、`python -m pip --version`。
2. SDK 当前发布的是 `0.1.5rc1`（预发布版），本仓库已显式固定版本；请使用上方的 `--pre` 命令。
3. 如果当前虚拟环境 Python 低于 3.10，使用 Python 3.11/3.12 创建全新虚拟环境，不能只升级 pip。
4. 如果 `uname -m` 为 `x86_64` 且你的 Mac 是 Apple Silicon，请检查是否在 Rosetta 下运行 Terminal 或 Python；官方 SDK 的 macOS runtime wheel 仅支持 arm64。
5. 如果仍失败，检查公司/校园 PyPI 镜像是否同步了预发布包；可使用 `python -m pip index versions --pre deepseek-harness-sdk` 诊断。

macOS 首次录音时需要授予 **Terminal 或当前使用的终端 App** 麦克风权限；如果失败，请检查 **系统设置 → 隐私与安全性 → 麦克风**。某些音频设备无法以 16 kHz 直接打开，需要切换系统输入设备。

## 3. 提供 OpenAI API Key

DSH Web Settings 内存储的密钥**不会自动转变为 Python 进程的 OPENAI_API_KEY**。为安全起见，在当前终端临时输入；不要把 Key 写入 Git、README、命令历史或聊天记录。

\`\`\`bash
read -r -s -p 'OpenAI API Key: ' OPENAI_API_KEY
echo
export OPENAI_API_KEY
\`\`\`

本脚本使用 \`gpt-4o-mini-transcribe\` 做 ASR，默认 \`gpt-4.1-mini\` 作为 Agent 模型。它们需要你的 OpenAI API 项目可用额度；ChatGPT Plus 订阅不代替 API 计费。

**重要集成边界**：官方 DSH SDK 的 profile 和 provider 配置可能与现有 \`web\` profile 不同。这里默认 \`--profile sdk --provider openai\`，只是期望使用已有 DSH_HOME 的 OpenAI provider；如果提示 adapter/provider/model 不可用，说明 SDK profile 尚未完成 OpenAI 适配，不表示语音识别有问题。不要擅自切到 DeepSeek API。本 MVP 当前未附带 profile 自动迁移脚本。

## 4. 先验收 SDK，不录音

\`\`\`bash
python voiceos/core.py --doctor
python voiceos/core.py --text "用一句中文介绍你自己" --no-speech
\`\`\`

第二条应打印 \`[Ultron]\` 回复。只有这一步成功，再开始麦克风测试。

## 5. 语音测试

\`\`\`bash
python voiceos/core.py
\`\`\`

操作说明：

1. 终端出现 \`Enter to record\` 时，按回车开始录音。
2. 对着 Mac 说：**“Ultron，你好，请用中文介绍一下自己。”**
3. 再按回车停止录音。
4. 看到识别文本 \`[You]\`，等待 DSH 完成处理；看到 \`[Ultron]\` 和 macOS 语音播报。
5. 播报期间按回车，停止播报（**仅停止 TTS，不会取消已经运行的工具动作**）。
6. 下一轮问：**“我刚才要求你使用什么语言回答？”**，验证同一运行中的 DSH Session 能保留上下文。
7. 回到提示符时输入 \`q\` 退出。

系统默认使用 macOS 当前默认声音。可选择系统已有语音：\`say -v '?' | head\`；再传 \`--voice Tingting\` 等实际可用名称。

## 6. 诊断和限制

- 通过 macOS \`scutil --proxy\` 识别已经启用的本机回环 HTTP 代理（与之前已验收的 \`127.0.0.1:7890\` 思路一致）。可设置 \`ULTRON_PROXY_AUTO=0\` 禁用自动检测。
- ASR 是**录音完成后转写**，不是实时流式识别；TTS 是系统 \`say\`，不是逐 token 低延迟 TTS。
- 播报支持打断，但不提供语音唤醒词、语音打断、重叠全双工对话、实时波形或 GUI。
- 麦克风原始音频仅生成于本机临时目录，请求 OpenAI 音频转写接口后自动删除；转写后的文本会进入 DSH 的 Session 存储，按 DSH profile 的规则保留。
- 使用 \`--session-id\` 在同一进程中复用会话标识；**跨进程 Session 恢复以及与 DSH Web 共享 Session 尚未验收，不作为 V0.1 MVP 承诺**。
- DSH SDK agent 可调用工具，务必保持本机权限最小化；不要让它自动执行高风险命令。SDK profile 的实际工具与权限策略需本机审计。
- macOS \`say\` 播报停止是子进程终止，不会撤回设备操作。
- 模型调用可能收费；不要将 API Key 或包含私人信息的转写日志提交 GitHub。
- 若 \`--text\` 失败，请先查 SDK profile/provider 兼容性，不需要重新安装 Ultron Web。Web 与 SDK Runtime 是不同的进程入口。
- 无现场 Mac 麦克风和用户密钥，本分支仅完成代码与离线测试编写，**还没有被宣称通过真实录音到 Agent 的端到端验收**。

## 7. 版本节奏

- **VoiceOS V0.1a（此分支）**：终端语音闭环；优先验证 SDK profile、麦克风、转写、TTS。
- **VoiceOS V0.1b**：验证与 DSH Web 的 Session 和工具事件桥接、降低语音延迟。
- **VoiceOS V0.2**：插件注册、macOS 音量控制、工具实际状态验证。
- **UI 阶段**：在语音内核稳定、接口事件固定之后才开始科幻 HUD。

上游 SDK 文档：https://github.com/deepseek-ai/deepseek-harness/blob/master/python/sdk/README.md

## 8. SDK 返回 JsonRpcError 的诊断

首先从功能分支拉取最新提交并重新执行文字测试：

```bash
cd ~/Downloads/ultron-web
git pull --ff-only origin feature/voiceos-core-mvp
cd harness
python voiceos/core.py --text '你好，请用一句中文介绍自己' --no-speech
```

新版脚本会输出脱敏后的 JSON-RPC 错误摘要（会隐藏当前 OPENAI_API_KEY 和常见 sk- token），用于确定是 provider/model 适配器未注册、profile 加载失败、凭据问题还是其他异常。请不要粘贴 DSH_HOME 中包含凭据的配置文件；如果错误中仍含有个人信息，请自行遮盖后再分享。

**关键区别**：`deepseek_harness` SDK 的 `sdk` profile 默认不保证装载 DSH Web 的 `openai` provider。单独 `export OPENAI_API_KEY` 并不等于 `sdk` 配置了 OpenAI 模型适配器。若错误证实是 adapter/provider 缺失，需要在 SDK profile 中显式注册 OpenAI adapter，而不是重复更换密钥。该适配将基于当前安装的 SDK release profile schema 修复。

此外，`read -s 'VAR?prompt'` 是 zsh 专用语法，bash 应使用 `read -r -s -p 'OpenAI API Key: ' OPENAI_API_KEY`，随后 `echo; export OPENAI_API_KEY`。如果 doctor 已显示 Key `set`，不要再次输入。

## 9. 修复 `no adapter registered for provider "openai"`

确认拉取修复后的分支：

```bash
cd ~/Downloads/ultron-web
git switch feature/voiceos-core-mvp
git pull --ff-only origin feature/voiceos-core-mvp
cd harness
python voiceos/core.py --doctor
python -m unittest discover -s voiceos/tests -v
python voiceos/core.py --text '你好 Ultron，请用中文介绍自己' --no-speech
```

这次修复新增 `voiceos/openai.patch.yml`：

```yaml
- id: llm-pi-ai
  config:
    providers:
      openai:
        apiKeyEnv: OPENAI_API_KEY
```

`core.py` 将这个只含**公开配置**的文件通过 `DeepSeekHarness(patches=(...))` 传入 SDK。官方完整 `sdk` profile 挂载 `llm-pi-ai`，补丁为其声明 `openai` 模型路由；通过进程环境使用已经设置的 API Key。没有修改 `$DSH_HOME/profiles/web/` 或浏览器里已生效的 OpenAI 设置。

若报 `UNKNOWN_MODEL`，换用当前 SDK 目录确实支持的 OpenAI 模型；若报 `MISSING_CREDENTIAL`，检查当前进程 `OPENAI_API_KEY` 是否已 export；若成功看到 `[Ultron]` 回复，继续运行 `python voiceos/core.py` 验收录音。

## 10. 已验收 Agent 文本回答，但麦克风提示 `No module named 'numpy'`

`sounddevice.InputStream` 的缓冲区处理依赖 NumPy。VoiceOS 依赖文件已加入 `numpy>=1.26,<3`；在激活的 Python 3.12 虚拟环境中执行：

```bash
cd ~/Downloads/ultron-web
git pull --ff-only origin feature/voiceos-core-mvp
cd harness
python -m pip install -r voiceos/requirements.txt
python voiceos/core.py --doctor
python voiceos/core.py
```

期待 doctor 输出 `numpy: installed`。文本 Agent 已经能返回正常回答，不需要重新生成 API Key，也不需要调整代理或 SDK Provider。按 Enter 录音、再按 Enter 停止，随后检查 `[You]` 识别内容和 `[Ultron]` 回复。如果出现录音设备或系统授权错误，请单独处理 macOS 麦克风权限。

## 11. 修复 `session "ultron-voiceos-mvp" already exists`

之前脚本固定复用 `ultron-voiceos-mvp` Session ID，重启后 SDK 会尝试创建一个已持久化的 Session，报 `already exists`。新版默认每次**启动**生成唯一的 `ultron-voice-<uuid>`，并在同一进程的所有语音轮次复用这个 ID。既不删除原 Session，也不影响 DSH Web。

```bash
cd ~/Downloads/ultron-web
git switch feature/voiceos-core-mvp
git pull --ff-only origin feature/voiceos-core-mvp
cd harness
python -m unittest discover -s voiceos/tests -v
python voiceos/core.py
```

日志会显示本次的 `[VoiceOS] Session: ultron-voice-...`。在同一个程序里连续两轮，分别说“我叫测试员小蓝，请记住这一轮”和“我刚才说我叫什么？”，观察 SDK 会话上下文。这个测试只需要短期 Session 上下文，不需要把名字保存到长期记忆。

`--session-id` 现在是**可选高级参数**，如自行指定已经持久化的旧 ID 仍可能冲突。**当前版本没有自动恢复跨进程的 SDK Session**；后续需要验证 `resume_session` 及已安装 SDK release 的支持情况，而不是清空已有 Session 数据。

你的前一次测试已确认麦克风录音及 ASR 正常，且 SDK 能返回真实中文回答，因此无需重装依赖或更换 API Key。

## 12. VoiceOS V0.1b：免按键语音对话与实验性打断

本阶段基于已验收的 OpenAI ASR → DSH SDK → macOS `say` 增量扩展；**没有新的 Web UI，也不是全双工实时语音**。只在当前终端会话运行，退出后不会持续监听。

### 更新和离线测试

```bash
cd ~/Downloads/ultron-web
git switch feature/voiceos-core-mvp
git pull --ff-only origin feature/voiceos-core-mvp
cd harness
source .venv-voiceos312/bin/activate
python -m unittest discover -s voiceos/tests -v
```

### 免按键模式（推荐先测）

```bash
python voiceos/core.py --hands-free
```

看到 `Listening automatically` 之后直接说话，停顿约 0.75 秒就自动结束录音、ASR 转写、Agent 回复和 `say` 播报。播报结束后自动进入下一轮监听，保持同一运行时的 Session 上下文。按 **Ctrl+C** 退出。系统不会自动开启录音权限；需要 macOS 当前终端已有麦克风授权。

### 可选：在播报时说话来打断（实验性）

**强烈建议戴耳机**，否则 Mac 外放可能被麦克风当成你的插话。

```bash
python voiceos/core.py --hands-free --barge-in
```

当 Ultron 正在朗读时，持续发声约 0.45 秒且音量足够大，可尝试停止 `say`。随后程序会显示 `Listening automatically`，请**重新完整说出**新请求。打断瞬间的音频不会自动形成完整提问，也不会取消正在执行的工具动作。

### 噪声或声音太小

```bash
# 安静环境，较轻的声音可能需要降低阈值
python voiceos/core.py --hands-free --vad-threshold 350
# 噪声大、频繁误触发可增大阈值
python voiceos/core.py --hands-free --vad-threshold 950
```

阈值取值限制 100–12000；这是固定 RMS 能量门限，不是神经网络语音活动检测。默认采样率 16kHz、分块 30ms、起音连续约 240ms、尾部静音约 750ms、最长单段约 35s。等待讲话最长 60s，超时后重新监听。

### 验收要点

1. 在 `--hands-free` 下连续进行两轮问题，不按回车，第二轮正确引用上一轮。
2. 停顿后能自动触发转写，终端出现 `[You]` 和 `[Ultron]`。
3. 在 `--barge-in` 与耳机环境下尝试插话，`say` 能结束；插话结束后重新提出完整请求。
4. 测试两次 `Ctrl+C` 正常退出，终端无需强制杀进程。
5. 保留原命令 `python voiceos/core.py`，验证按回车录音的兼容性。

**明确的限制**：ASR 仍是整段音频发送；DSH `run()` 仍需等待整轮结束才返回最终文本；`say` 仍为整段播报。当前不存在逐 Token TTS/持续全双工音频，也没有声学回声消除。打断算法是实验性的，会受耳机、声量、噪声和麦克风增益影响。

未经用户 Mac 实机测试，本次只能算代码已交付，不能宣称自然打断已通过验收。


## 13. ULTRON Original Voice · V0.1

三套原创声音风格：Prime（沉稳磁性）、Sentinel（优雅亲切）、Sovereign（低沉未来感）。这是内置声音加朗读风格指令，不是演员原声克隆，也不是独一无二且永久保存的声纹。

### Mac 本地生成三个中文 WAV 试听

```bash
cd ~/Downloads/ultron-web
git switch feature/voiceos-core-mvp
git pull --ff-only origin feature/voiceos-core-mvp
cd harness
source .venv-voiceos312/bin/activate
python -m unittest discover -s voiceos/tests -v
python voiceos/preview_voices.py --language zh --play
```

三个声音预览保存在本地 harness/voiceos/voice-previews/ 下。当前 OPENAI_API_KEY 需要已设置，合成 API 产生费用。仅试听一种可以运行：

```bash
python voiceos/preview_voices.py --persona prime --language zh --play
```

### 在 VoiceOS 连续语音中使用

```bash
python voiceos/core.py --hands-free --tts openai --persona prime
python voiceos/core.py --hands-free --tts openai --persona sentinel
python voiceos/core.py --hands-free --tts openai --persona sovereign
```

旧版 `python voiceos/core.py --hands-free` 仍使用系统 say；不受影响。OpenAI TTS 采用先合成 WAV 再 afplay 的整段播放方式，暂不支持 `--barge-in`，程序会显式拒绝此组合。合成可能增加响应延迟和费用；应明确告知听众声音为 AI 生成。

### 不等同于 OpenAI Prompt-to-Voice 的永久自定义声纹

OpenAI Speech API 的 gpt-4o-mini-tts 已公布于 2027-01-06 停止支持，因此这里只作为试听/临时过渡。若决定打造永久 Voice ID，可使用官方 POST /v1/audio/voices Prompt-to-Voice 生成，**但文字提示生成的 Voice ID 仅适用于 GPT-Live，不能传给现有 /v1/audio/speech**。后续需要用 GPT-Live 语音前端对接 DSH Agent 的任务执行。

## 14. ULTRON 机械音色 V0.2（保留原声，增加电子质感）

新增纯本地 NumPy 后处理模块 `voiceos/robotic_fx.py`：轻微 83Hz 侧带调制与 9ms/17ms 微延时共振，同时保留主要干声，避免夸张的机器人失真。参数 `--robotic` 取值 0～100，默认 25；0 为无损直通。仅作用于 `--tts openai` 的合成 WAV，不影响 macOS say。

### 试听以前生成的声音，免费比较机械感

```bash
cd ~/Downloads/ultron-web
git pull --ff-only origin feature/voiceos-core-mvp
cd harness
source .venv-voiceos312/bin/activate
python -m unittest discover -s voiceos/tests -v
python voiceos/preview_voices.py --from-wav voiceos/voice-previews/ultron-prime-zh.wav --robotic 20 --play
python voiceos/preview_voices.py --from-wav voiceos/voice-previews/ultron-prime-zh.wav --robotic 45 --play
python voiceos/preview_voices.py --from-wav voiceos/voice-previews/ultron-prime-zh.wav --robotic 70 --play
```

如之前没有生成过该 WAV，可先执行一次 `python voiceos/preview_voices.py --persona prime --language zh --robotic 45 --play`，此操作会产生一次 OpenAI Speech API 计费请求；以后从保存的 WAV 本地试听不同强度不产生新 API 费用。

### 正式启动 VoiceOS

```bash
python voiceos/core.py --hands-free --tts openai --persona prime --robotic 45
```

建议从 25（微弱）/45（均衡）/70（更显著）对比，用户听感为准。此为原创 AI 音效，不是 JARVIS 的演员原声，不引入音色克隆；不会改善真实流式延迟，也仍暂不支持 `--barge-in` 与 OpenAI TTS 同用。

## 15. 机械感明显增强版（响应试听反馈）

V0.2 的早期版本使用轻微调制和共振，实际效果不够明显。新版将处理层改为两组载波（92Hz/147Hz）环形调制、非线性谐波增强和短延迟共振，并真正提高 wet/dry 混合比例。这是原创电子合成声效果，不是电影 JARVIS 的声音复制，也不等于真正的多频带声码器。

### 利用上一次保存的 WAV，完全离线且无 TTS 费用地比较

```bash
cd ~/Downloads/ultron-web
git switch feature/voiceos-core-mvp
git pull --ff-only origin feature/voiceos-core-mvp
cd harness
source .venv-voiceos312/bin/activate
python -m unittest discover -s voiceos/tests -v
python voiceos/preview_voices.py --from-wav voiceos/voice-previews/ultron-prime-zh.wav --robotic 0 --play
python voiceos/preview_voices.py --from-wav voiceos/voice-previews/ultron-prime-zh.wav --robotic 45 --play
python voiceos/preview_voices.py --from-wav voiceos/voice-previews/ultron-prime-zh.wav --robotic 80 --play
```

将 Prime 换成你更喜欢的音色（如 sovereign）也可。输出存放 `voiceos/voice-previews/`，可在 Finder 中逐个对比。`--robotic 0` 为原文件字节级复制。注意高于 70 的效果可能牺牲可懂度，优先尝试 45。

### 语音对话直接使用新版

```bash
python voiceos/core.py --hands-free --tts openai --persona prime --robotic 65
```

当前 `--barge-in` 仍仅支持 macOS TTS；OpenAI TTS 音效整段处理后才播报，不是实时流式。新版尚待用户的 Mac 音色主观试听验收。