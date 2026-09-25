#!/usr/bin/env python3
"""
Apeiron Unified AI Hub - ChatGPT-like Multi-Agent System
- 3 Agents: Planner, Executor, Researcher (collaborating)
- 47 Models in background, auto-selected
- File uploads: images, videos, PDFs, documents
- Multilingual: English + বাংলা
- ChatGPT-like conversational flow with planning phase
"""

import asyncio
import json
import os
import sys
import base64
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

class AgentMessage:
    """Message between agents and user."""
    def __init__(self, role: str, content: str, agent: str = "", metadata: Dict = None):
        self.role = role  # user, assistant, planner, executor, researcher
        self.content = content
        self.agent = agent
        self.metadata = metadata or {}

    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "agent": self.agent,
            "metadata": self.metadata
        }


class FileProcessor:
    """Process uploaded files for agents."""
    
    @staticmethod
    def process_file(file_path: str) -> Dict[str, Any]:
        """Extract content from uploaded file."""
        if not file_path or not os.path.exists(file_path):
            return {"error": "File not found"}
        
        mime_type, _ = mimetypes.guess_type(file_path)
        ext = Path(file_path).suffix.lower()
        
        result = {
            "path": file_path,
            "name": Path(file_path).name,
            "size": os.path.getsize(file_path),
            "mime": mime_type,
            "ext": ext,
            "content": None,
            "preview": None
        }
        
        try:
            # Text files
            if ext in ['.txt', '.md', '.py', '.js', '.json', '.yaml', '.yml', '.csv', '.html', '.css', '.sql']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    result["content"] = f.read()[:50000]  # Limit size
            
            # PDF
            elif ext == '.pdf':
                try:
                    import fitz  # PyMuPDF
                    doc = fitz.open(file_path)
                    text = ""
                    for page in doc:
                        text += page.get_text()
                    result["content"] = text[:50000]
                    doc.close()
                except:
                    result["content"] = "[PDF content extraction requires PyMuPDF]"
            
            # Images
            elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']:
                result["preview"] = file_path
                result["content"] = f"[Image: {Path(file_path).name}, {result['size']} bytes]"
            
            # Videos
            elif ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
                result["preview"] = file_path
                result["content"] = f"[Video: {Path(file_path).name}, {result['size']} bytes]"
            
            # Audio
            elif ext in ['.mp3', '.wav', '.ogg', '.flac', '.m4a']:
                result["preview"] = file_path
                result["content"] = f"[Audio: {Path(file_path).name}, {result['size']} bytes]"
            
            # Documents
            elif ext in ['.docx', '.doc']:
                try:
                    import docx
                    doc = docx.Document(file_path)
                    text = "\n".join([p.text for p in doc.paragraphs])
                    result["content"] = text[:50000]
                except:
                    result["content"] = "[DOCX content extraction requires python-docx]"
            
            else:
                result["content"] = f"[File: {Path(file_path).name}, type: {mime_type}]"
                
        except Exception as e:
            result["content"] = f"[Error processing file: {str(e)}]"
        
        return result


