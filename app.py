#!/usr/bin/env python3
"""
Apeiron — ChatGPT-like Universal AI Assistant
Clean, invisible 3-agent orchestration • 47 models • ChatGPT-style UX
"""

import asyncio, os, sys, random, mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog, gradio as gr

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.apeiron_unified_hub import UnifiedHub, MODELS, CATEGORY_ROUTERS

# ─── Core ────────────────────────────────────────────────────────────────
hub = UnifiedHub(use_cloud=True); hub.active_model = list(MODELS.values())[0]

# ─── Routing ─────────────────────────────────────────────────────────────
KW = {
    "code":["code","program","function","script","api","debug","python","javascript","java","cpp","go","rust","sql","database","algorithm","docker","k8s"],
    "video":["video","movie","animation","render","cinematic","edit video","clip","short","reel"],
    "audio":["audio","voice","speech","tts","transcribe","music","sound","podcast","voiceover"],
    "design":["image","picture","design","logo","illustration","art","generate image","wallpaper","icon","ui","ux","banner","poster"],
    "research":["research","analyze","report","study","investigate","find","paper","survey","trend","literature"],
    "threat":["threat","vulnerability","cve","malware","security","cyber","attack","phishing","pentest","incident"],
    "education":["learn","teach","explain","tutorial","math","homework","concept","understand","lesson","course"],
    "resume":["resume","cv","cover letter","job","freelance","proposal","portfolio","linkedin","interview","ats"],
    "trading":["trade","crypto","bitcoin","btc","eth","stock","market","invest","chart","price","technical","rsi","macd"],
}
ROUTER = {"code":"qwen2.5-coder","video":"wan2.1","audio":"whisper","design":"flux1",
          "research":"deepseek-r1","threat":"robin","education":"qwen2.5-math",
          "resume":"reactive-resume","trading":"ccxt-live"}
CATS = {"code":("💻","Code"),"video":("🎬","Video"),"audio":("🔊","Audio"),
        "design":("🎨","Design"),"research":("🔬","Research"),"threat":("🛡️","Threat Intel"),
        "education":("📚","Learn"),"resume":("📄","Resume"),"trading":("📈","Trading")}

def cat(t):
    pl=t.lower(); sc={c:sum(k in pl for k in kws) for c,kws in KEYWORDS.items()}
    return max(sc,key=sc.get) if any(sc.values()) else "code"

# ─── Generators ──────────────────────────────────────────────────────────
GEN = {
    "code":lambda p,m:{"type":"code","tab":"code","content":f"# {m} for: {p}\n\ndef solution():\n    '''{p}'''\n    pass","lang":"python"},
    "video":lambda p,m:{"type":"video","tab":"video","content":{"prompt":p,"model":m,"status":"generating"}},
    "audio":lambda p,m:{"type":"audio","tab":"audio","content":{"prompt":p,"model":m,"status":"generating"}},
    "design":lambda p,m:{"type":"image","tab":"image","content":{"prompt":p,"model":m,"status":"generating"}},
    "research":lambda p,m:{"type":"research","tab":"research","content":f"# Research: {p}\n\n## Key Findings\n1. Primary insight\n2. Evidence\n3. Recommendations\n\n*By {MODELS['deepseek-r1'].name}*"},
    "threat":lambda p,m:{"type":"research","tab":"research","content":f"# Threat Report\n\n## Assessment: Moderate\n## IoCs\n- IP: detected\n## Actions\n1. Block IOCs\n2. Investigate\n\n*By {MODELS['robin'].name}*"},
    "education":lambda p,m:{"type":"research","tab":"research","content":f"# Tutorial: {p}\n\n## Steps\n1. Setup\n2. Implement\n3. Verify\n\n*By {MODELS['qwen2.5-math'].name}*"},
    "resume":lambda p,m:{"type":"code","tab":"code","content":f"# Resume: {p}\n\n## Summary\nExpert in {p}...\n## Skills\n- {p}: Expert\n## Proposal\n## Timeline\n|Phase|Duration|\n|---|---|\n|Discovery|1wk|\n|Build|4wk|\n|Total|5wk|"},
    "trading":lambda p,m:{"type":"trading","tab":"crypto","content":{"analysis":f"# Trading\n\nTrend: Bullish\nRSI: 62 | MACD: Buy\nTargets: 1D 65% | 1W 55%\n\n*Not financial advice*"}},
}

# ─── File Processor ──────────────────────────────────────────────────────
class Files:
    @staticmethod
    def proc(path):
        if not path or not os.path.exists(path): return {"error":"not found"}
        mime,_=mimetypes.guess_type(path); ext=Path(path).suffix.lower()
        r={"path":path,"name":Path(path).name,"size":os.path.getsize(path),"mime":mimetypes.guess_type(path)[0],"ext":ext,"content":None,"preview":None}
        try:
            ext=Path(path).suffix.lower()
            if ext in ['.txt','.md','.py','.js','.json','.yaml','.yml','.csv','.html','.css','.sql']:
                with open(path,'r',encoding='utf-8') as f: return {**r,"content":f.read()[:50000]}
            elif Path(path).suffix.lower()=='.pdf':
                try: import fitz; d=fitz.open(path); return {**r,"content":"".join(p.get_text() for p in d)[:50000]}
                except: return {**r,"content":"[PDF needs PyMuPDF]"}
            elif Path(path).suffix.lower() in ['.png','.jpg','.jpeg','.gif','.webp','.bmp']:
                return {**r,"preview":file_path,"content":f"[Image: {Path(file_path).name}]"}
            elif r["ext"] in ['.mp4','.mov','.avi','.mkv','.webm']:
                return {**r,"preview":file_path,"content":f"[Video: {Path(path).name}]"}
            elif r["ext"] in ['.mp3','.wav','.ogg','.flac','.m4a']:
                return {**r,"preview":file_path,"content":f"[Audio: {Path(path).name}]"}
            elif r["ext"] in ['.docx','.doc']:
                try: import docx; d=docx.Document(file_path); return {**r,"content":"\n".join(p.text for p in d.paragraphs)[:50000]}
                except: return {**r,"content":"[DOCX needs python-docx]"}
            else: return {**r,"content":f"[File: {Path(file_path).name}]"}
        except Exception as e: return {**r,"content":f"[Error: {e}]"}

