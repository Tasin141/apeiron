---
title: Apeiron Unified AI Hub
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: gradio
app_file: app.py
pinned: false
---

# 🏔️ Apeiron Unified AI Hub

**Central router for 47 open-source AI models** — One interface to rule them all.

## 🌟 Overview

Apeiron is a unified AI platform that routes your prompts to the optimal specialized model across 10 categories. No API keys needed — runs entirely on Hugging Face Spaces with cloud GPU inference.

## 🤖 47 Models Across 10 Categories

| Category | Models | Default |
|----------|--------|---------|
| 💻 **Coding** | Qwen 2.5-Coder, DeepSeek-Coder V2/V3, GLM-4, Llama 3.3, Aider, Phi-3, Mistral, Nemotron, CodeGemma | `qwen2.5-coder` |
| 🎬 **Video** | Wan 2.1/2.2, HunyuanVideo, LTX-Video, CogVideoX | `wan2.1` |
| 🔊 **Audio** | Whisper, Kokoro-82M, F5-TTS, XTTS-v2, YuE, Stable Audio Open | `whisper` |
| 🎨 **Design** | FLUX.1/FLUX.2, Stable Diffusion 3.5 Large, Qwen-Image 2.1 | `flux1` |
| 🔬 **Research** | DeepSeek-R1, QwQ-32B, STORM, Open Deep Research, Crawl4AI, SearXNG | `deepseek-r1` |
| 🛡️ **Threat Intel** | Robin, AIL Framework, OpenCTI, TorBot, Darkdump | `robin` |
| 🤖 **Agents** | LangGraph, AutoGen, CrewAI, Browser-Use, Open-Interpreter | `langgraph` |
| 📚 **Education** | Qwen 2.5-Math, DeepSeek-R1 (Edu), Llama 3.3 | `qwen2.5-math` |
| 📄 **Resume** | Reactive-Resume/Typst, Qwen 2.5 Proposal, Llama 3.3 Proposal | `reactive-resume` |
| 📈 **Trading** | FreqAI, Amazon Chronos, Google TimesFM, FinGPT, FinRL, CCXT Live | `ccxt-live` |

## 🚀 Quick Start

1. **Select a category** from the sidebar (e.g., "Coding", "Video", "Research")
2. **Enter your prompt** in the chat box
3. **Click Send** — Apeiron routes to the optimal model
4. **View results** in the right panels (Code, Images, Video, Audio, Reports, Charts)

### Example Prompts

| Category | Example Prompt |
|----------|----------------|
| 💻 Coding | `"Create a Python async web scraper with rate limiting"` |
| 🎬 Video | `"Generate a 10-second cinematic video of a futuristic city"` |
| 🎨 Design | `"Create a logo for a cybersecurity startup, minimal style"` |
| 🔬 Research | `"Analyze the latest developments in quantum computing 2024"` |
| 🛡️ Threat Intel | `"Generate threat report for CVE-2024-xxxx exploitation"` |
| 🤖 Agents | `"Build a multi-agent system for automated code review"` |
| 📚 Education | `"Explain transformer attention mechanism with code"` |
| 📄 Resume | `"Write ATS-optimized resume for Senior ML Engineer"` |
| 📈 Trading | `"Analyze BTC/USDT technical setup with risk management"` |

## 🏗️ Architecture

```
User Prompt
    │
    ▼
┌─────────────────────────────────────┐
│     Apeiron Unified Hub (Router)    │
│  • Category Detection               │
│  • Model Selection                  │
│  • Cloud Endpoint Routing           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       47 Specialized Models         │
│  (Cloud GPU Inference)              │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│      Unified Output Format          │
│  • Structured JSON Response         │
│  • Category-Specific Rendering      │
│  • Multi-Modal Display              │
└─────────────────────────────────────┘
```

## 🔧 Technical Details

- **Framework**: Gradio 5.x on Hugging Face Spaces
- **Runtime**: Python 3.10+ with asyncio
- **Inference**: Cloud GPU (zero local downloads)
- **Models**: 47 open-source models via cloud APIs
- **Output**: Multi-modal (code, images, video, audio, reports, charts)

## 📁 Project Structure

```
apeiron/
├── app.py                      # Gradio web dashboard (entry point)
├── core/
│   └── apeiron_unified_hub.py  # Central router for 47 models
├── modules/
│   ├── automation/
│   │   └── bg_self_improving_engine.py  # 24/7 background engine
│   ├── coding/
│   │   └── coder_engine.py
│   ├── media/
│   │   └── media_engine.py
│   ├── trading/
│   │   └── trading_engine.py
│   └── automation/
│       ├── cv_automation.py
│       └── research_crawler.py
└── requirements.txt            # Clean dependencies for HF Spaces
```

## ⚙️ Configuration

The system auto-configures on startup:
- Default model: `qwen2.5-coder` (coding category)
- Cloud-only execution (no local model downloads)
- 47 models registered across 10 categories
- Default active model prevents null errors

## 🔒 Privacy & Security

- **No local model storage** — all inference in cloud
- **No API keys required** — uses public endpoints
- **No data persistence** — stateless by default
- **HTTPS only** — all cloud communications encrypted

## 📄 License

MIT License — Open source, free to use and modify.

## 🤝 Contributing

1. Fork the repository
2. Add new models to `core/apeiron_unified_hub.py`
3. Update `CATEGORY_ROUTERS` mapping
4. Submit PR with tests

## 🔗 Links

- **Hugging Face Space**: [Apeiron Unified AI Hub](https://huggingface.co/spaces/username/apeiron)
- **GitHub**: [github.com/username/apeiron](https://github.com/username/apeiron)
- **Issues**: [GitHub Issues](https://github.com/username/apeiron/issues)

---

*Built with ❤️ for the open-source AI community*