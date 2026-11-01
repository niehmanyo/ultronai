# VoiceOS V0.2 — 低延迟语音与自然打断

## 基线与分支

- 前一阶段功能：`feature/voiceos-core-mvp`，已发 PR #4（待审核，不自动合并）。
- 本阶段：`feature/voiceos-v02-streaming`，从前一阶段功能分支派生，暂不新建 PR，也不改 main。
- **已编码的第一步：** OpenAI TTS 的已生成 WAV 播放阶段支持实验性麦克风打断；通过 `afplay` 终止播放。
- **未实现：** 增量 ASR、LLM Token 流处理、边生成边播报、回声消除、打断时保留完整用户插话、取消运行中的 Agent 工具。

## 第一阶段验收：GLACIAL + Barge-in

```bash
cd ~/Downloads/ultron-web
git fetch origin
git switch feature/voiceos-v02-streaming
git pull --ff-only origin feature/voiceos-v02-streaming
cd harness
source .venv-voiceos312/bin/activate
python -m unittest discover -s voiceos/tests -v
python -u voiceos/core.py --hands-free --tts openai --persona glacial --reply-language en --robotic 55 --barge-in
```

用耳机测试（避免自家扬声器的声音误触发麦克风）。对 Ultron 说一个需要较长回答的问题，待听到 GLACIAL 声音后再持续讲话约 0.45 秒。达到音量阈值时应停止 `afplay`，返回下一轮 `Listening automatically`。**插话会丢失**，需等到重新监听后完整说出问题。没触发可调低 `--vad-threshold`，但降低阈值也增加误触发。

回退命令：`python voiceos/core.py --hands-free --tts openai --persona glacial --reply-language en --robotic 55`；不指定 `--barge-in` 时不启动麦克风播报监听。

## 后续工程阶段

1. **低延迟播报**：研究当前语音 API 的真正流式传输能力，将音频分片写入低延迟播放设备；避免等完整 WAV 下载后才播放。要求 API 兼容性、分片数据格式、取消语义、音频头处理及测试。
2. **流式 Agent 桥接**：验证 DSH SDK 官方流式事件/执行增量接口；在明确合法 API 前不使用未证实的假方法。必要时加一层文本缓冲，只将已完成句子送 TTS，避免一字一请求和费用激增。
3. **VAD/AEC**：从固定 RMS 阈值迭代到具备语音判别力的 VAD，设计 echo cancellation（AEC），减少外放误触发。
4. **真正的语音打断**：从播放阶段停止扩大到正在合成时取消网络请求、正在执行时安全取消任务、保存并转写插话音频、遵循用户授权与工具安全边界。
5. **测试与指标**：追踪首音频延迟、TTFT、转写成功率、误触发率、真实打断成功率和每轮 API 消耗，设置可重复的本地测试用例。

## 约束

- macOS 原生终端优先，不额外做 UI。
- 不复制电影演员原声，保留原创英文 GLACIAL 声线。
- 维持可回退的成熟按键模式与上一个功能分支。
- API Key 不入 Git，音频本地文件不提交，自动化测试不触发付费模型请求。
- 目前所有 V0.2 代码尚待用户 Mac 实测，不能声称打断已通过验收。
