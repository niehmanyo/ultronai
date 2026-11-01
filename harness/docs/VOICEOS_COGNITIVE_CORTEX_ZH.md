# ULTRON Cognitive Cortex V0.2 — 真 3D 神经核心与语音联动

## 本轮升级

- 从二维 SVG 与文字面板替换为浏览器原生 WebGL 3D 神经球体、三个倾斜的轨道环和漂浮粒子，有真实 XYZ 坐标及透视投影。
- UI 极简化：只保留状态、连接灯、底部 ASR/Agent/TTS 耗时与最近回答；中枢占据主画面。
- **真实语音振幅联动**：Python 在 TTS WAV 播放前提取 50ms 一段的 RMS 音量包络，播放后每 50ms 同步通过 SSE 推送 `audio_level`。页面球体、粒子与光晕跟随实际声音波动。
- `speaking` 动画在系统播放器真正启动后进入，不在网络合成阶段假装播报；`thinking` 只是 Agent 正在工作，不暴露内部隐藏思维链。
- 浏览器不接收原始 WAV/麦克风数据，只收到 0~1 音量值；SSE 音量帧不写入事件历史，刷新页面不会回放过去语音。
- 原生 WebGL，不依赖 CDN、Three.js/npm 和外网下载；WebGL 不可用时显示静态回退核心。没有新增音效处理费用。
- **不包含语音打断**，GLACIAL 英文语音、自动监听和原 DSH 工作流不变。

## 安装和测试

```bash
cd ~/Downloads/ultron-web
git fetch origin
git switch feature/voiceos-visual-cortex
git pull --ff-only origin feature/voiceos-visual-cortex
cd harness
source .venv-voiceos312/bin/activate
python -m unittest discover -s voiceos/tests -v
```

### 1. 先看免费本地演示

```bash
python -u voiceos/dashboard_demo.py
```

浏览器打开 `http://127.0.0.1:8765`。DEMO 通过模拟音量包络测试 3D 球体发声效果，**不是实际语音，也不是实测模型耗时**。按 Ctrl+C 关闭演示释放端口。

### 2. 真实语音 + 3D UI

```bash
python -u voiceos/core.py --hands-free --tts openai --persona glacial --reply-language en --robotic 55 --dashboard
```

浏览器打开 `http://127.0.0.1:8765`。实际完整流程：自动检测讲话结束 → OpenAI ASR → DSH SDK Agent → GLACIAL TTS → WAV 本地机械处理 → 播放时实时音量反馈至神经核心 → 播报结束自动恢复监听。

如果端口被占：加 `--dashboard-port 8766`。在 CLI 中 Ctrl+C 停止。

## 验收

1. 免费 DEMO 能显示旋转 3D 球体和倾斜环；Speaking 阶段随演示音量变化，不是匀速呼吸。
2. 真实模式连接状态为 LINKED；说话后状态按实际阶段切换；不需要按回车发送。
3. GLACIAL 开始从 Mac 出声时，球体和光晕随英文重音起伏；结束后归零并进入监听。
4. 不传输原始音频、不泄漏密钥、无打断入口。请在本机运行离线测试并通过浏览器视觉验收；当前 GitHub 提交不代表已在你的 Mac 实测。

## 当前限制

- 已生成完整 WAV 后才播放。播放时音量驱动是相对开始时间同步，`afplay` 实际缓冲可能有小幅偏差；下一阶段可从同一播放器输出回调获取更精准的播放时钟。
- TTS 耗时指标仍为 **TTS + 完整播放**，不应当成首声音延迟。
- 若原始音频不是 PCM16 WAV，音量模块会拒绝对应格式；OpenAI 的 `response_format=wav` 正常应返回可处理的 PCM WAV。
- 本版是显式 WebGL 透视 3D，不依赖 Three.js。视觉效果随 Mac GPU/WebGL 能力和浏览器性能变化。
- WebGL 出现兼容问题时有视觉回退，但回退画面不具备 3D 动画。
- 隐私：页面本地只读，仍可能显示 Agent 最后输出，禁止公网暴露。

## 未来方向

增加真实 DSH 工具调用图谱和 P50/P95 性能趋势；若需要更高级的表面材质，可基于当前 3D 事件接口升级自定义 Shader，但不再通过大段文字填充界面。