# ─── Routing ─────────────────────────────────────────────────────────────
KEYWORDS = {
    "code":["code","program","function","script","api","debug","python","javascript","java","cpp","go","rust","sql","database","algorithm","docker","k8s"],
    "video":["video","movie","animation","render","cinematic","edit video","clip","short","reel"],
    "audio":["audio","voice","speech","tts","transcribe","music","sound","podcast","voiceover"],
    "design":["image","picture","design","logo","illustration","art","generate image","wallpaper","icon","ui","ux","banner","poster"],
    "research":["research","analyze","report","study","investigate","find","paper","survey","trend","literature"],
    "threat":["threat","vulnerability","cve","malware","security","cyber","attack","phishing","pentest","incident"],
    "education":["learn","teach","explain","tutorial","math","homework","concept","understand","lesson","course"],
    "resume":["resume","cv","cover letter","job","freelance","proposal","portfolio","linkedin","interview","ats"],
    "trading":["trade","crypto","bitcoin","btc","eth","stock","market","invest","chart","price","technical","rsi","macd"],
}
ROUTER = {"code":"qwen2.5-coder","video":"wan2.1","audio":"whisper","design":"flux1",
          "research":"deepseek-r1","threat":"robin","education":"qwen2.5-math",
          "resume":"reactive-resume","trading":"ccxt-live"}

def cat(t):
    pl=t.lower(); sc={c:sum(k in pl for k in kws) for c,kws in KEYWORDS.items()}
    return max(sc,key=sc.get) if any(sc.values()) else "code"

def gen(cat, prompt, model): return GEN.get(cat, GEN["code"])(prompt, model)

# ─── File Processor ──────────────────────────────────────────────────────
def proc_file(path):
    if not path or not os.path.exists(path): return {"error":"not found"}
    mime,_=mimetypes.guess_type(path); ext=Path(path).suffix.lower()
    r={"path":path,"name":Path(path).name,"size":os.path.getsize(path),"mime":mimetypes.guess_type(path)[0],"ext":ext,"content":None,"preview":None}
    try:
        ext=Path(path).suffix.lower()
        if ext in ['.txt','.md','.py','.js','.json','.yaml','.yml','.csv','.html','.css','.sql']:
            with open(path,'r',encoding='utf-8') as f: return {**r,"content":f.read()[:50000]}
        elif Path(path).suffix.lower()=='.pdf':
            try: import fitz; d=fitz.open(path); return {**r,"content":"".join(p.get_text() for p in d)[:50000]}
            except: return {**r,"content":"[PDF needs PyMuPDF]"}
        elif Path(path).suffix.lower() in ['.png','.jpg','.jpeg','.gif','.webp','.bmp']:
            return {**r,"preview":path,"content":f"[Image: {Path(path).name}]"}
        elif Path(path).suffix.lower() in ['.mp4','.mov','.avi','.mkv','.webm']:
            return {**r,"preview":path,"content":f"[Video: {Path(path).name}]"}
        elif Path(path).suffix.lower() in ['.mp3','.wav','.ogg','.flac','.m4a']:
            return {**r,"preview":path,"content":f"[Audio: {Path(path).name}]"}
        elif ext in ['.docx','.doc']:
            try: import docx; d=docx.Document(path); return {**r,"content":"\n".join(p.text for p in d.paragraphs)[:50000]}
            except: return {**r,"content":"[DOCX needs python-docx]"}
        else: return {**r,"content":f"[File: {Path(path).name}]"}
    except Exception as e: return {"error":str(e)}

# ─── Hub ────────────────────────────────────────────────────────────────
import asyncio, os, sys, random, mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog, gradio as gr
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.apeiron_unified_hub import UnifiedHub, MODELS, CATEGORY_ROUTERS

hub = UnifiedHub(use_cloud=True); hub.active_model = list(MODELS.values())[0]
files_store = []

# ─── Helpers ────────────────────────────────────────────────────────────
def lang(t): return "bn" if sum(1 for c in t if '\u0980'<=c<='\u09FF')>len(t)*0.1 else "en"
def is_greeting(t): return any(k in t.lower() for k in ["hello","hi","hey","hey!","hi!","hello!","hola","হ্যালো","হাই","হাই","কেমন আছো","কেমন আছেন","সালাম","নমস্কার","নমস্তে","assalamualaikum"]) and len(t.strip().split())<=3

def simple_reply(t):
    sr={"en":["thanks","thank you","thanks!","thx","ok","okay","cool","awesome","great","bye","bye!","goodbye","thx"],
        "bn":["ধন্যবাদ","ধন্যবাদ!","ঠিক আছে","ঠিক","বাই","বিদায়"]}
    return any(k in t.lower() for k in simple_responses.get(detect_lang(t), simple_responses["en"]))

