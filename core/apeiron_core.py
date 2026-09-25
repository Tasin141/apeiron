#!/usr/bin/env python3
"""Core orchestrator for the Apeiron Autonomous AI Engine - Cloud Optimized."""

import asyncio
import sys
import signal
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Awaitable
from modules.automation.bg_self_improving_engine import SelfImprovingEngine, BackgroundScheduler
import structlog
import aiohttp

# Configure structured logging
structlog.configure(
    processors=[
        structlog.dev.print_logger_for_level,
    ],
    logger_factory=structlog.stdLogger.factory,
)

logger = structlog.get_logger("apeiron")

# Model download configuration
MODEL_DOWNLOAD_DIR = Path(__file__).parent / "downloaded_models"
MODEL_DOWNLOAD_DIR.mkdir(exist_ok=True, parents=True)


class ModuleRegistry:
    """Registry for managing loaded modules and their interfaces."""

    def __init__(self) -> None:
        self.modules: Dict[str, Dict[str, Any]] = {}
        self.initialized: Dict[str, bool] = {}
        self.config: Dict[str, Any] = {}

    def register(self, name: str, module_obj: Any, init_fn: Optional[Callable] = None) -> None:
        """Register a module with optional initialization function."""
        self.modules[name] = {
            "object": module_obj,
            "init_fn": init_fn,
            "initialized": False,
        }
        logger.info(f"[green]Registered module:[/] {name}")

    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value (e.g., model names, API keys)."""
        self.config[key] = value
        logger.debug(f"Config set: {key}")

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get module info by name."""
        return self.modules.get(name)

    def initialize_all(self) -> None:
        """Initialize all registered modules."""
        for name, info in self.modules.items():
            if info["init_fn"] and not info["initialized"]:
                try:
                    info["init_fn"]()
                    info["initialized"] = True
                    logger.info(f"[green]Initialized:[/] {name}")
                except Exception as e:
                    logger.error(f"[red]Failed to initialize:[/] {name}: {e}")
                    info["initialized"] = False

    def run(self, name: str, *args, **kwargs) -> Any:
        """Run a module's main function."""
        info = self.get(name)
        if not info or not info["initialized"]:
            logger.error(f"Module not initialized: {name}")
            return None
        obj = info["object"]
        if hasattr(obj, "run"):
            return obj.run(*args, **kwargs)
        elif hasattr(obj, "execute"):
            return obj.execute(*args, **kwargs)
        return None


registry = ModuleRegistry()


def signal_handler() -> Callable:
    """Return a signal handler for graceful shutdown."""

    def handler(signum: int, frame: Any) -> None:
        logger.info("[yellow]Received signal {signum}, shutting down gracefully...[/]")
        asyncio.get_event_loop().stop()

    return handler


