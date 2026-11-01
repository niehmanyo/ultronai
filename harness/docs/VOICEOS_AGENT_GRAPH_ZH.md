# VoiceOS Cognitive Cortex V0.3 — 真实 Agent 工具执行图谱

## 核心目标

本版在既有 3D WebGL 神经中枢基础上，让周围的节点由 **DSH SDK 的真实会话事件**驱动。界面只显示实际发生的工具开始、结束和错误；不会推测或展示模型隐藏推理过程，也不使用外部虚构事件。

## 官方事件来源

- DSH Python SDK `harness.run(prompt, session_id=..., on_notification=...)` 可以订阅正在执行的会话事件。
- `notification.method == "session.event"` 时，其 `payload.event` 是带有 `type`, `data` 的会话事件。
- 使用真实 `tool/call` 的 `callId` 与 `name` 创建运行中节点。
- 使用真实 `tool/result` 的 `message.source.callId` 匹配对应节点，读取 `message.isError` 标识完成或失败。
- 事件范围包括 SDK 观察到的根 Session 与子 Session；采用 `(sessionId, callId)` 配对，防止跨子 Agent 冲突。
- 未收到结果的工具标为 `unknown`，不能冒充成功。

## 前端 3D 效果

- 原来的中央 3D 核心、旋转轨道、音频振幅联动不变。
- Agent 真正调用工具时，外围出现一个发光节点，并用能量线连接中央核心。
- `running` 使用青绿；`completed` 蓝色；`error` 红色；`unknown` 中性。
- 每轮最多绘制 18 个工具节点，避免界面失控。仅在收到真实工具事件时生成节点。
- HUD 仅显示最近一个工具名称与运行状态，其余大部分信息通过 3D 结构表达。

## 最小权限与隐私

只传工具名称（限制字符和长度）、自增的匿名节点 ID、运行状态与当前轮次。实际工具调用 ID、参数、结果、文件路径、私有文本及 API Key 不发送给网页。界面仍仅绑定本机 127.0.0.1。用户完整回复可能显示在原有 HUD 底部，避免公网暴露。

## Mac 运行命令

```bash
cd ~/Downloads/ultron-web
git fetch origin
git switch feature/voiceos-agent-graph
git pull --ff-only origin feature/voiceos-agent-graph
cd harness
source .venv-voiceos312/bin/activate
python -m unittest discover -s voiceos/tests -v

# 纯演示，不会发起真实工具或收费模型调用
python -u voiceos/dashboard_demo.py

# 真实语音对话 + DSH 工具网络
python -u voiceos/core.py --hands-free --tts openai --persona glacial --reply-language en --robotic 55 --dashboard
```

浏览器访问 `http://127.0.0.1:8765`，演示完成后先 Ctrl+C 释放端口。真实测试建议让 Agent 执行一个**有权限、低风险、且会调用工具**的任务；若任务只需要直接回答，界面不应该凭空生成工具节点。

## 当前限制和下一阶段

- 使用的是 SDK 公共 Notification 回调中出现的耐久 `tool/call` / `tool/result` 事件，不是完整推理思维链。
- 工具调用与结果可能相距较久；界面会持续显示运行状态。若 SDK 未提供该事件，图谱不会出现节点。
- 节点间的边当前表示“中央 Agent 与工具”的已知调用关系，不声称工具之间有无法证明的实际依赖。
- DSH SDK 事件字段基于官方文档，实际 Python 3.12 / deepseek-harness-sdk 0.1.5rc1 行为仍需 Mac 验证。
- 后续可研究 `tool/ptc-dispatch-start` / `tool/ptc-dispatch` 的子任务真实父子关系，再进一步细分网络。
- **PR #5 保持原样供审核，本版代码独立在 `feature/voiceos-agent-graph`，尚未创建额外 PR，也未合并 main。**