GREET_RESP = {
    "en":["Hello! 👋 How can I help? I can write code, generate images/videos, research, analyze data, create documents, and more!",
          "Hi! 👋 What would you like me to help with? Code, images, videos, research, documents — just ask!",
          "Hey! 👋 I'm your AI assistant with 47 specialized models. What do you need today?"],
    "bn":["হ্যালো! 👋 আজ আমি কীভাবে সাহায্য করতে পারি? কোড, ছবি, ভিডিও, রিসার্চ, ডকুমেন্ট — যেকোনো কিছু করাতে পারেন!",
          "হাই! 👋 আপনি কী চান? কোড লিখা, ছবি বানানো, ভিডিও তৈরি, রিসার্চ, অনুবাদ — যেকোনো কথা বলুন!"]
}
SIMPLE_REP = {"en":["You're welcome! 😊 Let me know if you need anything!","Anytime! 😊 Happy to help!"],
              "bn":["আপনাকেও ধন্যবাদ! 😊 আর কিছু লাগলে বলবেন!"]}

def detect_lang(t): return "bn" if sum(1 for c in t if '\u0980'<=c<='\u09FF')>len(t)*0.1 else "en"

# ─── File Processor ─────────────────────────────────────────────────────
import os, mimetypes
from pathlib import Path
def proc_file(path):
    if not path or not os.path.exists(path): return {"error":"not found"}
    mime,_=mimetypes.guess_type(path); ext=Path(path).suffix.lower()
    r={"path":path,"name":Path(path).name,"size":os.path.getsize(path),"mime":mimetypes.guess_type(path)[0],"ext":ext,"content":None,"preview":None}
    try:
        ext=Path(path).suffix.lower()
        if ext in ['.txt','.md','.py','.js','.json','.yaml','.yml','.csv','.html','.css','.sql']:
            with open(path,'r',encoding='utf-8') as f: return {**r,"content":f.read()[:50000]}
        elif Path(path).suffix.lower()=='.pdf':
            try: import fitz; d=fitz.open(path); return {**r,"content":"".join(p.get_text() for p in d)[:50000]}
            except: return {**r,"content":"[PDF needs PyMuPDF]"}
        elif Path(path).suffix.lower() in ['.png','.jpg','.jpeg','.gif','.webp','.bmp']:
            return {**r,"preview":path,"content":f"[Image: {Path(path).name}]"}
        elif Path(path).suffix.lower() in ['.mp4','.mov','.avi','.mkv','.webm']:
            return {**r,"preview":path,"content":f"[Video: {Path(path).name}]"}
        elif Path(path).suffix.lower() in ['.mp3','.wav','.ogg','.flac','.m4a']:
            return {**r,"preview":path,"content":f"[Audio: {Path(path).name}]"}
        elif Path(path).suffix.lower() in ['.docx','.doc']:
            try: import docx; d=docx.Document(path); return {**r,"content":"\n".join(p.text for p in d.paragraphs)[:50000]}
            except: return {**r,"content":"[DOCX needs python-docx]"}
        else: return {**r,"content":f"[File: {Path(path).name}]"}
    except Exception as e: return {"error":str(e)}

# ─── Global State ──────────────────────────────────────────────────────
import asyncio, os, sys, random, mimetypes, structlog, gradio as gr
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.apeiron_unified_hub import UnifiedHub, MODELS, CATEGORY_ROUTERS

hub = UnifiedHub(use_cloud=True); hub.active_model = list(MODELS.values())[0]
files_store = []

# ─── Routing ───────────────────────────────────────────────────────────
KEYWORDS = {
    "code":["code","program","function","script","api","debug","python","javascript","java","cpp","go","rust","sql","database","algorithm","docker","k8s"],
    "video":["video","movie","animation","render","cinematic","edit video","clip","short","reel"],
    "audio":["audio","voice","speech","tts","transcribe","music","sound","podcast","voiceover"],
    "design":["image","picture","design","logo","illustration","art","generate image","wallpaper","icon","ui","ux","banner","poster"],
    "research":["research","analyze","report","study","investigate","find","paper","survey","trend","literature"],
    "threat":["threat","vulnerability","cve","malware","security","cyber","attack","phishing","pentest","incident"],
    "education":["learn","teach","explain","tutorial","math","homework","concept","understand","lesson","course"],
    "resume":["resume","cv","cover letter","job","freelance","proposal","portfolio","linkedin","interview","ats"],
    "trading":["trade","crypto","bitcoin","btc","eth","stock","market","invest","chart","price","technical","rsi","macd"],
}
ROUTER = {"code":"qwen2.5-coder","video":"wan2.1","audio":"whisper","design":"flux1",
          "research":"deepseek-r1","threat":"robin","education":"qwen2.5-math",
          "resume":"reactive-resume","trading":"ccxt-live"}

def cat(t):
    pl=t.lower(); sc={c:sum(k in pl for k in kws) for c,kws in KEYWORDS.items()}
    return max(sc,key=sc.get) if any(sc.values()) else "code"

