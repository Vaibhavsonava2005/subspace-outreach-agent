# -*- coding: utf-8 -*-
"""
Result Exporter
===============

Exports :class:`PipelineResult` to JSON, CSV, and human-readable summary
formats.  All file outputs are written to a configurable output directory.

Created by Vaibhav Sonava
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from pipeline.models import PipelineResult


class ResultExporter:
    """Stateless exporter with class-method utilities."""

    # ------------------------------------------------------------------
    # JSON export
    # ------------------------------------------------------------------
    @staticmethod
    def to_json(result: PipelineResult, output_dir: str) -> str:
        """
        Serialise the full pipeline result to a pretty-printed JSON file.

        Parameters
        ----------
        result:
            The :class:`PipelineResult` to export.
        output_dir:
            Directory path where the JSON file will be written.

        Returns
        -------
        str
            Absolute path of the written JSON file.
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"pipeline_result_{result.input_domain.replace('.', '_')}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)

        payload = result.to_dict()
        payload["exported_at"] = datetime.now(tz=timezone.utc).isoformat()

        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

        logger.debug("JSON export written to {}", filepath)
        return os.path.abspath(filepath)

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------
    @staticmethod
    def to_csv(result: PipelineResult, output_dir: str) -> str:
        """
        Export decision-maker data as a CSV file.

        Columns: name, title, company, linkedin, email, verified, confidence.

        Parameters
        ----------
        result:
            The :class:`PipelineResult` whose decision-makers will be exported.
        output_dir:
            Directory path where the CSV file will be written.

        Returns
        -------
        str
            Absolute path of the written CSV file.
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"decision_makers_{result.input_domain.replace('.', '_')}_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)

        fieldnames = ["name", "title", "company", "linkedin", "email", "verified", "confidence"]

        # Prefer enriched list; fall back to raw decision_makers
        dm_list = result.emails_enriched if result.emails_enriched else result.decision_makers

        with open(filepath, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for dm in dm_list:
                writer.writerow(
                    {
                        "name": dm.name,
                        "title": dm.title,
                        "company": dm.company_domain,
                        "linkedin": dm.linkedin_url,
                        "email": dm.email,
                        "verified": dm.email_verified,
                        "confidence": dm.confidence_score,
                    }
                )

        logger.debug("CSV export written to {}", filepath)
        return os.path.abspath(filepath)

    # ------------------------------------------------------------------
    # Human-readable summary
    # ------------------------------------------------------------------
    @staticmethod
    def to_summary(result: PipelineResult) -> str:
        """
        Return a formatted multi-line text summary of the pipeline run.

        The summary includes stage timings, counts, and a quick table of
        discovered decision-makers.
        """
        lines: list[str] = [
            "",
            "╔══════════════════════════════════════════════════════════╗",
            "║            PIPELINE RUN SUMMARY                        ║",
            "╠══════════════════════════════════════════════════════════╣",
            f"║  Domain           : {result.input_domain:<36} ║",
            f"║  Companies Found  : {len(result.companies_found):<36} ║",
            f"║  Decision Makers  : {len(result.decision_makers):<36} ║",
            f"║  Emails Enriched  : {len(result.emails_enriched):<36} ║",
            f"║  Emails Composed  : {len(result.emails_sent):<36} ║",
            f"║  Total Duration   : {result.total_duration:<36.3f} ║",
            f"║  Success          : {'✅ Yes' if result.success else '❌ No':<36} ║",
            "╠══════════════════════════════════════════════════════════╣",
            "║  STAGE TIMINGS                                         ║",
        ]

        for stage, elapsed in result.stage_timings.items():
            lines.append(f"║    {stage:<26} {elapsed:>8.3f}s              ║")

        lines.append("╠══════════════════════════════════════════════════════════╣")
        lines.append("║  DECISION MAKERS                                       ║")
        lines.append("║  Name                    Title          Email           ║")
        lines.append("║  ──────────────────────── ────────────── ──────────────  ║")

        dm_list = result.emails_enriched if result.emails_enriched else result.decision_makers
        for dm in dm_list[:10]:  # cap at 10 for readability
            name_col = dm.name[:24].ljust(24)
            title_col = dm.title[:14].ljust(14)
            email_col = (dm.email or "—")[:16].ljust(16)
            lines.append(f"║  {name_col} {title_col} {email_col}║")

        if len(dm_list) > 10:
            lines.append(f"║  … and {len(dm_list) - 10} more                                       ║")

        lines.append("╚══════════════════════════════════════════════════════════╝")
        lines.append("")

        return "\n".join(lines)