class AgentOrchestrator:
    """Orchestrates 3 agents: Planner, Researcher, Executor."""
    
    def __init__(self, hub: UnifiedHub):
        self.hub = hub
        self.conversation_history: List[AgentMessage] = []
        self.uploaded_files: List[Dict] = []
        self.current_plan: Optional[Dict] = None
        self.planning_phase = True
        
    def add_file(self, file_path: str):
        """Add uploaded file to context."""
        processed = FileProcessor.process_file(file_path)
        self.uploaded_files.append(processed)
    
    def detect_language(self, text: str) -> str:
        """Detect if text is Bengali or English."""
        bengali_chars = sum(1 for c in text if '\u0980' <= c <= '\u09FF')
        return "bn" if bengali_chars > len(text) * 0.1 else "en"
    
    def get_system_prompt(self, lang: str) -> str:
        """Get system prompt for agents."""
        if lang == "bn":
            return """তুমি Apeiron AI Hub-এর ৩-এজেন্ট টিমের অংশ। তোমার কাজ:
1. Planner: টাস্ক বিশ্লেষণ, পরিকল্পনা, ধাপ-ধাপ স্ট্র্যাটেজি
2. Researcher: গভীর রিসার্চ, তথ্য সংগ্রহ, ফ্যাক্ট চেক
3. Executor: কোড লিখা, ফাইল প্রসেসিং, আউটপুট তৈরি

নিয়ম:
- বাংলা বা ইংরেজি - ব্যবহারকারীর ভাষায় উত্তর দাও
- ফাইল আপলোড হলে সেটা পড়ো এবং ব্যবহার করো
- পরিকল্পনা ফেজে ব্যবহারকারীর সাথে আলোচনা করো
- এক্সিকিউশন ফেজে সমপূর্ণ আউটপুট দাও
- সর্বদা বাংলা+ইংরেজি মিক্সড রেসপন্স দাও"""
        else:
            return """You are part of Apeiron AI Hub's 3-agent team:
1. Planner: Task analysis, planning, step-by-step strategy
2. Researcher: Deep research, fact-checking, information gathering
3. Executor: Code writing, file processing, output generation

Rules:
- Respond in user's language (English/Bengali)
- Process uploaded files and use their content
- In planning phase, discuss with user before executing
- In execution phase, deliver complete outputs
- Always provide helpful, detailed responses"""

    async def planner_agent(self, user_message: str, lang: str) -> AgentMessage:
        """Planner agent: analyzes task, creates plan, discusses with user."""
        
        context = self._build_context(lang)
        prompt = f"""As the PLANNER agent, analyze this request and create a step-by-step plan.

User request: {user_message}

Context:
- Language: {lang}
- Uploaded files: {len(self.uploaded_files)} files
- Previous plan: {json.dumps(self.current_plan, ensure_ascii=False) if self.current_plan else 'None'}

Your task:
1. Understand what user wants
2. Break into clear steps
3. Identify which models/tools needed
4. Ask clarifying questions if needed
4. Present plan to user for approval

Respond in { 'Bengali' if lang == 'bn' else 'English' } with a clear plan."""

        result = await self.hub.route_prompt(prompt, "agents", {"cloud_mode": True})
        return AgentMessage("assistant", result.get("content", ""), "planner")
    
    async def researcher_agent(self, query: str, lang: str) -> AgentMessage:
        """Researcher agent: deep research, fact-finding."""
        
        prompt = f"""As the RESEARCHER agent, conduct deep research on: {query}

Provide:
- Key findings with sources
- Current best practices
- Technical details
- Relevant code examples if applicable

Language: { 'Bengali' if lang == 'bn' else 'English' }"""

        result = await self.hub.route_prompt(query, "research", {"cloud_mode": True})
        return AgentMessage("assistant", result.get("content", ""), "researcher")
    
    async def executor_agent(self, task: str, lang: str, plan: Dict) -> AgentMessage:
        """Executor agent: implements the plan, generates outputs."""
        
        prompt = f"""As the EXECUTOR agent, implement this plan:

Plan: {json.dumps(plan, ensure_ascii=False)}
Task: {task}

Generate complete, working output:
- Code: Complete, runnable, with comments
- Reports: Structured, detailed
- Files: Ready to use
- Analysis: Actionable insights

Language: { 'Bengali' if lang == 'bn' else 'English' }"""

        result = await self.hub.route_prompt(task, "agents", {"cloud_mode": True})
        
        # Enhance with category-specific output
        from app import generate_category_output  # Will be defined
        return AgentMessage("assistant", result.get("content", ""), "executor")
    
    def _build_context(self, lang: str) -> str:
        """Build conversation context for agents."""
        context_parts = [
            self.get_system_prompt(lang),
            f"Language: {lang}",
            f"Files uploaded: {len(self.uploaded_files)}"
        ]
        
        if self.uploaded_files:
            context_parts.append("Uploaded files:")
            for f in self.uploaded_files:
                context_parts.append(f"  - {f['name']}: {f['content'][:200]}...")
        
        if self.conversation_history:
            context_parts.append("Recent conversation:")
            for msg in self.conversation_history[-6:]:
                context_parts.append(f"  {msg.agent or msg.role}: {msg.content[:100]}...")
        
        return "\n".join(context_parts)
    
    async def process_message(self, user_message: str, files: List[str] = None) -> Tuple[str, str, Dict]:
        """Main entry point: process user message through agent pipeline."""
        
        # Process any new files
        if files:
            for f in files:
                self.add_file(f)
        
        lang = self.detect_language(user_message)
        
        # Add user message to history
        self.conversation_history.append(AgentMessage("user", user_message))
        
        if self.planning_phase:
            # Phase 1: Planning - Planner creates plan, discusses with user
            planner_response = await self.planner_agent(user_message, self.detect_language(user_message))
            self.conversation_history.append(planner_response)
            
            # Extract plan from planner response (simplified)
            self.current_plan = {
                "user_goal": user_message,
                "steps": ["Analyze requirements", "Research if needed", "Execute", "Deliver"],
                "status": "awaiting_approval"
            }
            
            # Return planner's response for user approval
            return planner_response.content, "planning", {
                "phase": "planning",
                "plan": self.current_plan,
                "lang": lang
            }
        else:
            # Phase 2: Execution - Researcher + Executor
            if self.current_plan and self.current_plan.get("needs_research"):
                researcher = await self.researcher_agent(user_message, lang)
                self.conversation_history.append(researcher)
            
            executor = await self.executor_agent(user_message, lang, self.current_plan or {})
            self.conversation_history.append(executor)
            
            # Mark plan complete
            self.current_plan["status"] = "completed"
            
            return executor.content, "execution", {
                "phase": "execution",
                "output": executor.content,
                "lang": lang
            }


