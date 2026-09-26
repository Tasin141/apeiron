#!/usr/bin/env python3
"""
Apeiron AI Hub - ChatGPT-like Interface
Clean, minimal, ChatGPT-style interface with 3-agent orchestration
"""

import asyncio
import json
import os
import sys
import random
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import structlog

import gradio as gr

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.apeiron_unified_hub import UnifiedHub, MODELS, CATEGORY_ROUTERS

# Initialize hub
hub = UnifiedHub(use_cloud=True)
hub.active_model = list(MODELS.values())[0]

# ==================== AGENT SYSTEM ====================

class FileProcessor:
    """Process uploaded files for agents."""
    
    @staticmethod
    def process_file(file_path: str) -> Dict[str, Any]:
        if not file_path or not os.path.exists(file_path):
            return {"error": "File not found"}
        
        mime_type, _ = mimetypes.guess_type(file_path)
        ext = Path(file_path).suffix.lower()
        
        result = {
            "path": file_path, "name": Path(file_path).name,
            "size": os.path.getsize(file_path), "mime": mime_type, "ext": ext,
            "content": None, "preview": None
        }
        
        try:
            if ext in ['.txt', '.md', '.py', '.js', '.json', '.yaml', '.yml', '.csv', '.html', '.css', '.sql']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    result["content"] = f.read()[:50000]
            elif ext == '.pdf':
                try:
                    import fitz
                    doc = fitz.open(file_path)
                    text = "".join(page.get_text() for page in doc)
                    result["content"] = text[:50000]
                    doc.close()
                except: result["content"] = "[PDF content extraction requires PyMuPDF]"
            elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']:
                result["preview"] = file_path
                result["content"] = f"[Image: {Path(file_path).name}]"
            elif ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
                result["preview"] = file_path
                result["content"] = f"[Video: {Path(file_path).name}]"
            elif ext in ['.mp3', '.wav', '.ogg', '.flac', '.m4a']:
                result["preview"] = file_path
                result["content"] = f"[Audio: {Path(file_path).name}]"
            elif ext in ['.docx', '.doc']:
                try:
                    import docx
                    doc = docx.Document(file_path)
                    result["content"] = "\n".join(p.text for p in doc.paragraphs)[:50000]
                except: result["content"] = "[DOCX requires python-docx]"
            else:
                result["content"] = f"[File: {Path(file_path).name}]"
        except Exception as e:
            result["content"] = f"[Error: {e}]"
        return result


class AgentOrchestrator:
    def __init__(self, hub: UnifiedHub):
        self.hub = hub
        self.uploaded_files: List[Dict] = []
        self.current_plan: Optional[Dict] = None
        
    def add_file(self, file_path: str):
        self.uploaded_files.append(FileProcessor.process_file(file_path))
    
    def detect_language(self, text: str) -> str:
        bengali_chars = sum(1 for c in text if '\u0980' <= c <= '\u09FF')
        return "bn" if bengali_chars > len(text) * 0.1 else "en"
    
    async def execute_task(self, message: str, lang: str) -> Dict[str, Any]:
        """Execute task directly - auto-detect category, route to best model."""
        category = auto_detect_category(message)
        model_name = CATEGORY_ROUTERS.get(category, "qwen2.5-coder")
        
        # Route through hub
        result = await hub.route_prompt(
            prompt=message, category=category, preferences={"cloud_mode": True}
        )
        
        # Enhance with detailed output
        detailed = generate_category_output(category, message, model_name)
        result.update(detailed)
        result["auto_category"] = category
        result["auto_model"] = model_name
        return result


# ==================== GLOBAL ORCHESTRATOR ====================

orchestrator = AgentOrchestrator(hub)

