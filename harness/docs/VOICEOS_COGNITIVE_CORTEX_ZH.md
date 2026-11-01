# ULTRON Cognitive Cortex — 本地思维可视化 UI

## 产品目标与边界

原创 JARVIS 氛围的深色科技视觉控制台。保留已有 Python VoiceOS + DeepSeek Harness SDK Agent；只展示真实可观测事件，不显示或伪造模型内部隐藏思维链。

- 中央动态 AI 核心：随 LISTENING、TRANSCRIBING、THINKING、SYNTHESIZING、SPEAKING 状态变化。
- 左侧：语音及 Agent 执行阶段；右侧：真实 ASR、Agent、TTS 加播放、整轮耗时。
- 底部：近期事件时间线与最近完整回复。
- 技术：Python 标准库 HTTP + Server-Sent Events，原生 HTML/CSS/JS；绑定 127.0.0.1:8765，只读。
- 不引入打断功能。语音播报完后恢复免回车自动监听。
- 目前 THINKING 表示 DSH Agent 执行阶段，不等于内部推理文本、Token 流或工具执行图谱。

## 先看视觉 Demo：不消耗 API

```bash
cd ~/Downloads/ultron-web
git fetch origin
git switch feature/voiceos-visual-cortex
git pull --ff-only origin feature/voiceos-visual-cortex
cd harness
source .venv-voiceos312/bin/activate
python -m unittest discover -s voiceos/tests -v
python -u voiceos/dashboard_demo.py
```

浏览器通常会自动打开 http://127.0.0.1:8765。若未自动打开，请手动访问。演示数据有 DEMO 标记，完全是模拟事件，仅用于评估视觉效果。按 Ctrl+C 退出 Demo，释放端口。

## 运行真实 VoiceOS + 可视化界面

```bash
python -u voiceos/core.py --hands-free --tts openai --persona glacial --reply-language en --robotic 55 --dashboard
```

然后在浏览器打开 http://127.0.0.1:8765。这会继续使用原先的麦克风、ASR、DSH Agent 与 TTS，不需要回车发送每轮对话。界面不会替代现有终端，只同步显示实际事件。

端口冲突时传入 --dashboard-port 8766，并改用对应浏览器 URL；设为 0 可自动选择空闲端口。按 Ctrl+C 关闭 VoiceOS 和面板。

## 时间指标口径

- TRANSCRIPTION：语音 WAV 提交至 ASR 后到识别结束的 API 用时，不包括麦克风录音。
- AGENT WORK：完整的 DSH SDK run() 调用用时，包括可能发生的工具执行。
- TTS + PLAYBACK：语音合成、DSP 与完整播放的总用时，不是单纯生成耗时。
- TURN LATENCY：从进入监听到本轮完成的总时长，包括用户说话，不等于说完话到第一声。
- 当前都是单轮指标，不是 P50/P95。下一阶段继续拆分首 Token、首音频延迟，结合工具事件做图谱。

## 安全与验收

- 仅本机 127.0.0.1 服务，不要暴露至公网、端口转发或反向代理。
- 页面可看到 Agent 回复内容，不显示 API Key，不具备执行命令接口。
- 建议测试：浏览器连接显示 CONNECTED；连续三轮对话无需回车；视觉状态、事件与终端日志匹配；播报后自动恢复 LISTENING。
- 本次是代码提交，尚未通过用户 Mac 实机验证；单元测试需要用户本地运行。

## 后续

V0.2：接入 DSH SDK 经文档确认的公开工具事件（工具名称、开始/结束/错误），不泄露隐藏思维链。
V0.3：耗时历史趋势、P50/P95、从用户说完到首声的真实延迟及瓶颈高亮。