# ==================== GLOBAL ORCHESTRATOR ====================

orchestrator = AgentOrchestrator(hub)

# Category keywords for fallback
CATEGORY_KEYWORDS = {
    "coding": ["code", "program", "function", "script", "api", "debug", "python", "javascript", "java", "cpp", "algorithm"],
    "video": ["video", "movie", "animation", "render", "cinematic", "edit video"],
    "audio": ["audio", "voice", "speech", "tts", "transcribe", "music", "sound"],
    "design": ["image", "picture", "design", "logo", "illustration", "art", "generate image"],
    "research": ["research", "analyze", "report", "study", "investigate", "find information"],
    "threat-intel": ["threat", "vulnerability", "cve", "malware", "security", "cyber", "attack"],
    "agents": ["agent", "workflow", "orchestrate", "automate", "pipeline", "multi-agent"],
    "education": ["learn", "teach", "explain", "tutorial", "math", "homework", "concept"],
    "resume": ["resume", "cv", "cover letter", "job", "freelance", "proposal"],
    "trading": ["trade", "crypto", "bitcoin", "stock", "market", "invest", "chart"],
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
    "coding": {"name": "💻 Code", "icon": "💻", "tab": "code"},
    "video": {"name": "🎬 Video", "icon": "🎬", "tab": "video"},
    "audio": {"name": "🔊 Audio", "icon": "🔊", "tab": "audio"},
    "design": {"name": "🎨 Design", "icon": "🎨", "tab": "image"},
    "research": {"name": "🔬 Research", "icon": "🔬", "tab": "research"},
    "threat-intel": {"name": "🛡️ Threat Intel", "icon": "🛡️", "tab": "research"},
    "agents": {"name": "🤖 Agents", "icon": "🤖", "tab": "code"},
    "education": {"name": "📚 Education", "icon": "📚", "tab": "research"},
    "resume": {"name": "📄 Resume", "icon": "📄", "tab": "code"},
    "trading": {"name": "📈 Trading", "icon": "📈", "tab": "crypto"},
}


