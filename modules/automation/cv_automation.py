#!/usr/bin/env python3
"""Automated Markdown and PDF resume/portfolio generation engine based on
structured user profiles."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger("apeiron.cv")


class ResumeGenerationError(Exception):
    """Raised when resume generation fails."""
    pass


class CVAutomationEngine:
    """Automated Markdown and PDF resume/portfolio generation engine.

    Supports structured user profiles with education, experience, skills,
    projects, and generates both Markdown and PDF output.
    """

    def __init__(self, profile: Optional[Dict[str, Any]] = None) -> None:
        self.profile = profile or {}
        self._validate_profile()

    def _validate_profile(self) -> None:
        """Validate the user profile structure."""
        required_sections = ["name", "contact", "experience", "education", "skills"]
        for section in required_sections:
            if section not in self.profile:
                logger.warning(f"Missing profile section: {section}")

    def update_profile(self, profile: Dict[str, Any]) -> None:
        """Update the user profile with new data."""
        self.profile = profile
        self._validate_profile()
        logger.info("Profile updated", sections=list(profile.keys()))

    def _generate_markdown(self) -> str:
        """Generate Markdown resume from profile data."""
        name = self.profile.get("name", "Your Name")
        contact = self.profile.get("contact", {})
        experience = self.profile.get("experience", [])
        education = self.profile.get("education", [])
        skills = self.profile.get("skills", [])
        projects = self.profile.get("projects", [])

        lines = [
            f"# {name}'s Resume",
            "",
            "## Contact",
        ]

        # Contact info
        if contact.get("email"):
            lines.append(f"- 📧 {contact['email']}")
        if contact.get("phone"):
            lines.append(f"- 📞 {contact['phone']}")
        if contact.get("github"):
            lines.append(f"- 💻 {contact['github']}")
        if contact.get("linkedin"):
            lines.append(f"- 🔗 {contact['linkedin']}")
        if contact.get("portfolio"):
            lines.append(f"- 🌐 {contact['portfolio']}")

        lines.append("")
        lines.append("## Experience")

        for exp in experience:
            title = exp.get("title", "Position")
            company = exp.get("company", "Company")
            dates = exp.get("dates", "")
            bullets = exp.get("bullets", [])

            lines.append(f"### {title} at {company}")
            if dates:
                lines.append(f"*{dates}*")
            for bullet in bullets:
                lines.append(f"- {bullet}")
            lines.append("")

        lines.append("## Education")

        for edu in education:
            degree = edu.get("degree", "Degree")
            institution = edu.get("institution", "Institution")
            graduation = edu.get("graduation", "")
            lines.append(f"### {degree} at {institution}")
            if graduation:
                lines.append(f"*Graduation: {graduation}*")
            lines.append("")

        lines.append("## Skills")

        skill_categories: Dict[str, List[str]] = {}
        for skill in skills:
            category = skill.get("category", "Other")
            name = skill.get("name", "")
            if category not in skill_categories:
                skill_categories[category] = []
            skill_categories[category].append(name)

        for category, items in skill_categories.items():
            lines.append(f"### {category}")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")

        lines.append("## Projects")

        for proj in projects:
            title = proj.get("title", "Project")
            description = proj.get("description", "")
            links = proj.get("links", [])

            lines.append(f"### {title}")
            if description:
                lines.append(description)
            if links:
                for link in links:
                    lines.append(f"- {link}")
            lines.append("")

        return "\n".join(lines)

    def generate_markdown(self) -> str:
        """Public method to generate Markdown resume."""
        return self._generate_markdown()

    async def generate_pdf(self, output_path: Optional[str] = None) -> str:
        """Generate PDF resume from profile data.

        Uses weasyprint or reportlab for PDF generation.
        Falls back to writing Markdown if PDF generation is unavailable.
        """
        try:
            from weasyprint import HTML

            markdown_content = self._generate_markdown()
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        max-width: 8.5in;
                        margin: 0 auto;
                        padding: 1in;
                        line-height: 1.6;
                        color: #333;
                    }}
                    h1 {{
                        color: #2c3e50;
                        border-bottom: 2px solid #3498db;
                        padding-bottom: 10px;
                    }}
                    h2, h3 {{
                        color: #34495e;
                        margin-top: 30px;
                    }}
                    h1 {{
                        font-size: 28pt;
                    }}
                    h2 {{
                        font-size: 18pt;
                    }}
                    h3 {{
                        font-size: 14pt;
                    }}
                    ul {{
                        margin-left: 20px;
                    }}
                    a {{
                        color: #3498db;
                        text-decoration: none;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                </style>
            </head>
            <body>
                {markdown_content.replace('$', '\\$').replace('`', '')}
            </body>
            </html>
            """

            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"resume_{timestamp}.pdf"

            HTML(string=html_content).write_pdf(output_path)

            logger.info(f"PDF generated", path=output_path)
            return output_path

        except ImportError:
            logger.warning("weasyprint not available, writing Markdown fallback")
            # Write Markdown as fallback
            markdown = self._generate_markdown()
            fallback_path = output_path or f"resume_{datetime.now().strftime('%Y%m%d')}.md"
            with open(fallback_path, "w", encoding="utf-8") as f:
                f.write(markdown)
            return fallback_path
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            raise ResumeGenerationError(f"PDF generation failed: {e}")

    def export_resume(
        self,
        format: str = "markdown",
        output_path: Optional[str] = None,
    ) -> str:
        """Export resume in specified format.

        Args:
            format: "markdown" or "pdf"
            output_path: Optional path for output file

        Returns:
            Path to generated file
        """
        if format.lower() == "markdown":
            markdown = self._generate_markdown()
            if output_path is None:
                output_path = f"resume_{datetime.now().strftime('%Y%m%d')}.md"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown)
            logger.info(f"Markdown resume exported", path=output_path)
            return output_path
        elif format.lower() == "pdf":
            return asyncio.run(self.generate_pdf(output_path))
        else:
            raise ResumeGenerationError(f"Unsupported format: {format}")


