# -*- coding: utf-8 -*-
"""
Stage 1 – Ocean.io Company Discovery
=====================================

Discovers lookalike companies for a given domain using the Ocean.io API.
Includes retry logic, structured error handling, and graceful fallbacks.

Created by Vaibhav Sonava
"""
from __future__ import annotations

from typing import List

import httpx
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from pipeline.models import Company

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OCEAN_API_URL = "https://api.ocean.io/v1/companies/similar"
REQUEST_TIMEOUT = 30.0  # seconds


class OceanStage:
    """Stage 1: Discover lookalike companies via Ocean.io."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key.strip() if api_key else ""

    # ------------------------------------------------------------------
    # Internal HTTP call with tenacity retry
    # ------------------------------------------------------------------
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        before_sleep=before_sleep_log(logger, "WARNING"),  # type: ignore[arg-type]
        reraise=True,
    )
    def _call_ocean_api(self, domain: str) -> list[dict]:
        """Execute the Ocean.io API call with automatic retries."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {"domain": domain, "limit": 5}

        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(OCEAN_API_URL, json=payload, headers=headers)

            # Handle specific status codes before raising
            if response.status_code == 401:
                logger.warning("Ocean.io API: 401 Unauthorized – check your API key.")
                raise httpx.HTTPStatusError(
                    "Unauthorized", request=response.request, response=response
                )
            if response.status_code == 403:
                logger.warning("Ocean.io API: 403 Forbidden – insufficient permissions.")
                raise httpx.HTTPStatusError(
                    "Forbidden", request=response.request, response=response
                )
            if response.status_code == 429:
                logger.warning("Ocean.io API: 429 Rate-limited – backing off.")
                raise httpx.HTTPStatusError(
                    "Rate limited", request=response.request, response=response
                )

            response.raise_for_status()

        data = response.json()
        return data.get("companies", [])

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def run(self, domain: str) -> List[Company]:
        """
        Discover similar companies for *domain*.

        Returns a list of :class:`Company` instances.  On failure or when no
        API key is configured, returns a single-element fallback list
        containing only the input domain.
        """
        logger.info("🌊  Ocean.io stage – discovering companies similar to '{}'", domain)

        if not self.api_key:
            logger.warning("Ocean.io API key is empty; returning fallback for '{}'.", domain)
            return self._fallback(domain)

        try:
            raw_companies = self._call_ocean_api(domain)
            if not raw_companies:
                logger.warning("Ocean.io returned 0 companies; using fallback.")
                return self._fallback(domain)

            companies: list[Company] = []
            for item in raw_companies:
                try:
                    companies.append(
                        Company(
                            domain=item.get("domain", domain),
                            name=item.get("name", ""),
                            industry=item.get("industry", ""),
                            employee_count=int(item.get("employee_count", 0) or 0),
                            description=item.get("description", ""),
                        )
                    )
                except (ValueError, TypeError) as exc:
                    logger.warning("Skipping malformed company record: {} – {}", item, exc)

            logger.success(
                "Ocean.io stage complete – {} companies discovered.", len(companies)
            )
            return companies if companies else self._fallback(domain)

        except Exception as exc:
            logger.warning("Ocean.io stage failed: {} – returning fallback.", exc)
            return self._fallback(domain)

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------
    @staticmethod
    def _fallback(domain: str) -> list[Company]:
        """Return a minimal fallback list containing only the input domain."""
        return [
            Company(
                domain=domain,
                name=domain.split(".")[0].capitalize(),
                industry="Unknown",
                employee_count=0,
                description=f"Fallback entry for {domain}",
            )
        ]