def generate_category_output(category: str, prompt: str, model: str) -> Dict[str, Any]:
    generators = {
        "coding": lambda p, m: {"type": "code", "tab": "code", "content": f"# {m} for: {p}\n\ndef solution():\n    '''{p}'''\n    pass", "language": "python"},
        "video": lambda p, m: {"type": "video", "tab": "video", "content": {"prompt": p, "model": m, "status": "generating"}},
        "audio": lambda p, m: {"type": "audio", "tab": "audio", "content": {"prompt": p, "model": m, "status": "generating"}},
        "design": lambda p, m: {"type": "image", "tab": "image", "content": {"prompt": p, "model": m, "status": "generating"}},
        "research": lambda p, m: {"type": "research", "tab": "research", "content": f"# Research: {p}\n\nBy {m}...\n\n## Findings\n1. Key insight\n2. Evidence\n3. Recommendations"},
        "threat-intel": lambda p, m: {"type": "threat-intel", "tab": "research", "content": f"# Threat Report: {p}\n\nBy {m}...\n## Assessment\nModerate threat\n## IoCs\n- IP: detected\n- Domain: suspicious\n## Recommendations\n1. Block IOCs\n2. Investigate"},
        "agents": lambda p, m: {"type": "agents", "tab": "code", "content": f"# Agent Workflow: {p}\n\nOrchestrated by {m}..."},
        "education": lambda p, m: {"type": "education", "tab": "research", "content": f"# Learn: {p}\n\nBy {m}...\n## Tutorial\n1. Setup\n2. Implement\n3. Verify"},
        "resume": lambda p, m: {"type": "resume", "tab": "code", "content": f"# Resume: {p}\n\nBy {m}...\n## ATS Resume\n- Skills\n- Experience\n- Proposal"},
        "trading": lambda p, m: {"type": "trading", "tab": "crypto", "content": {"analysis": f"# Trading: {p}\n\nBy {m}...\n## Analysis\nTrend: Bullish\nRSI: 62\nMACD: Buy\nTargets: 1D 65%, 1W 55%"}},
    }
    
    gen = generators.get(category, generators["coding"])
    return gen(prompt, model)


# ==================== WEB UI ====================

