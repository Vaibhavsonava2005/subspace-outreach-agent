# -*- coding: utf-8 -*-
"""
Pipeline Orchestrator
=====================

Master controller that chains the four pipeline stages (Ocean → Prospeo →
Eazyreach → Brevo), provides a rich progress UI, captures timing metrics,
and persists results.

Created by Vaibhav Sonava
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from loguru import logger
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
)

from pipeline.models import PipelineResult
from pipeline.ocean_stage import OceanStage
from pipeline.prospeo_stage import ProspeoStage
from pipeline.brevo_stage import BrevoStage
from pipeline.exporter import ResultExporter


class PipelineOrchestrator:
    """
    Chains all four outreach-pipeline stages and produces a
    :class:`PipelineResult` with timing metrics.

    Parameters
    ----------
    config:
        Dictionary containing API keys and sender details::

            {
                "ocean_api_key": "...",
                "prospeo_api_key": "...",
                "eazyreach_api_key": "...",
                "brevo_api_key": "...",
                "sender_email": "you@company.com",
                "sender_name": "Your Name",
                "output_dir": "output",       # optional, default "output"
            }
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

        # Instantiate stages
        self.ocean = OceanStage(api_key=config.get("ocean_api_key", ""))
        self.prospeo = ProspeoStage(api_key=config.get("prospeo_api_key", ""))
        self.brevo = BrevoStage(
            api_key=config.get("brevo_api_key", ""),
            sender_email=config.get("sender_email", "outreach@example.com"),
            sender_name=config.get("sender_name", "Outreach Bot"),
        )

        self.output_dir = config.get("output_dir", "output")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def run(self, domain: str, dry_run: bool = False) -> PipelineResult:
        """
        Execute the full outreach pipeline for *domain*.

        Parameters
        ----------
        domain:
            Target company domain (e.g. ``"acme.com"``).
        dry_run:
            If ``True``, emails are composed but not actually sent.

        Returns
        -------
        PipelineResult
            Aggregated results with timing data and all discovered artefacts.
        """
        logger.info("=" * 60)
        logger.info("🚀  Pipeline started for domain: {}", domain)
        logger.info("=" * 60)

        result = PipelineResult(input_domain=domain)
        stage_timings: dict[str, float] = {}
        pipeline_start = time.perf_counter()

        stages = [
            ("🌊  Ocean.io – Company Discovery", self._run_ocean, {"domain": domain}),
            ("🔍  Prospeo – Decision-Maker Search & Email", self._run_prospeo, {}),
            ("✉️   Brevo – Email Dispatch", self._run_brevo, {"domain": domain, "dry_run": dry_run}),
        ]

        # ---- Rich progress bar ----
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=30),
            TimeElapsedColumn(),
            transient=False,
        ) as progress:
            task_id = progress.add_task("Pipeline", total=len(stages))

            for description, handler, kwargs in stages:
                progress.update(task_id, description=description)
                stage_name = description.split("–")[0].strip()
                t0 = time.perf_counter()

                try:
                    handler(result, **kwargs)
                except Exception as exc:
                    logger.error("Stage '{}' crashed: {}", stage_name, exc)

                elapsed = round(time.perf_counter() - t0, 3)
                stage_timings[stage_name] = elapsed
                logger.info("⏱  {} completed in {:.3f}s", stage_name, elapsed)
                progress.advance(task_id)

        result.stage_timings = stage_timings
        result.total_duration = round(time.perf_counter() - pipeline_start, 3)
        result.success = True

        # ---- Persist results ----
        self._save_results(result)

        logger.info("=" * 60)
        logger.info(
            "✅  Pipeline finished in {:.3f}s  |  {} companies  |  {} DMs  |  {} emails",
            result.total_duration,
            len(result.companies_found),
            len(result.decision_makers),
            len(result.emails_sent),
        )
        logger.info("=" * 60)

        return result

    # ------------------------------------------------------------------
    # Internal stage runners
    # ------------------------------------------------------------------
    def _run_ocean(self, result: PipelineResult, *, domain: str) -> None:
        result.companies_found = self.ocean.run(domain)

    def _run_prospeo(self, result: PipelineResult) -> None:
        result.decision_makers = self.prospeo.run(result.companies_found)
        result.emails_enriched = [dm for dm in result.decision_makers if dm.email]

    def _run_brevo(
        self, result: PipelineResult, *, domain: str, dry_run: bool
    ) -> None:
        result.emails_sent = self.brevo.run(
            result.decision_makers, input_domain=domain, dry_run=dry_run
        )

    # ------------------------------------------------------------------
    # Result persistence
    # ------------------------------------------------------------------
    def _save_results(self, result: PipelineResult) -> None:
        """Save pipeline results as JSON and CSV to the output directory."""
        try:
            output_path = Path(self.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            json_file = ResultExporter.to_json(result, str(output_path))
            csv_file = ResultExporter.to_csv(result, str(output_path))
            summary = ResultExporter.to_summary(result)

            logger.info("📁  JSON saved → {}", json_file)
            logger.info("📁  CSV  saved → {}", csv_file)
            logger.info("\n{}", summary)
        except Exception as exc:
            logger.error("Failed to save results: {}", exc)