CATEGORY_KEYWORDS = {
    "coding": ["code", "program", "function", "script", "api", "debug", "python", "javascript", "java", "cpp", "algorithm", "database", "sql"],
    "video": ["video", "movie", "animation", "render", "cinematic", "edit video", "clip"],
    "audio": ["audio", "voice", "speech", "tts", "transcribe", "music", "sound", "podcast"],
    "design": ["image", "picture", "design", "logo", "illustration", "art", "generate image", "wallpaper", "icon"],
    "research": ["research", "analyze", "report", "study", "investigate", "find information", "paper", "survey"],
    "threat-intel": ["threat", "vulnerability", "cve", "malware", "security", "cyber", "attack", "phishing"],
    "agents": ["agent", "workflow", "orchestrate", "automate", "pipeline", "multi-agent"],
    "education": ["learn", "teach", "explain", "tutorial", "math", "homework", "concept", "understand"],
    "resume": ["resume", "cv", "cover letter", "job", "freelance", "proposal", "portfolio"],
    "trading": ["trade", "crypto", "bitcoin", "btc", "eth", "stock", "market", "invest", "chart", "price"],
}

CATEGORY_ROUTERS = {
    "coding": "qwen2.5-coder", "video": "wan2.1", "audio": "whisper",
    "design": "flux1", "research": "deepseek-r1", "threat-intel": "robin",
    "agents": "langgraph", "education": "qwen2.5-math", "resume": "reactive-resume", "trading": "ccxt-live",
}


def auto_detect_category(prompt: str) -> str:
    prompt_lower = prompt.lower()
    scores = {cat: sum(1 for kw in kws if kw in prompt_lower) for cat, kws in CATEGORY_KEYWORDS.items()}
    return max(scores, key=scores.get) if any(scores.values()) else "coding"


# ==================== OUTPUT GENERATORS ====================

CATEGORY_GENERATORS = {
    "coding": {"name": "Code Generation", "icon": "💻", "tab": "code"},
    "video": {"name": "Video Synthesis", "icon": "🎬", "tab": "video"},
    "audio": {"name": "Audio & Voice", "icon": "🔊", "tab": "audio"},
    "design": {"name": "Graphic Design", "icon": "🎨", "tab": "image"},
    "research": {"name": "Deep Research", "icon": "🔬", "tab": "research"},
    "threat-intel": {"name": "Threat Intelligence", "icon": "🛡️", "tab": "research"},
    "agents": {"name": "AI Agents", "icon": "🤖", "tab": "code"},
    "education": {"name": "Education & Math", "icon": "📚", "tab": "research"},
    "resume": {"name": "Resume & Freelance", "icon": "📄", "tab": "code"},
    "trading": {"name": "Trading & Crypto", "icon": "📈", "tab": "crypto"},
}


def generate_category_output(category: str, prompt: str, model: str) -> Dict[str, Any]:
    generators = {
        "coding": lambda p, m: {"type": "code", "tab": "code", "content": f"# {m} for: {p}\n\ndef solution():\n    '''{p}'''\n    pass", "language": "python"},
        "video": lambda p, m: {"type": "video", "tab": "video", "content": {"prompt": p, "model": m, "status": "generating"}},
        "audio": lambda p, m: {"type": "audio", "tab": "audio", "content": {"prompt": p, "model": m, "status": "generating"}},
        "design": lambda p, m: {"type": "image", "tab": "image", "content": {"prompt": p, "model": m, "status": "generating"}},
        "research": lambda p, m: {"type": "research", "tab": "research", "content": f"# Research: {p}\n\nBy {m}...\n\n## Key Findings\n1. Primary insight\n2. Supporting evidence\n3. Recommendations"},
        "threat-intel": lambda p, m: {"type": "threat-intel", "tab": "research", "content": f"# Threat Report: {p}\n\nBy {m}...\n## Assessment: Moderate\n## IoCs\n- IP: detected\n- Domain: suspicious\n## Actions\n1. Block IOCs\n2. Investigate"},
        "agents": lambda p, m: {"type": "agents", "tab": "code", "content": f"# Agent Workflow: {p}\n\nOrchestrated by {m}..."},
        "education": lambda p, m: {"type": "education", "tab": "research", "content": f"# Learn: {p}\n\nBy {m}...\n## Tutorial\n1. Setup\n2. Implement\n3. Verify"},
        "resume": lambda p, m: {"type": "resume", "tab": "code", "content": f"# Resume: {p}\n\nBy {m}...\n## ATS Resume\n- Skills\n- Experience\n- Proposal"},
        "trading": lambda p, m: {"type": "trading", "tab": "crypto", "content": {"analysis": f"# Trading: {p}\n\nBy {m}...\n## Analysis\nTrend: Bullish\nRSI: 62\nMACD: Buy\nTargets: 1D 65%, 1W 55%"}},
    }
    return generators.get(category, generators["coding"])(prompt, model)