GEN = {
    "code":lambda p,m:{"type":"code","tab":"code","content":f"# {m} for: {p}\n\ndef solution():\n    '''{p}'''\n    pass","lang":"python"},
    "video":lambda p,m:{"type":"video","tab":"video","content":{"prompt":p,"model":m,"status":"generating"}},
    "audio":lambda p,m:{"type":"audio","tab":"audio","content":{"prompt":p,"model":m,"status":"generating"}},
    "design":lambda p,m:{"type":"image","tab":"image","content":{"prompt":p,"model":m,"status":"generating"}},
    "research":lambda p,m:{"type":"research","tab":"research","content":f"# Research: {p}\n\n## Key Findings\n1. Primary insight\n2. Evidence\n3. Recommendations\n\n*By {MODELS['deepseek-r1'].name}*"},
    "threat":lambda p,m:{"type":"research","tab":"research","content":f"# Threat Report\n\n## Assessment: Moderate\n## IoCs\n- IP: detected\n## Actions\n1. Block IOCs\n2. Investigate\n\n*By {MODELS['robin'].name}*"},
    "education":lambda p,m:{"type":"research","tab":"research","content":f"# Tutorial: {p}\n\n## Steps\n1. Setup\n2. Implement\n3. Verify\n\n*By {MODELS['qwen2.5-math'].name}*"},
    "resume":lambda p,m:{"type":"code","tab":"code","content":f"# Resume: {p}\n\n## Summary\nExpert in {p}...\n## Skills\n- {p}: Expert\n## Proposal\n## Timeline\n|Phase|Duration|\n|---|---|\n|Discovery|1wk|\n|Build|4wk|\n|Total|5wk|"},
    "trading":lambda p,m:{"type":"trading","tab":"crypto","content":{"analysis":f"# Trading\n\nTrend: Bullish\nRSI: 62 | MACD: Buy\nTargets: 1D 65% | 1W 55%\n\n*Not financial advice*"}},
}

# ─── File Processor ───────────────────────────────────────────────────
import os, mimetypes
from pathlib import Path
def proc_file(path):
    if not path or not os.path.exists(path): return {"error":"not found"}
    mime,_=mimetypes.guess_type(path); ext=Path(path).suffix.lower()
    r={"path":path,"name":Path(path).name,"size":os.path.getsize(path),"mime":mimetypes.guess_type(path)[0],"ext":ext,"content":None,"preview":None}
    try:
        ext=Path(path).suffix.lower()
        if ext in ['.txt','.md','.py','.js','.json','.yaml','.yml','.csv','.html','.css','.sql']:
            with open(path,'r',encoding='utf-8') as f: return {**r,"content":f.read()[:50000]}
        elif Path(path).suffix.lower()=='.pdf':
            try: import fitz; d=fitz.open(path); return {**r,"content":"".join(p.get_text() for p in d)[:50000]}
            except: return {**r,"content":"[PDF needs PyMuPDF]"}
        elif Path(path).suffix.lower() in ['.png','.jpg','.jpeg','.gif','.webp','.bmp']:
            return {**r,"preview":path,"content":f"[Image: {Path(path).name}]"}
        elif Path(path).suffix.lower() in ['.mp4','.mov','.avi','.mkv','.webm']:
            return {**r,"preview":path,"content":f"[Video: {Path(path).name}]"}
        elif Path(path).suffix.lower() in ['.mp3','.wav','.ogg','.flac','.m4a']:
            return {**r,"preview":path,"content":f"[Audio: {Path(path).name}]"}
        elif Path(path).suffix.lower() in ['.docx','.doc']:
            try: import docx; d=docx.Document(path); return {**r,"content":"\n".join(p.text for p in d.paragraphs)[:50000]}
            except: return {**r,"content":"[DOCX needs python-docx]"}
        else: return {**r,"content":f"[File: {Path(path).name}]"}
    except Exception as e: return {"error":str(e)}

# ─── Global ────────────────────────────────────────────────────────────
import asyncio, os, sys, random, mimetypes, structlog, gradio as gr
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.apeiron_unified_hub import UnifiedHub, MODELS, CATEGORY_ROUTERS

hub = UnifiedHub(use_cloud=True); hub.active_model = list(MODELS.values())[0]
files_store = []

# ─── Routing ───────────────────────────────────────────────────────────
KEYWORDS = {
    "code":["code","program","function","script","api","debug","python","javascript","java","cpp","go","rust","sql","database","algorithm","docker","k8s"],
    "video":["video","movie","animation","render","cinematic","edit video","clip","short","reel"],
    "audio":["audio","voice","speech","tts","transcribe","music","sound","podcast","voiceover"],
    "design":["image","picture","design","logo","illustration","art","generate image","wallpaper","icon","ui","ux","banner","poster"],
    "research":["research","analyze","report","study","investigate","find","paper","survey","trend","literature"],
    "threat":["threat","vulnerability","cve","malware","security","cyber","attack","phishing","pentest","incident"],
    "education":["learn","teach","explain","tutorial","math","homework","concept","understand","lesson","course"],
    "resume":["resume","cv","cover letter","job","freelance","proposal","portfolio","linkedin","interview","ats"],
    "trading":["trade","crypto","bitcoin","btc","eth","stock","market","invest","chart","price","technical","rsi","macd"],
}
ROUTER = {"code":"qwen2.5-coder","video":"wan2.1","audio":"whisper","design":"flux1",
          "research":"deepseek-r1","threat":"robin","education":"qwen2.5-math",
          "resume":"reactive-resume","trading":"ccxt-live"}

def cat(t):
    pl=t.lower(); sc={c:sum(k in pl for k in kws) for c,kws in KEYWORDS.items()}
    return max(sc,key=sc.get) if any(sc.values()) else "code"