# For async support
import asyncio

# CLI interface
async def cli() -> None:
    """Run the CV automation engine as an interactive CLI."""
    import json

    from rich.console import RichConsole
    from rich.panel import Panel

    console = RichConsole(stderr=True)
    engine = CVAutomationEngine()

    console.print(Panel.fit(
        "[bold blue]Apeiron CV Automation[/]\n"
        "[white]Markdown and PDF resume/portfolio generation[/]",
        title="CV Engine",
    ))

    while True:
        console.print("\n[bold cyan]Options:[/]")
        console.print("1. Load profile from JSON")
        console.print("2. Update profile fields")
        console.print("3. Generate Markdown resume")
        console.print("4. Generate PDF resume")
        console.print("5. View current profile")
        console.print("0. Back to main menu")
        console.print()

        choice = console.input("[green]Select:[/] ").strip()

        if choice == "0":
            break
        elif choice == "1":
            json_str = console.input("[cyan]Enter profile JSON:[/] ")
            try:
                profile = json.loads(json_str)
                engine.update_profile(profile)
                console.print("[green]Profile loaded successfully![/]")
            except json.JSONDecodeError as e:
                console.print(f"[red]Invalid JSON:[/] {e}")
        elif choice == "2":
            console.print("\n[bold]Current profile sections:[/]")
            sections = list(engine.profile.keys()) if engine.profile else []
            for s in sections:
                console.print(f"  - {s}")
            field = console.input("[cyan]Enter field to update:[/] ").strip()
            value = console.input("[cyan]Enter new value (JSON):[/] ")
            try:
                parsed = json.loads(value)
                engine.profile[field] = parsed
                console.print(f"[green]{field} updated![/]")
            except json.JSONDecodeError:
                console.print(f"[red]Invalid JSON, setting as string.[/]")
                engine.profile[field] = value
                console.print(f"[green]{field} updated![/]")
        elif choice == "3":
            try:
                markdown = engine.generate_markdown()
                console.print("[green]Markdown generated![/]")
                console.print(markdown[:500] + ("..." if len(markdown) > 500 else ""))
            except Exception as e:
                console.print(f"[red]Error:[/] {e}")
        elif choice == "4":
            output = console.input("[cyan]Enter PDF output path (or enter for default):[/] ").strip()
            if not output:
                output = None
            try:
                path = await engine.generate_pdf(output)
                console.print(f"[green]PDF generated:[/] {path}")
            except Exception as e:
                console.print(f"[red]Error:[/] {e}")
        elif choice == "5":
            console.print(f"\n[bold]Current Profile:[/]")
            if engine.profile:
                console.print_json(json.dumps(engine.profile, indent=2))
            else:
                console.print("[yellow]No profile loaded.[/]")


if __name__ == "__main__":
    import asyncio
    asyncio.run(cli())