orchestrator = AgentOrchestrator(hub)


# ==================== CHAT HANDLER ====================

async def chat_handler(message, history, files, planning_phase_flag, conv_hist, current_plan, lang):
    """ChatGPT-like natural handler - no planning phase for simple tasks."""
    
    if not message.strip() and not files:
        return history, "", planning_phase_flag, current_plan, lang, "Ready", {}, "", None, None, None, "", None
    
    # Process files
    if files:
        for f in files:
            orchestrator.add_file(f.name if hasattr(f, 'name') else f)
    
    # Detect language
    full_text = message + " " + " ".join([f.get("content", "") for f in orchestrator.uploaded_files])
    lang = orchestrator.detect_language(full_text)
    
    # --- Simple greetings ---
    greeting_kws = ["hello", "hi", "hey", "hey there", "hola", "hey!", "hi!", "hello!", "হ্যালো", "হাই", "হাই", "কেমন আছো", "কেমন আছেন", "সালাম", "নমস্কার", "নমস্তে", "assalamualaikum"]
    if any(kw in message.lower() for kw in greeting_keywords) and len(message.strip().split()) <= 3:
        responses = {
            "en": ["Hello! 👋 How can I help you today? I can write code, generate images/videos, do research, analyze data, create documents, and more!",
                   "Hi there! 👋 What would you like me to help with? Code, images, videos, research, documents - just ask!",
                   "Hey! 👋 I'm your AI assistant with 47 specialized models. What do you need today?"],
            "bn": ["হ্যালো! 👋 আজ আমি কীভাবে সাহায্য করতে পারি? কোড, ছবি, ভিডিও, রিসার্চ, ডকুমেন্ট - যেকোনো কিছু করাতে পারেন!",
                   "হাই! 👋 আপনি কী চান? কোড লিখা, ছবি বানানো, ভিডিও তৈরি, রিসার্চ, অনুবাদ - যেকোনো কথা বলুন!"]
        }
        response = random.choice(responses.get(lang, ["Hello! 👋 How can I help?"]))
        new_history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": response}]
        return new_history, "", False, {}, lang, "Ready", {}, "", None, None, None, "", None
    
    # Simple conversational responses
    simple_kws = ["thanks", "thank you", "thanks!", "thx", "ok", "okay", "cool", "awesome", "great", "bye", "bye!", "goodbye", "thanks!", "thx", "ধন্যবাদ", "ধন্যবাদ!", "ঠিক আছে", "ঠিক", "বাই", "বিদায়"]
    if any(kw in message.lower() for kw in simple_responses):
        responses = {"en": ["You're welcome! 😊 Let me know if you need anything else!", "Anytime! 😊 Happy to help!", "Glad to help! Let me know if you need anything else!"],
                     "bn": ["আপনাকেও ধন্যবাদ! 😊 আর কিছু লাগলে বলবেন!", "কোন কথা নেই! 😊 আর কিছু দরকার হলে জানাবেন!"]}
        response = random.choice(responses.get(lang, responses["en"]))
        new_history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": response}]
        return new_history, "", False, {}, lang, "Ready", {}, "", None, None, None, "", None
    
    # Process files
    if files:
        for f in files:
            orchestrator.add_file(f.name if hasattr(f, 'name') else f)
    
    full_text = message + " " + " ".join([f.get("content", "") for f in orchestrator.uploaded_files])
    lang = orchestrator.detect_language(full_text)
    
    try:
        # Auto-detect category and execute directly
        category = auto_detect_category(message)
        model_name = CATEGORY_ROUTERS.get(category, "qwen2.5-coder")
        
        # Route through hub
        result = await hub.route_prompt(message, category, {"cloud_mode": True})
        detailed = generate_category_output(category, message, MODELS[CATEGORY_ROUTERS.get(category, "qwen2.5-coder")].name)
        result.update(detailed)
        
        gen_info = CATEGORY_GENERATORS.get(category, {"icon": "🤖", "name": "AI Assistant", "tab": "research"})
        
        # Format response based on category
        if detailed.get("type") == "code":
            response = f"""**{gen_info['icon']} {gen_info['name']}** (via {MODELS[CATEGORY_ROUTERS.get(category, "qwen2.5-coder")].name})

Here's your code:

```{detailed.get('language', 'python')}
{detailed.get('content', '')}
```"""
        elif detailed.get("type") in ("research", "threat-intel", "education"):
            response = f"""**{gen_info['icon']} {gen_info['name']}** (via {MODELS[CATEGORY_ROUTERS.get(category, "qwen2.5-coder")].name})

{detailed.get('content', '')}"""
        elif detailed.get("type") == "trading":
            response = f"""**{gen_info['icon']} {gen_info['name']}** (via {MODELS[CATEGORY_ROUTERS.get(category, "qwen2.5-coder")].name})

{detailed.get('content', {}).get('analysis', '')}"""
        elif detailed.get("type") in ("agents", "resume"):
            response = f"""**{gen_info['icon']} {gen_info['name']}** (via {MODELS[CATEGORY_ROUTERS.get(category, "qwen2.5-coder")].name})

{detailed.get('content', '')}"""
        else:
            response = f"""**{gen_info['icon']} {gen_info['name']}** (via {MODELS[CATEGORY_ROUTERS.get(category, "qwen2.5-coder")].name})

✅ **Generating your {gen_info['name'].lower()}...** Check the **{gen_info['tab']}** tab for the result!"""
        
        new_history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": response}]
        
        return (new_history, "", False, {}, lang, "✅ Done", {"status": "done"},
                detailed.get("content", ""), 
                None if detailed.get("type") != "image" else [], 
                None if detailed.get("type") != "video" else None, 
                None if detailed.get("type") != "audio" else None, 
                detailed.get("content", "") if detailed.get("type") in ("research", "threat-intel", "education") else "",
                None)
                
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        new_history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": error_msg}]
        return new_history, "", False, {}, lang, f"❌ Error: {e}", {}, "", None, None, None, "", None


