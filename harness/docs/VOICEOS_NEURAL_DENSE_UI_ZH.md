# ULTRON Neural Cortex — Dense Edition

## 目标

只升级已有本地可视化 UI，不改变 TTS、ASR、DSH Agent、语音交互协议。用户已明确暂不替换语音，**本分支从 `feature/voiceos-agent-graph` 创建，不包含 Kokoro 安装和依赖改动**。保留现有 OpenAI GLACIAL 声线、免回车模式、3D 语音振幅同步和真实工具事件图谱；不加入语音打断。

## 本次视觉增强

- 3D 核心点云外壳：2400 个点。
- 3D 体积内核：1150 个点，使用均匀体积半径分布增强深度。
- 3D 外围点云壳：1050 个点。
- 星云散点：1150 个点，分布在外围 3D 空间。
- 共 **5750 个基础点**，此外还有真实工具调用节点与 180 条装饰性神经几何线段；这些线段不是虚构的任务链。
- 语音时核心点云在 GPU shader 中依据真实 50ms RMS 音量包络进行细微位移与亮度响应，连同光晕和轨道产生能量波动。
- thinking 时点阵旋转更活跃；当 DSH 真实报告 tool/call/tool/result，工具图谱继续显示对应节点。
- 极简 HUD：中枢主视觉、左右状态灯、底部耗时和最后回答；增加少量科幻扫描纹理与 HUD 边角。
- WebGL 在 Mac 显卡上运行；点云几何只创建一次，不每帧重建。切换工具图谱时销毁旧 GPU buffer，防止多轮执行泄漏显存。
- 尊重 macOS / 浏览器 prefers-reduced-motion；该模式下旋转动画停止，但事件及数据仍可更新。

## 安装与免费预览

```bash
cd ~/Downloads/ultron-web
git fetch origin
git switch feature/voiceos-neural-dense-ui
git pull --ff-only origin feature/voiceos-neural-dense-ui
cd harness
source .venv-voiceos312/bin/activate
python -m unittest discover -s voiceos/tests -v
python -u voiceos/dashboard_demo.py
```

浏览器访问 `http://127.0.0.1:8765`。Demo 的工具节点和语音振幅均明确是模拟数据，不调用模型和 TTS。演示结束后在终端 Ctrl+C 释放端口。

## 真实 GLACIAL + 3D 点云

```bash
python -u voiceos/core.py --hands-free --tts openai --persona glacial --reply-language en --robotic 55 --dashboard
```

默认打开 `http://127.0.0.1:8765`。无需设置 Kokoro、无需下载额外模型。该功能仍需原有 OpenAI API Key 和网络。

## 质量验收

1. 待机时 3D 球体明显由点阵组成，近远点与外围星云有空间层次感。
2. 听到 GLACIAL 时，点云微变形、光晕及轨道随实际播放音量起伏；播报完自然回落。
3. Agent 执行中有更明显的计算热区；工具节点仍只由真实 SDK 的调用事件出现。
4. 浏览器切换窗口、恢复窗口和调整尺寸时不崩溃；在较弱 Mac 上观察 CPU/GPU 占用，必要时降低点阵数量。
5. 页面没有额外后端控制权限、不暴露工具内容和隐藏思维链。

## 当前限制

代码已推送 GitHub，尚未在用户的 Mac 实测，不能声称视觉验收已经通过。WebGL 不是带精确物理光线追踪的渲染器；点阵发光使用轻量加法混合和透视深浅处理。此版本没有把隐藏思维链暴露出来。

独立分支 `feature/voiceos-neural-dense-ui`，不修改 main，不创建或合并 MR。