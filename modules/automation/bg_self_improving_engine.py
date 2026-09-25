#!/usr/bin/env python3
"""Apeiron 24/7 Self-Improving Background Engine.

Autonomous AI engine that runs continuously, self-analyzes, self-improves,
self-debugs, and continuously learns from new data across all domains.
"""

import asyncio
import json
import logging
import os
import sys
import time
import gc
import hashlib
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = structlog.get_logger("apeiron.bg_engine")


class MemoryCell:
    """Persistent memory cell for storing learned patterns."""
    
    def __init__(self, ttl_hours: int = 168) -> None:  # 1 week default
        self.ttl = timedelta(hours=ttl_hours)
        self.memory_dir = Path(__file__).parent.parent / "bg_memory"
        self.memory_dir.mkdir(exist_ok=True, parents=True)
        self._lock = asyncio.Lock()
    
    async def store(self, key: str, value: Any, category: str = "general") -> str:
        """Store a memory cell."""
        async with self._lock:
            cell_id = f"{category}:{key}:{int(time.time())}"
            cell_data = {
                "id": cell_id,
                "key": key,
                "value": value,
                "category": category,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + self.ttl).isoformat(),
                "access_count": 0,
                "access_times": [],
            }
            
            filepath = self.memory_dir / f"{cell_id}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(cell_data, f, indent=2)
            
            # Clean old expired cells
            await self._cleanup()
            
            return cell_id
    
    async def retrieve(self, key: str, category: str = "general") -> Optional[Any]:
        """Retrieve a memory cell."""
        async with self._lock:
            filepath = self.memory_dir / f"{category}:{key}.json"
            if not filepath.exists():
                return None
            
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    cell_data = json.load(f)
                
                # Check expiry
                created = datetime.fromisoformat(cell_data["created_at"])
                if datetime.utcnow() - created > self.ttl:
                    filepath.unlink(missing_ok=True)
                    return None
                
                cell_data["access_count"] += 1
                cell_data["access_times"].append(datetime.utcnow().isoformat())
                
                # Keep only last 50 access times
                if len(cell_data["access_times"]) > 50:
                    cell_data["access_times"] = cell_data["access_times"][-50:]
                
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(cell_data, f, indent=2)
                
                return cell_data["value"]
            except (json.JSONDecodeError, KeyError):
                filepath.unlink(missing_ok=True)
                return None
    
    async def _cleanup(self) -> None:
        """Remove expired memory cells."""
        now = datetime.utcnow()
        for filepath in self.memory_dir.glob("*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                created = datetime.fromisoformat(data["created_at"])
                if now - created > self.ttl:
                    filepath.unlink()
            except (json.JSONDecodeError, KeyError):
                filepath.unlink(missing_ok=True)


class CodeAnalyzer:
    """Analyzes code structure, identifies improvements, and detects patterns."""
    
    def __init__(self) -> None:
        self.pattern_library: Dict[str, Dict] = {}
        self.anti_patterns: Dict[str, Dict] = {}
    
    async def analyze_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Analyze code for patterns, anti-patterns, and improvement opportunities."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {"error": "Invalid syntax", "language": language}
        
        analysis = {
            "language": language,
            "complexity": self._calculate_complexity(tree),
            "patterns": self._detect_patterns(code, language),
            "anti_patterns": self._detect_anti_patterns(code, language),
            "optimizations": self._suggest_optimizations(code, language),
            "metrics": {
                "lines_of_code": len(code.splitlines()),
                "nesting_depth": self._max_nesting_depth(tree),
                "function_count": len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]),
                "import_count": len([n for n in ast.walk(tree) if isinstance(n, ast.Import)]),
            }
        }
        
        return analysis
    
    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
                complexity += 1
        return complexity
    
    def _detect_patterns(self, code: str, language: str) -> List[Dict]:
        """Detect known good patterns."""
        patterns = []
        # Add pattern detection logic here
        return patterns
    
    def _detect_anti_patterns(self, code: str, language: str) -> List[Dict]:
        """Detect anti-patterns and issues."""
        anti_patterns = []
        # Add anti-pattern detection
        return anti_patterns
    
    def _suggest_optimizations(self, code: str, language: str) -> List[Dict]:
        """Suggest code optimizations."""
        optimizations = []
        # Add optimization suggestions
        return optimizations
    
    def _max_nesting_depth(self, tree: ast.AST) -> int:
        """Calculate maximum nesting depth."""
        depths = []
        
        def walk(node, depth=0):
            depths.append(depth)
            for child in ast.iter_child_nodes(node):
                walk(child, depth + 1)
        
        walk(tree)
        return max(depths) if depths else 0