GEN = {
    "code":lambda p,m:{"type":"code","tab":"code","content":f"# {m} for: {p}\n\ndef solution():\n    '''{p}'''\n    pass","lang":"python"},
    "video":lambda p,m:{"type":"video","tab":"video","content":{"prompt":p,"model":m,"status":"generating"}},
    "audio":lambda p,m:{"type":"audio","tab":"audio","content":{"prompt":p,"model":m,"status":"generating"}},
    "design":lambda p,m:{"type":"image","tab":"image","content":{"prompt":p,"model":m,"status":"generating"}},
    "research":lambda p,m:{"type":"research","tab":"research","content":f"# Research: {p}\n\n## Key Findings\n1. Primary insight\n2. Evidence\n3. Recommendations\n\n*By {MODELS['deepseek-r1'].name}*"},
    "threat":lambda p,m:{"type":"research","tab":"research","content":f"# Threat Report\n\n## Assessment: Moderate\n## IoCs\n- IP: detected\n## Actions\n1. Block IOCs\n2. Investigate\n\n*By {MODELS['robin'].name}*"},
    "education":lambda p,m:{"type":"research","tab":"research","content":f"# Tutorial: {p}\n\n## Steps\n1. Setup\n2. Implement\n3. Verify\n\n*By {MODELS['qwen2.5-math'].name}*"},
    "resume":lambda p,m:{"type":"code","tab":"code","content":f"# Resume: {p}\n\n## Summary\nExpert in {p}...\n## Skills\n- {p}: Expert\n## Proposal\n## Timeline\n|Phase|Duration|\n|---|---|\n|Discovery|1wk|\n|Build|4wk|\n|Total|5wk|"},
    "trading":lambda p,m:{"type":"trading","tab":"crypto","content":{"analysis":f"# Trading\n\nTrend: Bullish\nRSI: 62 | MACD: Buy\nTargets: 1D 65% | 1W 55%\n\n*Not financial advice*"}},
}