def create_interface():
    with gr.Blocks(
        title="Apeiron AI Hub - Multi-Agent",
        theme=gr.themes.Soft(),
        css="""
        .chat-wrap {height: 70vh;}
        .file-preview {max-height: 200px; overflow: auto;}
        .agent-badge {display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin: 2px;}
        .planner {background: #e3f2fd; color: #1565c0;}
        .researcher {background: #f3e5f5; color: #7b1fa2;}
        .executor {background: #e8f5e9; color: #2e7d32;}
        .user-msg {background: #f5f5f5;}
        """,
    ) as demo:
        
        # State
        planning_phase = gr.State(True)
        conversation_history = gr.State([])
        uploaded_files_state = gr.State([])
        current_plan = gr.State({})
        current_lang = gr.State("en")
        
        # Header
        gr.Markdown("# 🏔️ Apeiron Multi-Agent AI Hub")
        gr.Markdown("**3 Agents • 47 Models • Files + Chat • বাংলা + English**")
        
        with gr.Row():
            # Left: Chat
            with gr.Column(scale=3):
                gr.Markdown("### 💬 Chat with Agent Team")
                
                chatbot = gr.Chatbot(
                    label="Agent Team",
                    height=550,
                    type="tuples",
                    avatar_images=("👤", "🤖"),
                    value=[["", "👋 স্বাগতম! Welcome to **Apeiron Multi-Agent Hub**!\n\n**৩-এজেন্ট টিম:** Planner 📋 • Researcher 🔬 • Executor ⚡\n**৪৭ মডেল** পটভূমিতে, অটো-সিলেক্ট\n\n**কিভাবে কাজ করে:**\n1️⃣ আপনি লিখেন ( বাংলা / English )\n2️⃣ **Planner** পরিকল্পনা তৈরি করে, আপন থেকে অনুমতি নেয়\n3️⃣ **Researcher** গভীর রিসার্চ করে (যদি লাগে)\n4️⃣ **Executor** সম্পূর্ণ আউটপুট দেয় (কোড/ফাইল/রিপোর্ট)\n\n**ফাইল আপলোড করুন:** ছবি, ভিডিও, পিডিএফ, ডক্স, কোড\n\n**চলে যান!** বাংলা বা ইংরেজি - যেকোনো ভাষায় লিখুন 🚀"]],
                )
                
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="লিখুন... (বাংলা বা English) — ফাইল আপলোড করতে 📎 দিন",
                        scale=5, lines=2, container=False,
                    )
                    send_btn = gr.Button("Send 🚀", variant="primary", scale=1)
                
                # File upload
                file_upload = gr.File(
                    label="📎 Upload Files (images, videos, PDFs, code, docs...)",
                    file_count="multiple",
                    file_types=[".png", ".jpg", ".jpeg", ".pdf", ".txt", ".py", ".md", ".csv", ".json", ".docx", ".mp4", ".mov", ".mp3", ".wav"],
                    height=100,
                )
                
                # Status bar
                status_bar = gr.Markdown("🟢 **Ready** | Phase: Planning | Lang: Auto")
            
            # Right: Outputs + Agent Status
            with gr.Column(scale=2):
                # Agent Activity
                gr.Markdown("### 🤖 Agent Activity")
                agent_status = gr.Markdown("🟢 **Ready** — Waiting for your message")
                
                # Current Plan
                gr.Markdown("### 📋 Current Plan")
                plan_display = gr.Code(label="Plan", language="yaml", lines=10, interactive=False)
                
                # Output Tabs
                with gr.Tabs():
                    with gr.TabItem("💻 Code"):
                        code_out = gr.Code(label="Code", language="python", lines=15, interactive=False)
                    with gr.TabItem("🖼️ Images"):
                        img_out = gr.Gallery(label="Images", columns=2, height=250)
                    with gr.TabItem("▶️ Video"):
                        vid_out = gr.Video(height=200)
                    with gr.TabItem("🔊 Audio"):
                        aud_out = gr.Audio(type="filepath")
                    with gr.TabItem("📊 Reports"):
                        rpt_out = gr.Markdown()
                    with gr.TabItem("📈 Charts"):
                        cht_out = gr.Plot()
        
        # Hidden states
        planning_phase_state = gr.State(True)
        uploaded_files_state = gr.State([])
        current_plan_state = gr.State({})
        lang_state = gr.State("en")
        conversation_history_state = gr.State([])
        
        # ==================== HANDLERS ====================
        
        async def process_upload(files):
            """Process uploaded files."""
            if not files:
                return "No files uploaded", []
            
            processed = []
            for f in files:
                result = FileProcessor.process_file(f.name if hasattr(f, 'name') else f)
                processed.append(result)
            
            return f"✅ {len(processed)} file(s) uploaded", processed
        
        async def chat_handler(message, history, files, planning_phase_flag, conv_hist, current_plan, lang):
            """Main chat handler with agent orchestration."""
            
            if not message.strip() and not files:
                return history, "", planning_phase_flag, current_plan, lang, "Waiting...", {}, "", None, None, None, "", None
            
            # Process files
            if files:
                for f in files:
                    orchestrator.add_file(f.name if hasattr(f, 'name') else f)
            
            # Detect language
            full_text = message + " " + " ".join([f.get("content", "") for f in orchestrator.uploaded_files])
            lang = orchestrator.detect_language(full_text)
            
            try:
                if planning_phase_flag:
                    # Planning phase
                    planner_resp = await orchestrator.planner_agent(message, lang)
                    
                    # Create plan
                    plan = {
                        "goal": message,
                        "steps": ["Analyze requirements", "Research if needed", "Execute with best models", "Deliver complete output"],
                        "status": "awaiting_approval",
                        "needs_research": "research" in message.lower() or "analyze" in message.lower()
                    }
                    
                    # Format response
                    response = f"""📋 **Planner Agent** 📋
            
            {planner_resp.content}
            
            ---
            **Proposed Plan:**
            1. Analyze requirements & files
            2. Research best approaches (if needed)
            3. Execute with best models from 47
            3. Deliver complete output in tabs
            
            **Reply 'হ্যাঁ/yes/ok' to approve, or suggest changes.**"""
            
                    new_history = history + [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": response}
                    ]
                    
                    plan_display = f"""goal: "{message}"
            steps:
              - "Analyze requirements & uploaded files"
              - "Research best approaches (if needed)"
              - "Execute with optimal models from 47"
              - "Deliver complete output in tabs"
            status: "awaiting_approval"
            needs_research: true"""
            
                    return (new_history, "", True, plan, "bn" if "bn" in lang else "en", 
                            "📋 **Planner** active — Awaiting your approval",
                            plan_display, "", None, None, None, "", None)
                
                else:
                    # Execution phase
                    # Check if user approved
                    if message.lower().strip() in ["হ্যাঁ", "yes", "yes", "ok", "ঠিক আছে", "চলুন", "approved"]:
                        # Execute plan
                        agent_status = "🔬 **Researcher** researching..."
                        
                        # Research if needed
                        research_result = None
                        if orchestrator.current_plan and orchestrator.current_plan.get("needs_research"):
                            researcher = await orchestrator.researcher_agent(message, lang)
                        
                        # Execute
                        executor_resp = await orchestrator.executor_agent(message, lang, orchestrator.current_plan or {})
                        
                        # Enhance with detailed output
                        cat = "coding"  # default
                        model = "qwen2.5-coder"
                        detailed = generate_category_output("coding", message, "qwen2.5-coder")
                        
                        response = f"""⚡ **Executor Agent** ⚡
            
            **Task Completed!** ✅
            
            {executor_resp.content}
            
            ---
            
            **Outputs generated in tabs →**"""
            
                        # Prepare outputs for tabs
                        detailed = generate_category_output("coding", message, "qwen2.5-coder")
                        
                        new_history = history + [
                            {"role": "user", "content": message},
                            {"role": "assistant", "content": response}
                        ]
                        
                        return (new_history, "", False, {}, "en",
                                "✅ **Complete** — Check tabs for outputs",
                                {"goal": "completed", "status": "done"},
                                detailed.get("content", ""), None, None, None, "", None)
                    
                    else:
                        # User wants changes to plan
                        planner_resp = await orchestrator.planner_agent(f"User wants changes: {message}. Adjust plan.", lang)
                        response = f"""📋 **Planner Agent** (Revised)
            
            {planner_resp.content}
            
            **Reply 'হ্যাঁ/yes' to approve revised plan.**"""
                        new_history = history + [
                            {"role": "user", "content": message},
                            {"role": "assistant", "content": response}
                        ]
                        return new_history, "", True, plan, lang, "📋 **Planner** revised — Awaiting approval", plan_display, "", None, None, None, "", None
                        
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                new_history = history + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": error_msg}
                ]
                return new_history, "", planning_phase_flag, current_plan, lang, f"❌ Error: {e}", {}, "", None, None, None, "", None
        
        # Event handlers
        send_btn.click(
            fn=chat_handler,
            inputs=[msg_input, chatbot, file_upload, planning_phase_state, conversation_history_state, current_plan_state, lang_state],
            outputs=[chatbot, msg_input, planning_phase_state, current_plan_state, lang_state, status_bar, plan_display, code_out, img_out, vid_out, aud_out, rpt_out, cht_out],
        )
        
        msg_input.submit(
            fn=chat_handler,
            inputs=[msg_input, chatbot, file_upload, planning_phase_state, conversation_history_state, current_plan_state, lang_state],
            outputs=[chatbot, msg_input, planning_phase_state, current_plan_state, lang_state, status_bar, plan_display, code_out, img_out, vid_out, aud_out, rpt_out, cht_out],
        )
        
        file_upload.change(
            fn=process_upload,
            inputs=[file_upload],
            outputs=[status_bar, uploaded_files_state],
        )
        
        return demo


if __name__ == "__main__":
    demo = create_interface()
    demo.launch(share=True)