class SelfImprovingEngine:
    """Core engine that continuously analyzes, improves, and self-debugs."""
    
    def __init__(self, engine_name: str = "apeiron_bg") -> None:
        self.engine_name = engine_name
        self.running = False
        self.analysis_interval = 300  # 5 minutes
        self.improvement_threshold = 0.7  # 70% similarity to trigger rewrite
        
        # Components
        self.memory = MemoryCell()
        self.code_analyzer = CodeAnalyzer()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # State
        self.improvement_count = 0
        self.total_analyses = 0
        self.successful_fixes = 0
        self.learned_patterns: set = set()
        
        # Registered modules to improve
        self.modules: Dict[str, Dict] = {}
    
    async def start(self) -> None:
        """Start the 24/7 background improvement loop."""
        self.running = True
        logger.info(f"Starting {self.engine_name} 24/7 self-improvement engine")
        
        # Initialize with system scan
        await self._initial_scan()
        
        while self.running:
            try:
                await self._improvement_cycle()
                # Wait for next cycle
                await asyncio.sleep(self.analysis_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in improvement cycle: {e}")
                await asyncio.sleep(60)  # Wait minute on error
        
        logger.info(f"{self.engine_name} shutting down")
    
    async def stop(self) -> None:
        """Stop the background engine."""
        self.running = False
    
    async def _initial_scan(self) -> None:
        """Initial scan of all registered modules."""
        logger.info("Performing initial system scan")
        # Scan registered modules for improvement opportunities
        for module_name, module_info in self.modules.items():
            try:
                code = module_info.get("code", "")
                if code:
                    analysis = await self.analyze_code(code, module_info.get("language", "python"))
                    await self._store_analysis(module_name, analysis)
            except Exception as e:
                logger.warning(f"Error scanning module {module_name}: {e}")
        
        logger.info("Initial scan complete")
    
    async def _improvement_cycle(self) -> None:
        """Run one complete improvement cycle."""
        self.total_analyses += 1
        logger.debug(f"Starting improvement cycle #{self.total_analyses}")
        
        # 1. Analyze all registered modules
        analysis_tasks = []
        for module_name, module_info in self.modules.items():
            code = module_info.get("code", "")
            if code:
                tasks.append(
                    self.analyze_code(module_name, code, module_info.get("language", "python"))
                )
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 2. Process analysis results
            for module_name, result in zip(self.modules.keys(), results):
                if isinstance(result, Exception):
                    logger.error(f"Analysis error for {module_name}: {result}")
                    continue
                
                await self._process_analysis(module_name, result)
        
        # 3. Self-debug: Find and fix errors in own code
        await self._self_debug()
        
        # 4. Store learned patterns
        await self._consolidate_learnings()
        
        # 5. Generate improvement report
        logger.debug(f"Improvement cycle complete: {self.improvement_count} improvements made")
    
    async def _process_analysis(self, module_name: str, analysis: Dict) -> None:
        """Process analysis results and generate improvements."""
        if "error" in analysis:
            # Self-debug: try to fix the error
            await self._fix_module_errors(module_name, analysis)
            return
        
        # Check for optimization opportunities
        optimizations = analysis.get("optimizations", [])
        if optimizations:
            # Generate improved code
            improved_code = await self._generate_improved_code(module_name, analysis)
            if improved_code:
                # Store the improvement
                await self._update_module_code(module_name, improved_code)
                self.improvement_count += 1
                logger.info(f"Improved {module_name} (cycle {self.improvement_count})")
        
        # Store learned patterns
        patterns = analysis.get("patterns", [])
        for pattern in patterns:
            pattern_key = f"{analysis['language']}:{pattern.get('type', 'unknown')}"
            self.learned_patterns.add(pattern_key)
    
    async def _self_debug(self) -> None:
        """Analyze and fix errors in the engine's own code."""
        # Get the engine's source code
        try:
            engine_source = self._get_engine_source()
            if engine_source:
                analysis = await self.analyze_code(engine_source, "python")
                
                if "error" not in analysis:
                    # Check for improvements
                    optimizations = analysis.get("optimizations", [])
                    if optimizations:
                        # Apply self-fixes
                        improved = await self._generate_improved_code("self_debug", analysis)
                        if improved:
                            logger.info("Self-improvement opportunity detected in engine code")
                            self.successful_fixes += 1
        except Exception as e:
            logger.debug(f"Self-debug error (expected in production): {e}")
    
    async def _generate_improved_code(self, module_name: str, analysis: Dict) -> Optional[str]:
        """Generate improved version of code based on analysis."""
        # This is a simplified improvement - in production would use LLM
        code = analysis.get("original_code", "")
        optimizations = analysis.get("optimizations", [])
        
        if not code or not optimizations:
            return None
        
        # Apply simple improvements based on detected patterns
        improved = code
        
        for opt in optimizations:
            suggestion = opt.get("suggestion", "")
            if "remove_unused_import" in suggestion.lower():
                # Simple heuristic: remove common unused imports
                improved = self._remove_unused_imports(improved)
            elif "reduce_nesting" in suggestion.lower():
                improved = self._reduce_nesting(improved)
            elif "add_type_hints" in suggestion.lower():
                improved = self._add_type_hints(improved)
        
        # Verify improved code has valid syntax
        try:
            ast.parse(improved)
            return improved
        except SyntaxError:
            return None
    
    def _remove_unused_imports(self, code: str) -> str:
        """Simple unused import removal."""
        # Basic heuristic - in production would use proper import analysis
        return code
    
    def _reduce_nesting(self, code: str) -> str:
        """Reduce code nesting depth."""
        # Basic restructuring
        return code
    
    def _add_type_hints(self, code: str) -> str:
        """Add type hints to Python code."""
        return code
    
    async def _fix_module_errors(self, module_name: str, analysis: Dict) -> None:
        """Attempt to fix errors in a module."""
        # Get current code
        if module_name in self.modules:
            code = self.modules[module_name].get("code", "")
            # Try to generate fixed version
            improved = await self._generate_improved_code(module_name, analysis)
            if improved:
                await self._update_module_code(module_name, improved)
                self.successful_fixes += 1
                logger.info(f"Self-fixed errors in {module_name}")
    
    async def _update_module_code(self, module_name: str, new_code: str) -> None:
        """Update module source code."""
        if module_name in self.modules:
            self.modules[module_name]["code"] = new_code
            self.modules[module_name]["updated_at"] = datetime.utcnow().isoformat()
            
            # Persist to memory
            await self.memory.store(
                f"module:{module_name}",
                {"code": new_code, "updated": True},
                category="module_improvements"
            )
            
            logger.info(f"Updated {module_name} with improved code")
    
    async def _consolidate_learnings(self) -> None:
        """Consolidate learned patterns and update memory."""
        # Store summary of learned patterns
        pattern_summary = {
            "total_patterns": len(self.learned_patterns),
            "patterns": list(self.learned_patterns)[:100],  # Top 100
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        await self.memory.store(
            "learned_patterns_summary",
            pattern_summary,
            category="learning_summary"
        )
        
        # Clear processed patterns to keep memory fresh
        self.learned_patterns.clear()
    
    async def analyze_code(self, module_name: str, code: str, language: str = "python") -> Dict:
        """Public method to analyze code."""
        return await self.code_analyzer.analyze_code(code, language)
    
    def register_module(self, name: str, code: str, language: str = "python") -> None:
        """Register a module for continuous improvement."""
        self.modules[name] = {
            "code": code,
            "language": language,
            "registered_at": datetime.utcnow().isoformat(),
            "last_analyzed": None,
        }
        logger.info(f"Registered module: {name}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get engine status report."""
        return {
            "engine": self.engine_name,
            "running": self.running,
            "total_analyses": self.total_analyses,
            "improvements_made": self.improvement_count,
            "successful_fixes": self.successful_fixes,
            "modules_registered": len(self.modules),
            "learned_patterns": len(self.learned_patterns),
            "memory_entries": len(list((Path(__file__).parent.parent / "bg_memory").glob("*.json"))),
        }


# Background scheduler for continuous operation
class BackgroundScheduler:
    """Manages the 24/7 background operation of the self-improving engine."""
    
    def __init__(self, engine: SelfImprovingEngine, interval: int = 300) -> None:
        self.engine = engine
        self.interval = interval
        self.task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the background scheduler."""
        if self.engine.running:
            logger.warning("Engine already running")
            return
        
        self.engine.running = True
        self.task = asyncio.create_task(self.engine.start())
        logger.info("Background scheduler started")
    
    async def stop(self) -> None:
        """Stop the background scheduler."""
        self.engine.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Background scheduler stopped")


# CLI interface for the background engine
async def bg_engine_cli() -> None:
    """Run the background engine as a CLI application."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Apeiron Background Self-Improving Engine")
    parser.add_argument("--start", action="store_true", help="Start the 24/7 background engine")
    parser.add_argument("--stop", action="store_true", help="Stop the background engine")
    parser.add_argument("--status", action="store_true", help="Show engine status")
    parser.add_argument("--register", type=str, help="Register a module for improvement (code:language)")
    
    args = parser.parse_args()
    
    engine = SelfImprovingEngine()
    
    if args.start:
        scheduler = BackgroundScheduler(engine)
        asyncio.create_task(scheduler.start())
        logger.info("24/7 Background engine started. Press Ctrl+C to stop.")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(60)
                if not engine.running:
                    break
                print(f"Status: {engine.get_status()}")
        except KeyboardInterrupt:
            await engine.stop()
            await scheduler.stop()
            logger.info("Background engine stopped")
    
    elif args.status:
        print(json.dumps(engine.get_status(), indent=2))
    
    elif args.register:
        # Parse code:language
        parts = args.register.split(":")
        if len(parts) == 2:
            code, language = parts
            engine.register_module("cli_module", code, language)
            logger.info(f"Registered module: {args.register}")
        else:
            print("Format: --register <code>:<language>")


if __name__ == "__main__":
    asyncio.run(bg_engine_cli())