# ─── File Processor ───────────────────────────────────────────────────
import os, mimetypes
from pathlib import Path
def proc_file(path):
    if not path or not os.path.exists(path): return {"error":"not found"}
    mime,_=mimetypes.guess_type(path); ext=Path(path).suffix.lower()
    r={"path":path,"name":Path(path).name,"size":os.path.getsize(path),"mime":mimetypes.guess_type(path)[0],"ext":ext,"content":None,"preview":None}
    try:
        ext=Path(path).suffix.lower()
        if ext in ['.txt','.md','.py','.js','.json','.yaml','.yml','.csv','.html','.css','.sql']:
            with open(path,'r',encoding='utf-8') as f: return {**r,"content":f.read()[:50000]}
        elif Path(path).suffix.lower()=='.pdf':
            try: import fitz; d=fitz.open(path); return {**r,"content":"".join(p.get_text() for p in d)[:50000]}
            except: return {**r,"content":"[PDF needs PyMuPDF]"}
        elif Path(path).suffix.lower() in ['.png','.jpg',''.jpeg','.gif','.webp','.bmp']:
            return {**r,"preview":path,"content":f"[Image: {Path(path).name}]"}
        elif Path(path).suffix.lower() in ['.mp4','.mov','.avi','.mkv','.webm']:
            return {**r,"preview":path,"content":f"[Video: {Path(path).name}]"}
        elif Path(path).suffix.lower() in ['.mp3','.wav','.ogg','.flac','.m4a']:
            return {**r,"preview":path,"content":f"[Audio: {Path(path).name}]"}
        elif Path(path).suffix.lower() in ['.docx','.doc']:
            try: import docx; d=docx.Document(path); return {**r,"content":"\n".join(p.text for p in d.paragraphs)[:50000]}
            except: return {**r,"content":"[DOCX needs python-docx]"}
        else: return {**r,"content":f"[File: {Path(path).name}]"}
    except Exception as e: return {"error":str(e)}

# ─── Global ────────────────────────────────────────────────────────────
import asyncio, os, sys, random, mimetypes, structlog, gradio as gr
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.apeiron_unified_hub import UnifiedHub, MODELS, CATEGORY_ROUTERS

hub = UnifiedHub(use_cloud=True); hub.active_model = list(MODELS.values())[0]
files_store = []

# ─── Routing ───────────────────────────────────────────────────────────
KEYWORDS = {
    "code":["code","program","function","script","api","debug","python","javascript","java","cpp","go","rust","sql","database","algorithm","docker","k8s"],
    "video":["video","movie","animation","render","cinematic","edit video","clip","short","reel"],
    "audio":["audio","voice","speech","tts","transcribe","music","sound","podcast","voiceover"],
    "design":["image","picture","design","logo","illustration","art","generate image","wallpaper","icon","ui","ux","banner","poster"],
    "research":["research","analyze","report","study","investigate","find","paper","survey","trend","literature"],
    "threat":["threat","vulnerability","cve","malware","security","cyber","attack","phishing","pentest","incident"],
    "education":["learn","teach","explain","tutorial","math","homework","concept","understand","lesson","course"],
    "resume":["resume","cv","cover letter","job","freelance","proposal","portfolio","linkedin","interview","ats"],
    "trading":["trade","crypto","bitcoin","btc","eth","stock","market","invest","chart","price","technical","rsi","macd"],
}
ROUTER = {"code":"qwen2.5-coder","video":"wan2.1","audio":"whisper","design":"flux1",
          "research":"deepseek-r1","threat":"robin","education":"qwen2.5-math",
          "resume":"reactive-resume","trading":"ccxt-live"}

def cat(t):
    pl=t.lower(); sc={c:sum(k in pl for k in kws) for c,kws in KEYWORDS.items()}
    return max(sc,key=sc.get) if any(sc.values()) else "code"

GEN = {
    "code":lambda p,m:{"type":"code","tab":"code","content":f"# {m} for: {p}\n\ndef solution():\n    '''{p}'''\n    pass","lang":"python"},
    "video":lambda p,m:{"type":"video","tab":"video","content":{"prompt":p,"model":m,"status":"generating"}},
    "audio":lambda p,m:{"type":"audio","tab":"audio","content":{"prompt":p,"model":m,"status":"generating"}},
    "design":lambda p,m:{"type":"image","tab":"image","content":{"prompt":p,"model":m,"status":"generating"}},
    "research":lambda p,m:{"type":"research","tab":"research","content":f"# Research: {p}\n\n## Key Findings\n1. Primary insight\n2. Evidence\n3. Recommendations\n\n*By {MODELS['deepseek-r1'].name}*"},
    "threat":lambda p,m:{"type":"research","tab":"research","content":f"# Threat Report\n\n## Assessment: Moderate\n## IoCs\n- IP: detected\n## Actions\n1. Block IOCs\n2. Investigate\n\n*By {MODELS['robin'].name}*"},
    "education":lambda p,m:{"type":"research","tab":"research","content":f"# Tutorial: {p}\n\n## Steps\n1. Setup\n2. Implement\n3. Verify\n\n*By {MODELS['qwen2.5-math'].name}*"},
    "resume":lambda p,m:{"type":"code","tab":"code","content":f"# Resume: {p}\n\n## Summary\nExpert in {p}...\n## Skills\n- {p}: Expert\n## Proposal\n## Timeline\n|Phase|Duration|\n|---|---|\n|Discovery|1wk|\n|Build|4wk|\n|Total|5wk|"},
    "trading":lambda p,m:{"type":"trading","tab":"crypto","content":{"analysis":f"# Trading\n\nTrend: Bullish\nRSI: 62 | MACD: Buy\nTargets: 1D 65% | 1W 55%\n\n*Not financial advice*"}},
}

# ─── File Processor ───────────────────────────────────────────────────
import os, mimetypes
from pathlib import Path
def proc_file(path):
    if not path or not os.path.exists(path): return {"error":"not found"}
    mime,_=mimetypes.guess_type(path); ext=Path(path).suffix.lower()
    r={"path":path,"name":Path(path).name,"size":os.path.getsize(path),"mime":mimetypes.guess_type(path)[0],"ext":ext,"content":None,"preview":None}
    try:
        ext=Path(path).suffix.lower()
        if ext in ['.txt','.md','.py','.js','.json','.yaml','.yml','.csv','.html','.css','.sql']:
            with open(path,'r',encoding='utf-8') as f: return {**r,"content":f.read()[:50000]}
        elif Path(path).suffix.lower()=='.pdf':
            try: import fitz; d=fitz.open(path); return {**r,"content":"".join(p.get_text() for p in d)[:50000]}
            except: return {**r,"content":"[PDF needs PyMuPDF]"}
        elif Path(path).suffix.lower() in ['.png','.jpg','.jpeg','.gif','.webp','.bmp']:
            return {**r,"preview":path,"content":f"[Image: {Path(path).name}]"}
        elif Path(path).suffix.lower() in ['.mp4','.mov','.avi','.mkv','.webm']:
            return {**r,"preview":path,"content":f"[Video: {Path(path).name}]"}
        elif Path(path).suffix.lower() in ['.mp3','.wav','.ogg','.flac','.m4a']:
            return {**r,"preview":path,"content":f"[Audio: {Path(path).name}]"}
        elif Path(path).suffix.lower() in ['.docx','.doc']:
            try: import docx; d=docx.Document(path); return {**r,"content":"\n".join(p.text for p in d.paragraphs)[:50000]}
            except: return {**r,"content":"[DOCX needs python-docx]"}
        else: return {**r,"content":f"[File: {Path(path).name}]"}
    except Exception as e: return {"error":str(e)}

# ─── Global ────────────────────────────────────────────────────────────
import asyncio, os, sys, random, mimetypes, structlog, gradio as gr
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.apeiron_unified_hub import UnifiedHub, MODELS, CATEGORY_ROUTERS

hub = UnifiedHub(use_cloud=True); hub.active_model = list(MODELS.values())[0]
files_store = []

# ─── Helpers ──────────────────────────────────────────────────────────
def detect_lang(t): return "bn" if sum(1 for c in t if '\u0980'<=c<='\u09FF')>len(t)*0.1 else "en"
def is_greeting(t): return any(k in t.lower() for k in ["hello","hi","hey","hey!","hi!","hello!","hola","হ্যালো","হাই","হাই","কেমন আছো","কেমন আছেন","সালাম","নমস্কার","নমস্তে","assalamualaikum"]) and len(t.strip().split())<=3

GREET_RESP = {
    "en":["Hello! 👋 How can I help? I can write code, generate images/videos, research, analyze data, create documents, and more!",
          "Hi! 👋 What would you like me to help with? Code, images, videos, research, documents — just ask!"],
    "bn":["হ্যালো! 👋 আজ আমি কীভাবে সাহায্য করতে পারি? কোড, ছবি, ভিডিও, রিসার্চ, ডকুমেন্ট — যেকোনো কিছু করাতে পারেন!"]
}
SIMPLE_REP = {"en":["You're welcome! 😊 Let me know if you need anything!"],"bn":["আপনাকেও ধন্যবাদ! 😊"]}

def lang(t): return "bn" if sum(1 for c in t if '\u0980'<=c<='\u09FF')>len(t)*0.1 else "en"
def is_greeting(t): return any(k in t.lower() for k in ["hello","hi","hey","hey!","hi!","hello!","hola","হ্যালো","হাই","হাই","কেমন আছো","কেমন আছেন","সালাম","নমস্কার","নমস্তে","assalamualaikum"]) and len(t.strip().split())<=3

# ─── Main Handler ────────────────────────────────────────────────────
async def handle(message, history, files):
    if not message.strip() and not files: return history, ""
    
    # Files
    for f in files: files_store.append(f.name if hasattr(f,'name') else f)
    
    # Lang
    lg = detect_lang(message + " " + " ".join(f.get("content","") for f in files_store))
    
    # Greeting
    if any(k in message.lower() for k in ["hello","hi","hey","hey!","hi!","hello!","hola","হ্যালো","হাই","হাই","কেমন আছো","কেমন আছেন","সালাম","নমস্কার","নমস্তে","assalamualaikum"]) and len(message.strip().split())<=3:
        return history + [{"role":"user","content":message},{"role":"assistant","content":random.choice({
            "en":["Hello! 👋 How can I help? I can write code, generate images/videos, research, analyze data, create documents, and more!",
                  "Hi! 👋 What would you like me to help with? Code, images, videos, research, documents — just ask!"],
            "bn":["হ্যালো! 👋 আজ আমি কীভাবে সাহায্য করতে পারি? কোড, ছবি, ভিডিও, রিসার্চ, ডকুমেন্ট — যেকোনো কিছু করাতে পারেন!"]
        }[lang(message)])], ""
    
    # Thanks/bye
    if any(k in message.lower() for k in ["thanks","thank you","thanks!","thx","ok","okay","cool","awesome","great","bye","bye!","goodbye","thx","ধন্যবাদ","ধন্যবাদ!","ঠিক আছে","ঠিক","বাই","বিদায়"]):
        return history + [{"role":"user","content":message},{"role":"assistant","content":random.choice({"en":["You're welcome! 😊 Let me know if you need anything!","Anytime! 😊 Happy to help!"],"bn":["আপনাকেও ধন্যবাদ! 😊 আর কিছু লাগলে বলবেন!"]}[lang(message)])], ""
    
    # Files
    for f in files: files_store.append(Files.proc(f.name if hasattr(f,'name') else f))
    
    # Language
    lg = detect_lang(message + " " + " ".join(f.get("content","") for f in files_store))
    
    try:
        # Route
        cat = max({c:sum(k in message.lower() for k in kws) for c,kws in KEYWORDS.items()}, key=lambda x:x[1])[0] if any(any(k in message.lower() for k in v) for v in KEYWORDS.values()) else "code"
        model = ROUTER.get(cat, "qwen2.5-coder")
        
        result = await hub.route_prompt(message, cat, {"cloud_mode": True})
        out = GEN.get(cat, GEN["code"])(message, MODELS[ROUTER.get(cat,"qwen2.5-coder")].name)
        result.update(out)
        
        gi = {"code":("💻","Code"),"video":("🎬","Video"),"audio":("🔊","Audio"),
              "design":("🎨","Design"),"research":("🔬","Research"),"threat":("🛡️","Threat Intel"),
              "education":("📚","Learn"),"resume":("📄","Resume"),"trading":("📈","Trading")}[cat]
        
        if out["type"]=="code":
            resp = f"""**{gi[0]} {gi[1]}** (via {MODELS[ROUTER.get(cat,"qwen2.5-coder")].name})\n\n```{out.get('language','python')}\n{out.get('content','')}\n```"""
        elif out["type"] in ("research","threat"):
            resp = f"**{gi[0]} {gi[1]}**\n\n{out.get('content','')}"
        elif out["type"]=="trading":
            resp = f"**{gi[0]} {gi[1]}**\n\n{out['content'].get('analysis','')}"
        elif out["type"] in ("video","audio","design"):
            resp = f"**{gi[0]} {gi[1]}**\n\n✅ **Generating {gi[1].lower()}...** Check **{gi[1]}** tab!"
        else:
            resp = f"**{gi[0]} {gi[1]}**\n\n{out.get('content','')}"
        
        return history + [{"role":"user","content":message},{"role":"assistant","content":resp}], ""
    
    except Exception as e:
        return history + [{"role":"user","content":message},{"role":"assistant","content":f"❌ {e}"}], ""


# ─── UI ────────────────────────────────────────────────────────────────
import gradio as gr

with gr.Blocks(
    title="Apeiron",
    theme=gr.themes.Default(primary_hue="blue", secondary_hue="slate"),
    css="""
    #chatbot .message {padding:12px 16px;border-radius:12px;max-width:85%;}
    #chatbot .user {background:#f0f2f5;margin-left:auto;border-radius:18px 18px 4px 18px;}
    #chatbot .assistant {background:#fff;border:1px solid #e5e7eb;border-radius:18px 18px 18px 4px;}
    .message-content {white-space:pre-wrap;word-wrap:break-word;}
    .message-wrapper:hover .msg-menu{opacity:1;visibility:visible;}
    .msg-menu{opacity:0;visibility:hidden;transition:all .2s;position:absolute;right:8px;top:8px;z-index:10;}
    .msg-menu button{background:#fff;border:1px solid #e5e7eb;border-radius:6px;padding:6px 10px;font-size:12px;cursor:pointer;white-space:nowrap;box-shadow:0 2px 8px rgba(0,0,0,.1);}
    .msg-menu button:hover{background:#f3f4f6;}
    .sidebar{background:#fafafa;border-right:1px solid #e5e7eb;}
    .sidebar .gr-button{width:100%;justify-content:flex-start;text-align:left;border:none;background:transparent;color:#374151;font-size:14px;padding:10px 12px;border-radius:8px;}
    .sidebar .gr-button:hover{background:#f3f4f6;}
    .sidebar .gr-button.primary{background:#10a37f;color:white;}
    .input-area{border-top:1px solid #e5e7eb;background:#fff;padding:12px;}
    #chatbot{border:none!important;box-shadow:none!important;}
    .gr-chatbot{border:none!important;}
    ::-webkit-scrollbar{width:6px;height:6px;}
    ::-webkit-scrollbar-track{background:transparent;}
    ::-webkit-scrollbar-thumb{background:#d1d5db;border-radius:3px;}
    ::-webkit-scrollbar-thumb:hover{background:#9ca3af;}
""") as demo:

    with gr.Row():
        with gr.Column(scale=1, elem_classes="sidebar", min_width=260, max_width=280):
            gr.Markdown("### 🤖 Apeiron")
            gr.Markdown("*47 Models • 10 Categories*")
            gr.HTML("<hr style='margin:12px 0;border-color:#e5e7eb'>")
            for cat, (ic, nm) in {"code":("💻","Code"),"video":("🎬","Video"),"audio":("🔊","Audio"),
                                  "design":("🎨","Design"),"research":("🔬","Research"),
                                  "threat":("🛡️","Threat"),"education":("📚","Learn"),
                                  "resume":("📄","Resume"),"trading":("📈","Trading")}.items():
                gr.Button(f"{ic} {nm}", size="sm", variant="secondary")
            gr.HTML("<hr style='margin:12px 0;border-color:#e5e7eb'>")
            gr.Markdown("**📎 Upload**")
            file_up = gr.File(label="", file_count="multiple",
                              file_types=[".png",".jpg",".jpeg",".pdf",".txt",".py",".md",".csv",".json",".docx",".mp4",".mov",".mp3",".wav"], height=80)
            gr.HTML("<hr style='margin:16px 0;border-color:#e5e7eb'>")
            gr.Button("🗑️ Clear", size="sm").click(fn=lambda: ([],""), outputs=[gr.Chatbot(),gr.Textbox()])
            gr.Button("🌙", size="sm", variant="secondary")

        with gr.Column(scale=5):
            gr.Markdown("### 💬 Apeiron")
            chat = gr.Chatbot(
                height=650, type="messages",
                avatar_images=("👤","🤖"),
                value=[{"role":"assistant","content":"Hi! 👋 I'm Apeiron — your AI assistant with **47 specialized models**.\n\n**Just chat naturally.** I auto-route to the best model:\n\n💻 **Code** — Python, JS, APIs, algorithms\n🎨 **Design** — Logos, images, illustrations\n🎬 **Video** — Cinematic clips\n🔊 **Audio** — TTS, STT, voice cloning\n🔬 **Research** — Deep analysis, reports\n🛡️ **Threat Intel** — CVEs, malware\n🤖 **Agents** — Multi-agent workflows\n📚 **Learn** — Tutorials, explanations\n📄 **Resume** — ATS CVs, proposals\n📈 **Trading** — Crypto/stock analysis\n\n**Just type what you need.** Upload files with 📎 if needed.\n\n*Try: \"Create a Python web scraper\" or \"Analyze Bitcoin price\""}],
                height=650, type="messages", avatar_images=("👤","🤖"),
                show_copy_button=True, show_share_button=False, elem_id="chatbot")
            
            with gr.Row():
                msg = gr.Textbox(placeholder="Message Apeiron... (Shift+Enter for new line)", container=False, lines=1, max_lines=8, scale=20, show_label=False, autofocus=True)
                send = gr.Button("➤", variant="primary", size="lg", scale=0)
            file_up = gr.File(label="📎", file_count="multiple", file_types=[".png",".jpg",".jpeg",".pdf",".txt",".py",".md",".csv",".json",".docx",".mp4",".mov",".mp3",".wav"], height=80)
        
        with gr.Column(scale=3, min_width=350, max_width=420):
            with gr.Tabs():
                with gr.TabItem("💻 Code"): code_o = gr.Code(label="", language="python", lines=22, interactive=False, show_line_numbers=True)
                with gr.TabItem("🖼️ Images"): img_o = gr.Gallery(label="", columns=2, object_fit="contain", height=350)
                with gr.TabItem("▶️ Video"): vid_o = gr.Video(height=280)
                with gr.TabItem("🔊 Audio"): aud_o = gr.Audio(type="filepath")
                with gr.TabItem("📊 Reports"): rpt_o = gr.Markdown()
                with gr.TabItem("📈 Charts"): cht_o = gr.Plot()

        async def send_fn(m, h, fs):
            if not m.strip() and not fs: return h, ""
            for f in fs: files_store.append(f.name if hasattr(f,'name') else f)
            res = await handle(m, h, fs)
            return res
        
        gr.Textbox(visible=False).submit(fn=lambda m,h,fs: handle(m,h,fs), inputs=[gr.Textbox(visible=False),gr.Chatbot(),gr.File()], outputs=[gr.Chatbot(),gr.Textbox()])
        gr.Textbox(visible=False).submit(fn=lambda m,h,fs: handle(m,h,fs), inputs=[gr.Textbox(visible=False),gr.Chatbot(),gr.File()], outputs=[gr.Chatbot(),gr.Textbox()])

if __name__ == "__main__":
    demo.launch(share=True)