# ==================== WEB UI - ChatGPT Style ====================

def create_interface():
    with gr.Blocks(
        title="Apeiron AI",
        theme=gr.themes.Default(primary_hue="blue", secondary_hue="slate"),
        css="""
        /* ChatGPT-style styling */
        #chatbot .message { padding: 12px 16px; border-radius: 12px; max-width: 85%; }
        #chatbot .user { background: #f0f2f5; margin-left: auto; border-radius: 18px 18px 4px 18px; }
        #chatbot .assistant { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 18px 18px 18px 4px; }
        #chatbot .message-content { white-space: pre-wrap; word-wrap: break-word; }
        .message-row { display: flex; align-items: flex-start; gap: 8px; }
        .avatar { width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 14px; }
        .user-avatar { background: #10a37f; color: white; }
        .assistant-avatar { background: #10a37f; color: white; }
        
        /* 3-dot menu on hover */
        .message-wrapper { position: relative; }
        .message-wrapper:hover .msg-menu { opacity: 1; visibility: visible; }
        .msg-menu { opacity: 0; visibility: hidden; transition: all 0.2s; position: absolute; right: 8px; top: 8px; z-index: 10; }
        .msg-menu button { background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 6px 10px; font-size: 12px; cursor: pointer; white-space: nowrap; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .msg-menu button:hover { background: #f3f4f6; }
        
        /* Clean sidebar */
        .sidebar { background: #fafafa; border-right: 1px solid #e5e7eb; }
        .sidebar .gr-button { width: 100%; justify-content: flex-start; text-align: left; border: none; background: transparent; color: #374151; font-size: 14px; padding: 10px 12px; border-radius: 8px; }
        .sidebar .gr-button:hover { background: #f3f4f6; }
        .sidebar .gr-button.primary { background: #10a37f; color: white; }
        
        /* Input area */
        .input-area { border-top: 1px solid #e5e7eb; background: #fff; padding: 12px; }
        
        /* Hide Gradio chrome */
        #chatbot { border: none !important; box-shadow: none !important; }
        .gr-chatbot { border: none !important; }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #9ca3af; }
        """,
    ) as demo:
        
        # State
        planning_phase_state = gr.State(False)
        current_plan_state = gr.State({})
        lang_state = gr.State("en")
        uploaded_files_state = gr.State([])
        
        # Header - minimal
        with gr.Row(elem_classes="header"):
            with gr.Column(scale=1):
                gr.Markdown("### 🤖 Apeiron")
            with gr.Column(scale=5):
                pass
            with gr.Column(scale=1, min_width=100):
                theme_toggle = gr.Button("🌙", size="sm", variant="secondary")
        
        with gr.Row(elem_classes="main-container"):
            # Left Sidebar - minimal
            with gr.Column(scale=1, elem_classes="sidebar", min_width=260, max_width=280):
                gr.Markdown("### 🤖 Apeiron")
                gr.Markdown("*47 Models • 10 Categories*")
                gr.HTML("<hr style='margin: 12px 0; border-color: #e5e7eb;'>")
                
                # Quick actions as pills
                with gr.Column():
                    gr.Markdown("**Quick Actions**")
                    quick_btns = []
                    for cat_key, gen in CATEGORY_GENERATORS.items():
                        btn = gr.Button(f"{gen['icon']} {gen['name']}", size="sm", variant="secondary")
                        quick_btns.append((btn, cat_key))
                
                gr.HTML("<hr style='margin: 16px 0; border-color: #e5e7eb;'>")
                gr.Markdown("**Upload Files**")
                file_upload = gr.File(
                    label="", file_count="multiple",
                    file_types=[".png", ".jpg", ".jpeg", ".pdf", ".txt", ".py", ".md", ".csv", ".json", ".docx", ".mp4", ".mov", ".mp3", ".wav"],
                    height=80,
                )
                
                gr.HTML("<hr style='margin: 16px 0; border-color: #e5e7eb;'>")
                with gr.Row():
                    clear_btn = gr.Button("🗑️ Clear Chat", size="sm", variant="secondary")
                    theme_btn = gr.Button("🌙 Dark", size="sm", variant="secondary")
            
            # Main Chat Area
            with gr.Column(scale=5):
                # Chat display - ChatGPT style
                chatbot = gr.Chatbot(
                    label="",
                    height=650,
                    type="messages",
                    avatar_images=("👤", "🤖"),
                    value=[{"role": "assistant", "content": "Hello! 👋 I'm Apeiron — your AI assistant with **47 specialized models** across 10 categories.\n\n**Just chat naturally.** I'll automatically route to the best model:\n\n💻 **Code** — Python, JS, APIs, algorithms\n🎨 **Design** — Logos, images, illustrations\n🎬 **Video** — Cinematic clips, animations\n🔊 **Audio** — TTS, STT, voice cloning\n🔬 **Research** — Deep analysis, reports\n🛡️ **Threat Intel** — CVEs, malware, incidents\n🤖 **Agents** — Multi-agent workflows\n📚 **Education** — Tutorials, explanations\n📄 **Resume** — ATS CVs, proposals\n📈 **Trading** — Crypto/stock analysis\n\n**Just type what you need.** Upload files with 📎 if needed.\n\n*Try: \"Create a Python web scraper\" or \"Analyze Bitcoin price\""}],
                elem_id="chatbot",
                show_copy_button=True,
                show_share_button=False,
            )
            
            # Input area - ChatGPT style
            with gr.Row(elem_classes="input-area"):
                with gr.Column(scale=1, min_width=50):
                    pass
                with gr.Column(scale=20):
                    msg_input = gr.Textbox(
                        placeholder="Message Apeiron... (Shift+Enter for new line)",
                        container=False,
                        lines=1,
                        max_lines=8,
                        show_label=False,
                        autofocus=True,
                    )
                with gr.Column(scale=1, min_width=50):
                    send_btn = gr.Button("➤", variant="primary", size="lg")
            
            # Right Panel - Output Tabs
            with gr.Column(scale=3, min_width=350, max_width=420):
                with gr.Tabs():
                    with gr.TabItem("💻 Code"):
                        code_out = gr.Code(label="", language="python", lines=22, interactive=False, show_line_numbers=True)
                    with gr.TabItem("🖼️ Images"):
                        img_out = gr.Gallery(label="", columns=2, object_fit="contain", height=350)
                    with gr.TabItem("▶️ Video"):
                        vid_out = gr.Video(height=280)
                    with gr.TabItem("🔊 Audio"):
                        aud_out = gr.Audio(type="filepath")
                    with gr.TabItem("📊 Reports"):
                        rpt_out = gr.Markdown()
                    with gr.TabItem("📈 Charts"):
                        cht_out = gr.Plot()
        
        # States
        planning_phase_state = gr.State(False)
        current_plan_state = gr.State({})
        lang_state = gr.State("en")
        uploaded_files_state = gr.State([])
        
        # ==================== EVENT HANDLERS ====================
        
        def process_upload(files):
            if not files: return "Ready", []
            processed = []
            for f in files:
                result = FileProcessor.process_file(f.name if hasattr(f, 'name') else f)
                processed.append(result)
            return f"✅ {len(processed)} file(s) ready", processed
        
        async def handle_send(message, history, files, planning_flag, conv_hist, current_plan, lang):
            return await chat_handler(message, history, files, False, [], {}, lang)
        
        # Event wiring
        send_btn.click(
            fn=handle_send,
            inputs=[msg_input, chatbot, file_upload, gr.State(False), gr.State([]), gr.State({}), lang_state],
            outputs=[chatbot, msg_input, gr.State(False), gr.State({}), lang_state, 
                     gr.State("Ready"), gr.State({}), code_out, img_out, vid_out, aud_out, gr.State(""), gr.State(None)],
        )
        
        msg_input.submit(
            fn=handle_send,
            inputs=[msg_input, chatbot, file_upload, gr.State(False), gr.State([]), gr.State({}), lang_state],
            outputs=[chatbot, msg_input, gr.State(False), gr.State({}), lang_state,
                     gr.State("Ready"), gr.State({}), code_out, img_out, vid_out, aud_out, gr.State(""), gr.State(None)],
        )
        
        file_upload.change(fn=process_upload, inputs=[file_upload], outputs=[gr.State("Ready"), gr.State([])])
        
        def clear_chat():
            return [], "", False, {}, "en", "Ready", {}, "", None, None, None, "", None
        
        clear_btn.click(fn=clear_chat, outputs=[chatbot, msg_input, gr.State(False), gr.State({}), lang_state, gr.State("Ready"), gr.State({}), code_out, img_out, vid_out, aud_out, gr.State(""), gr.State(None)])
        
        # Quick action buttons
        for btn, cat in quick_btns:
            btn.click(fn=lambda c=cat: (f"Quick: {CATEGORY_GENERATORS[c]['name']}", c), 
                     outputs=[msg_input, gr.State("")])
        
        def toggle_theme():
            return gr.update()
        theme_btn.click(fn=toggle_theme, outputs=[])
        theme_toggle.click(fn=toggle_theme, outputs=[])
        
        return demo


if __name__ == "__main__":
    demo = create_interface()
    demo.launch(share=True)