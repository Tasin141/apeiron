#!/usr/bin/env python3
"""Deep-research and intelligence data pipelines for web scraping, search aggregation,
and automated research synthesis (STORM-inspired) - Cloud Optimized."""

import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import structlog

logger = structlog.get_logger("apeiron.research")


@dataclass
class ResearchNode:
    """Represents a node in the research graph."""
    url: str
    title: str
    content: str
    depth: int
    source: str
    timestamp: float
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchReport:
    """Structured research report output."""
    query: str
    summary: str
    findings: List[ResearchNode]
    sources: List[str]
    generated_at: float
    model_used: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)


class WebScraper:
    """High-speed dynamic web scraping interface using Crawl4AI or fallback."""

    def __init__(self, headless: bool = True, max_concurrent: int = 3) -> None:
        self.headless = headless
        self.max_concurrent = max_concurrent
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the crawler."""
        if self._initialized:
            return
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerConfig
            logger.info(
                "Initializing web scraper",
                headless=self.headless,
                max_concurrent=self.max_concurrent,
            )
            self._initialized = True
        except ImportError:
            logger.warning("Crawl4AI not available, using requests fallback")
            self._initialized = True

    async def scrape_url(
        self,
        url: str,
        selector: Optional[str] = None,
        timeout: float = 30.0,
    ) -> Optional[ResearchNode]:
        """Scrape a single URL and return a ResearchNode."""
        try:
            # Try Crawl4AI first
            try:
                from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerConfig

                browser_config = BrowserConfig(
                    headless=self.headless,
                    viewport_width=1920,
                    viewport_height=1080,
                )
                crawler_config = CrawlerConfig(
                    timeout=timeout,
                    remove_overlay_elements=True,
                    simulate_user=True,
                )

                async with AsyncWebCrawler(browser_config=browser_config) as crawler:
                    result = await crawler.arun(
                        url=url,
                        config=crawler_config,
                    )

                    if result.success and result.html:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(result.html, "html.parser")

                        # Remove script and style elements
                        for script in soup(["script", "style", "header", "footer", "nav"]):
                            script.decompose()

                        text = soup.get_text(separator=" ").strip()
                        if not text:
                            return None

                        # Extract title
                        title = soup.find("title")
                        title_text = title.get_text().strip() if title else "No title"

                        return ResearchNode(
                            url=url,
                            title=title_text,
                            content=text[:5000],
                            depth=1,
                            source="crawl4ai",
                            timestamp=time.time(),
                            metadata={
                                "final_url": result.final_url if hasattr(result, 'final_url') else url,
                                "status_code": result.status_code if hasattr(result, 'status_code') else 200,
                            }
                        )
            except Exception as e:
                logger.warning(f"Crawl4AI failed for {url}, using fallback: {e}")

            # Fallback: requests + BeautifulSoup (lighter)
            import requests
            from bs4 import BeautifulSoup

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code != 200:
                logger.warning(f"Failed to scrape {url}: status {response.status_code}")
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove unwanted elements
            for element in soup(["script", "style", "header", "footer", "nav", "aside"]):
                element.decompose()

            text = soup.get_text(separator=" ").strip()
            if not text:
                return None

            title = soup.find("title")
            title_text = title.get_text().strip() if title else "No title"

            return ResearchNode(
                url=url,
                title=title_text,
                content=text[:5000],
                depth=1,
                source="requests",
                timestamp=time.time(),
                metadata={"status_code": response.status_code},
            )

        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return None


class SearchAggregator:
    """Meta-search aggregation wrapper for SearXNG / DuckDuckGo - Cloud Optimized."""

    def __init__(self, engines: List[str] = None) -> None:
        self.engines = engines or ["duckduckgo", "searxng"]
        self._session = None

    async def search(
        self,
        query: str,
        max_results: int = 20,
        engines: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Search the web using multiple engines and aggregate results."""
        engines = engines or self.engines
        all_results: List[Dict[str, Any]] = []

        for engine in engines:
            try:
                results = await self._search_engine(engine, query, max_results // len(engines))
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"Search engine {engine} failed: {e}")

        # Deduplicate by URL
        seen_urls: Set[str] = set()
        deduped = []
        for result in all_results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduped.append(result)

        return deduped[:max_results]

    async def _search_engine(
        self,
        engine: str,
        query: str,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Search using a specific engine."""
        if engine == "duckduckgo":
            return await self._duckduckgo(query, max_results)
        elif engine == "searxng":
            return await self._searxng(query, max_results)
        else:
            logger.warning(f"Unknown search engine: {engine}")
            return []

    async def _duckduckgo(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo."""
        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for i, result in enumerate(ddgs.text(
                    query,
                    max_results=max_results,
                    region="wt-wt",
                    safesearch="off",
                )):
                    if i >= max_results:
                        break
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("href", ""),
                        "snippet": result.get("body", ""),
                        "source": "duckduckgo",
                    })
            return results
        except ImportError:
            logger.warning("duckduckgo-search not available")
            return []
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []

    async def _searxng(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search using SearXNG instance."""
        try:
            import requests

            # Default SearXNG instance (public ones)
            searxng_instances = [
                "https://searx.be",
                "https://searxng.org",
                "https://libre.website/searxng",
            ]

            for base_url in searxng_instances:
                try:
                    params = {"q": query, "format": "json"}
                    response = requests.get(
                        f"{base_url}/search",
                        params=params,
                        timeout=15,
                        headers={"User-Agent": "Apeiron/1.0"},
                    )
                    if response.status_code == 200:
                        data = response.json()
                        results = []
                        for item in data[:max_results]:
                            results.append({
                                "title": item.get("title", ""),
                                "url": item.get("url", ""),
                                "snippet": item.get("content", ""),
                                "source": "searxng",
                            })
                        return results
                except Exception:
                    continue

            return []
        except Exception as e:
            logger.error(f"SearXNG search error: {e}")
            return []


class ResearchSynthesizer:
    """STORM-inspired multi-step automated research report generator."""

    def __init__(self, max_depth: int = 3, max_nodes_per_level: int = 10) -> None:
        self.max_depth = max_depth
        self.max_nodes_per_level = max_nodes_per_level
        self.scraper = WebScraper()
        self.search_aggregator = SearchAggregator()

    async def generate_report(
        self,
        query: str,
        initial_urls: Optional[List[str]] = None,
    ) -> ResearchReport:
        """Generate a comprehensive research report for a given query."""
        logger.info(f"Starting research synthesis", query=query)

        # Step 1: Search for relevant pages
        search_results = await self.search_aggregator.search(query, max_results=20)

        # Step 2: Build research graph by scraping URLs
        nodes: List[ResearchNode] = []
        if initial_urls:
            scrape_tasks = [self.scraper.scrape_url(url) for url in initial_urls]
            scraped = await asyncio.gather(*scrape_tasks)
            nodes = [n for n in scraped if n is not None]
        else:
            # Scrape search results
            scrape_tasks = []
            for result in search_results[:10]:
                url = result.get("url", "")
                if url:
                    scrape_tasks.append(self.scraper.scrape_url(url))

            if scrape_tasks:
                scraped = await asyncio.gather(*scrape_tasks)
                nodes = [n for n in scraped if n is not None]

        # Step 3: Deduplicate and rank nodes
        seen_urls: Set[str] = set()
        unique_nodes: List[ResearchNode] = []
        for node in nodes:
            if node.url not in seen_urls:
                seen_urls.add(node.url)
                unique_nodes.append(node)

        # Step 4: Generate summary and findings
        summary_parts = []
        all_findings: List[ResearchNode] = []

        for node in unique_nodes[:self.max_nodes_per_level]:
            summary_parts.append(f"- {node.title}: {node.content[:200]}...")
            all_findings.append(node)

        # Step 5: Create report
        query_lower = query.lower()
        if any(kw in query_lower for kw in ["cybersecurity", "threat", "osint"]):
            report = ResearchReport(
                query=query,
                summary=self._generate_cybersecurity_summary(all_findings),
                findings=all_findings,
                sources=[node.url for node in unique_nodes[:10]],
                generated_at=time.time(),
                model_used="STORM-inspired synthesizer",
            )
        else:
            report = ResearchReport(
                query=query,
                summary=" ".join(summary_parts) if summary_parts else "No significant findings.",
                findings=all_findings,
                sources=[node.url for node in unique_nodes[:10]],
                generated_at=time.time(),
                model_used="STORM-inspired synthesizer",
            )

        logger.info(
            f"Research report generated",
            query=query,
            findings_count=len(report.findings),
            sources_count=len(report.sources),
        )

        return report

    def _generate_cybersecurity_summary(self, findings: List[ResearchNode]) -> str:
        """Generate cybersecurity-focused summary from findings."""
        threats = []
        for node in findings:
            content_lower = node.content.lower()
            if any(
                kw in content_lower
                for kw in ["vulnerability", "exploit", "malware", "ransomware", "breach", "attack"]
            ):
                threats.append(
                    f"[{node.title}] {node.content[:150]}..."
                )

        if threats:
            return f"Cybersecurity threats identified:\n" + "\n".join(threats[:10])
        return "No specific cybersecurity threats found in current sources."


# OSINT Threat-Intelligence Feed Collector
class OSINTCollector:
    """Public OSINT threat-intelligence feed collector for cybersecurity tracking."""

    def __init__(self) -> None:
        self.search_aggregator = SearchAggregator()
        self.keywords = [
            "cyber threat intelligence",
            "malware analysis",
            "vulnerability disclosure",
            "APT report",
            "CVE feed",
            " threat actor",
        ]

    async def collect_threat_feeds(self, max_feeds: int = 20) -> List[ResearchReport]:
        """Collect OSINT threat-intelligence feeds."""
        reports: List[ResearchReport] = []

        for keyword in self.keywords[:5]:  # Limit to avoid rate limiting
            try:
                results = await self.search_aggregator.search(keyword, max_results=5)
                if results:
                    report = ResearchReport(
                        query=keyword,
                        summary=f"Search results for: {keyword}",
                        findings=[],
                        sources=[r.get("url", "") for r in results[:5]],
                        generated_at=time.time(),
                        model_used="OSINT collector",
                    )
                    reports.append(report)
            except Exception as e:
                logger.warning(f"OSINT collection failed for {keyword}: {e}")

        return reports


# CLI interface
async def cli() -> None:
    """Run the research crawler as an interactive CLI."""
    import json

    console = __import__("rich.console").Console()
    console.print(Panel.fit(
        "[bold blue]Apeiron Research Crawler[/]\n"
        "[deep-purple1]Deep-research and intelligence data pipelines - Cloud Optimized[/]",
        title="Research Crawler",
    ))

    synthesizer = ResearchSynthesizer()
    osint = OSINTCollector()

    while True:
        console.print("\n[bold cyan]Options:[/]")
        console.print("1. Synthesize research report")
        console.print("2. Collect OSINT threat feeds")
        console.print("3. Search web (meta-search)")
        console.print("4. Scrape single URL")
        console.print("0. Back to main menu")
        console.print()

        choice = console.input("[green]Select:[/] ").strip()

        if choice == "0":
            break
        elif choice == "1":
            query = console.input("[cyan]Enter research query:[/] ")
            report = await synthesizer.generate_report(query)
            console.print(f"\n[bold]Research Report:[/]")
            console.print(f"  Query: {report.query}")
            console.print(f"  Summary: {report.summary[:500]}...")
            console.print(f"  Findings: {len(report.findings)} nodes")
            console.print(f"  Sources: {len(report.sources)} URLs")
            console.print(f"  Generated: {report.generated_at}")
            console.print(f"\n[bold]Full JSON:[/]")
            console.print(report.to_json())
        elif choice == "2":
            console.print("[cyan]Collecting OSINT threat feeds...[/]")
            reports = await osint.collect_threat_feeds()
            for i, report in enumerate(reports, 1):
                console.print(f"\n[bold]Report {i}:[/] {report.query}")
                console.print(f"  Sources: {len(report.sources)}")
                console.print(f"  Summary: {report.summary[:200]}...")
        elif choice == "3":
            query = console.input("[cyan]Enter search query:[/] ")
            results = await synthesizer.search_aggregator.search(query, max_results=10)
            console.print(f"\n[bold]Search results for:[/] {query}")
            for i, result in enumerate(results[:10], 1):
                console.print(f"\n[{i}] {result.get('title', 'No title')}")
                console.print(f"    URL: {result.get('url', 'N/A')[:80]}...")
                console.print(f"    Snippet: {result.get('snippet', '')[:100]}...")
        elif choice == "4":
            url = console.input("[cyan]Enter URL to scrape:[/] ")
            node = await WebScraper().scrape_url(url)
            if node:
                console.print(f"\n[bold]Scraped Node:[/]")
                console.print(f"  Title: {node.title}")
                console.print(f"  URL: {node.url}")
                console.print(f"  Depth: {node.depth}")
                console.print(f"  Content preview: {node.content[:200]}...")
            else:
                console.print("[red]Failed to scrape URL.[/]")


if __name__ == "__main__":
    import asyncio
    asyncio.run(cli())