class ApeironEngine:
    """Master engine that orchestrates all Apeiron modules - Cloud Optimized."""

    def __init__(self) -> None:
        self.running: bool = False
        self.modules_dir: Path = Path(__file__).parent / "modules"
        self.api_config: Dict[str, str] = {}
        self.background_engine: Optional[SelfImprovingEngine] = None
        self.background_scheduler: Optional[BackgroundScheduler] = None

    async def _import_modules(self) -> None:
        """Dynamically import all module engines."""
        module_files = [
            ("coding", "coder_engine", "CoderEngine"),
            ("media", "media_engine", "MediaEngine"),
            ("trading", "trading_engine", "TradingEngine"),
            ("automation", "research_crawler", "ResearchCrawler"),
            ("automation", "cv_automation", "CVAutomation"),
        ]

        for dir_name, file_name, class_name in module_files:
            mod_path = self.modules_dir / dir_name / file_name
            if not mod_path.exists():
                logger.warning(f"[yellow]Module not found:[/] {mod_path}")
                continue

            # Add parent to path temporarily
            sys.path.insert(0, str(mod_path.parent))
            try:
                mod = __import__(file_name, fromlist=[class_name])
                cls = getattr(mod, class_name)
                registry.register(dir_name, cls)
                logger.info(f"[green]Imported:[/] {dir_name}.{class_name}")
            except ImportError as e:
                logger.error(f"[red]Failed to import:[/] {dir_name}: {e}")
            finally:
                sys.path.remove(str(mod_path.parent))

    async def _download_model(self, model_id: str, model_name: str) -> str:
        """Download a model from Hugging Face Hub.
        
        Args:
            model_id: Hugging Face repo ID (e.g., "openbmb/MiniCPM5-1B-Base")
            model_name: Local display name for the model
            
        Returns:
            Path to the downloaded model directory
        """
        import shutil
        
        download_path = MODEL_DOWNLOAD_DIR / model_name
        
        if download_path.exists():
            logger.info(f"Model {model_name} already downloaded")
            return str(download_path)
        
        logger.info(f"Downloading model: {model_id}", model=model_name)
        
        try:
            # Use huggingface_hub to download
            from huggingface_hub import hf_hub_download, snapshot_download
            
            # Download the model files
            if not shutil.which("huggingface_hub"):
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "huggingface_hub"],
                    capture_output=True,
                    timeout=60,
                )
            
            # Download using snapshot_download for full repo
            snapshot_download(
                repo_id=model_id,
                local_dir=str(download_path),
                local_dir_use_symlinks=False,
            )
            
            logger.info(f"Model downloaded successfully", path=str(download_path))
            return str(download_path)
            
        except Exception as e:
            logger.error(f"Failed to download model {model_id}: {e}")
            # Return empty path, will use fallback
            return str(MODEL_DOWNLOAD_DIR / "fallback")

    async def _initialize_models(self) -> None:
        """Initialize models based on configuration."""
        # Set default models for cloud/low-resource deployment
        default_models = {
            "coding": "minicpm5-1b",  # 1B parameters, good for code
            "media": "flux-schnell",  # FLUX Schnell, fast generation
            "trading": "geb-1.3b",    # Lightweight for analysis
            "research": "minicpm-1b", # For web analysis
            "cv": "rule-based",       # CV uses rule-based primarily
        }

        for module_name, model_name in default_models.items():
            registry.set_config(f"{module_name}_model", model_name)
        
        # Download models if not present
        model_downloads = {
            "coding": ("openbmb/MiniCPM5-1B-Base", "minicpm5-1b"),
            "media": ("black-forest-labs/FLUX.1-schnell", "flux-schnell"),
            "trading": ("GEB-AGI/geb-1.3b", "geb-1.3b"),
            "research": ("openbmb/MiniCPM-1B", "minicpm-1b"),
        }
        
        for module_key, (repo_id, local_name) in model_downloads.items():
            try:
                path = await self._download_model(repo_id, local_name)
                logger.info(f"Model ready for {module_key}", path=path)
            except ImportError:
                logger.warning(f"huggingface_hub not installed, skipping download for {module_key}")
            except Exception as e:
                logger.error(f"Model download failed for {module_key}: {e}")
        
        logger.info("Models configured for cloud deployment", config=default_models)

    async def start(self) -> None:
        """Start the Apeiron engine."""
        self.running = True
        console = __import__("rich.console").Console
        RichConsole.__init__(console, stderr=True) if hasattr(__import__("rich.console").RichConsole, '__init__') else None

        console.print(Panel.fit(
            "[bold blue]Apeiron Autonomous AI Engine[/]\n"
            "[white]Master Aggregator System - Cloud Optimized[/]",
            title="System Init",
        ))
        logger.info("Apeiron engine starting...")

        # Import all modules
        await self._import_modules()

        # Set up model configuration
        await self._initialize_models()

        # Initialize background self-improving engine
        self.background_engine = SelfImprovingEngine()
        self.background_scheduler = BackgroundScheduler(self.background_engine)
        
        # Register all modules with the background engine
        for module_name, info in registry.modules.items():
            module_code = info.get("object", {}).get("__code__", "")
            if module_code:
                self.background_engine.register_module(module_name, module_code, "python")
        
        # Start the 24/7 background improvement loop
        asyncio.create_task(self.background_scheduler.start())

        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler())
        signal.signal(signal.SIGTERM, signal_handler())

        # Run interactive CLI
        await self._cli_loop()

    async def _cli_loop(self) -> None:
        """Interactive command-line menu."""
        while self.running:
            console.print("\n[bold cyan]Apeiron Menu:[/]")
            console.print("1. Code Engine - Generate/validate/execute code")
            console.print("2. Media Engine - Image/Video/Audio generation")
            console.print("3. Trading Engine - Market data/backtesting")
            console.print("4. Research Crawler - Web scraping & synthesis")
            console.print("5. CV Automation - Resume/portfolio generation")
            console.print("6. Background Engine Status")
            console.print("0. Exit")
            console.print()

            choice = console.input("[green]Select option:[/] ").strip()

            if choice == "0":
                self.running = False
                console.print("[yellow]Goodbye![/]")
                # Stop background engine on exit
                if self.background_engine:
                    await self.background_engine.stop()
                if self.background_scheduler:
                    await self.background_scheduler.stop()
                break
            elif choice == "1":
                await self._run_module("coding")
            elif choice == "2":
                await self._run_module("media")
            elif choice == "3":
                await self._run_module("trading")
            elif choice == "4":
                await self._run_module("automation")
            elif choice == "5":
                await self._run_module("automation")
            elif choice == "6":
                # Show background engine status
                if self.background_engine:
                    status = self.background_engine.get_status()
                    console.print(f"\n[bold]Background Engine Status:[/]")
                    console.print(f"  Running: {status['running']}")
                    console.print(f"  Total analyses: {status['total_analyses']}")
                    console.print(f"  Improvements made: {status['improvements_made']}")
                    console.print(f"  Successful fixes: {status['successful_fixes']}")
                    console.print(f"  Modules registered: {status['modules_registered']}")
                    console.print(f"  Learned patterns: {status['learned_patterns']}")
                else:
                    console.print("[red]Background engine not initialized.[/]")
            else:
                console.print("[red]Invalid option, please try again.[/]")

    async def _run_module(self, category: str) -> None:
        """Run a specific module's interactive session."""
        info = registry.get(category)
        if not info:
            console.print(f"[red]Module not found:[/] {category}")
            return

        obj = info["object"]
        console.print(f"\n[bold]{category.title()} Engine[/bold]")

        # Run module-specific CLI
        if hasattr(obj, "cli"):
            await obj.cli()
        else:
            console.print("[yellow]No CLI interface defined for this module.[/]")

    def stop(self) -> None:
        """Stop the engine."""
        self.running = False


def main() -> None:
    """Entry point for the Apeiron engine."""
    engine = ApeironEngine()
    try:
        asyncio.run(engine.start())
    except KeyboardInterrupt:
        console.print("\n[yinterrupted by user[/]")


if __name__ == "__main__":
    main()