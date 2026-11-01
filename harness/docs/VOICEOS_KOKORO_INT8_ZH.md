# VoiceOS V0.4 · Kokoro-82M INT8 本地 TTS 适配

## 目标与现状

在已有 macOS VoiceOS / DSH Agent / 3D Cognitive Cortex 基础上新增 **`--tts kokoro`**：
- 完全本地合成英文 TTS（不调用 OpenAI Speech API），保留现有云端 `--tts openai --persona glacial` 路径。
- 声线选用 Kokoro 官方英文男声：默认 `am_onyx`，可切换 `am_adam`, `am_echo`, `am_michael`, `bm_george`, `bm_lewis`, `bm_daniel`。
- 量化模型来自 thewh1teagle/kokoro-onnx **model-files-v1.0**，固定使用 `kokoro-v1.0.int8.onnx`（约 88 MB）与配套 `voices-v1.0.bin`（约 28 MB）。不能混用 onnx-community 中逐声线 bin 文件。
- 后端 `kokoro-onnx` 调用 `Kokoro(model, voices).create(text, voice, speed, lang="en-us")`，模型在同一个进程中加载一次并保持可复用。
- 使用标准 16-bit 24kHz 左右的 PCM WAV（采样率取模型实际返回值），现有 `robotic_fx.process_robotic` 与 `personas.play_wav` 不变；3D Cortex 从播放 WAV 提取 50ms RMS 音量包络实时发送 SSE。
- Kokoro 只替换 **TTS**；OpenAI STT、DSH Agent、工具执行和回应准确率不受影响，依然需要原本的 `OPENAI_API_KEY` 与网络。
- **不实现语音打断、不修改 main、不自动部署、不自动创建 MR**。
- 本版代码已提交独立分支，但模型下载与 Mac 上实机速度/音质尚未验证。

## 1. 获取新分支与依赖

```bash
cd ~/Downloads/ultron-web
git fetch origin
git switch feature/voiceos-kokoro-int8
git pull --ff-only origin feature/voiceos-kokoro-int8
cd harness
source .venv-voiceos312/bin/activate

# 基础 VoiceOS 依赖仍沿用已有环境
python -m pip install -r voiceos/requirements-kokoro.txt
```

依赖是可选的，与旧的 `voiceos/requirements.txt` 隔离。建议使用先前已经成功运行 VoiceOS 的 Python 3.12 环境。ONNX Runtime 通常在 Mac CPU 上运行；量化文件较小并不意味着在所有设备都一定比 FP16 更快。

## 2. 首次显式安装模型（仅一次）

```bash
python voiceos/setup_kokoro.py
```

默认存放：
- `~/Library/Caches/UltronVoiceOS/kokoro-v1.0/kokoro-v1.0.int8.onnx`
- `~/Library/Caches/UltronVoiceOS/kokoro-v1.0/voices-v1.0.bin`

安装器从作者 GitHub Release 的版本固定 URL 下载，不自动运行任何远程脚本。复用现有 Mac 回环 HTTPS 代理设置；下载中断会删除临时文件，不覆盖已完成的本地模型。**不下载模型则不会自动启用 Kokoro**。

若你需要自定义路径，安装时用 `--model-dir /你的路径`，启动时也传同样的 `--kokoro-model-dir`。

## 3. 免费离线试听与对比

```bash
python voiceos/preview_kokoro.py --voice am_onyx --robotic 55
python voiceos/preview_kokoro.py --voice bm_george --robotic 55
python voiceos/preview_kokoro.py --voice bm_daniel --robotic 45
```

试听生成文件仅保存在 `harness/voiceos/voice-previews/`（已被 .gitignore 忽略），不走任何 TTS API；相同文字、语速和声线组合会自动复用 WAV。想完全重新本地生成时加 `--force`，不产生云端 TTS 费用。

Kokoro 目前只是男声预设，**并不支持像 OpenAI GLACIAL 那样的自由文字音色指令**；冷酷机械感主要来自声线选择、语速和原有 DSP。不要假装它是专门训练的“原创 Ultron 声纹”。

## 4. 启动真实免回车对话 + 3D 神经核心

```bash
python -u voiceos/core.py \
  --hands-free \
  --reply-language en \
  --tts kokoro \
  --kokoro-voice am_onyx \
  --kokoro-speed 0.92 \
  --robotic 55 \
  --kokoro-fallback none \
  --dashboard
```

本地 UI: http://127.0.0.1:8765

上述命令显式禁用云端 TTS 回退；如果想在本地合成失败时自动尝试付费 GLACIAL TTS，把 `--kokoro-fallback none` 改为 `--kokoro-fallback openai`（需要显式开启）。会在终端警告回退即将发生，仍依赖 OPENAI_API_KEY 和网络。

对比云端 GLACIAL：

```bash
python -u voiceos/core.py --hands-free --reply-language en --tts openai --persona glacial --robotic 55 --dashboard
```

录音和 Agent 还是原来的流程；只切换语音输出 TTS。

## 5. 医生检查与离线测试

```bash
python -m unittest discover -s voiceos/tests -v
python voiceos/core.py --doctor --tts kokoro --reply-language en
```

重点验收：
1. 无网络 TTS 调用时仍有本地英文声音；不会因为缺少模型文件静默退化成系统语音。
2. 自然语言问答仍无回车、Agent 不变、多轮上下文可用。
3. 3D 神经核心在播放 Kokoro PCM WAV 时随声音脉冲；音量事件仅传 normalized level，不传原始音频。
4. 首次模型加载与每轮合成耗时清楚输出；建议测试 10 条短句和 10 条长句，分别对比实际延迟与音色。
5. 故意指定错误模型目录验证 `--kokoro-fallback none` 报错停止；改为 `openai` 时明确提示云端回退。
6. 用户本机测试通过再考虑另开 MR；**当前没有合并 main**。

## 6. 已知限制及下一步优化

- 本版依然要生成 **整段回复 WAV** 才开始播放，真正的“首音频流式播放”下一阶段可基于 Kokoro 的 `create_stream` API 做分片播放。
- 目前的 Kokoro 模型是英文 v1.0，选择 `--tts kokoro` 必须同时设置 `--reply-language en`。这是让 Agent 尽量用英文回答的指令，不保证外来工具结果中绝对无非英文文本。
- 第一次安装下载约 116 MB 模型/声线资产，首次加载花费取决于 Mac 性能。Apple Silicon 或 Intel Mac 的实际速度未经实测，不对性能倍率作保证。
- 与任意本地模型一样，如果输入文本过长、模型返回错误或声线不合适，需要评测与调整；云端 GLACIAL 仍是可用的明确回退选项。
- 该模型与 `deepseek-harness-sdk` 没有依赖关系，不会替换 DSH 推理。
