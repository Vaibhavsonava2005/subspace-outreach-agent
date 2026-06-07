# -*- coding: utf-8 -*-
"""
Stage 2 – Prospeo Decision-Maker Discovery
===========================================

Searches for key decision-makers (CEO, Founder, CTO, VP Sales, Director)
at each target company using the Prospeo API.

Created by Vaibhav Sonava
"""
from __future__ import annotations

import random
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

from pipeline.models import Company, DecisionMaker

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROSPEO_API_URL = "https://api.prospeo.io/search-person"
REQUEST_TIMEOUT = 30.0
TARGET_TITLES = ["CEO", "Founder", "CTO", "VP Sales", "Director"]

# Fallback data used when the API key is missing or calls fail
_FALLBACK_FIRST_NAMES = ["Aarav", "Priya", "James", "Sara", "Chen", "Maria", "Liam", "Fatima"]
_FALLBACK_LAST_NAMES = ["Patel", "Sharma", "Williams", "Kim", "Garcia", "Müller", "Singh", "Ali"]


class ProspeoStage:
    """Stage 2: Discover decision-makers at target companies via Prospeo."""

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
    def _search_person(self, domain: str, title: str) -> list[dict]:
        """Query Prospeo for a single (domain, title) pair."""
        headers = {
            "X-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {"job_title": title, "company_website": domain, "limit": 5}

        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(PROSPEO_API_URL, json=payload, headers=headers)

            if response.status_code == 401:
                logger.error("Prospeo API: 401 Unauthorized – check your API key.")
                raise httpx.HTTPStatusError(
                    "Unauthorized", request=response.request, response=response
                )
            if response.status_code == 429:
                logger.warning("Prospeo API: 429 Rate-limited – backing off.")
                raise httpx.HTTPStatusError(
                    "Rate limited", request=response.request, response=response
                )

            response.raise_for_status()

        data = response.json()
        # Prospeo may return a single object or a list; normalise.
        results = data.get("results", data.get("data", []))
        if isinstance(results, dict):
            results = [results]
        return results if isinstance(results, list) else []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def run(self, companies: List[Company]) -> List[DecisionMaker]:
        """
        Search for decision-makers across all *companies*.

        Returns a deduplicated list of :class:`DecisionMaker` instances.
        Falls back to realistic mock data when the API is unavailable.
        """
        logger.info(
            "🔍  Prospeo stage – searching decision-makers across {} companies",
            len(companies),
        )

        if not self.api_key:
            logger.warning("Prospeo API key is empty; returning fallback decision-makers.")
            return self._fallback(companies)

        decision_makers: list[DecisionMaker] = []
        seen_keys: set[str] = set()  # (name_lower, domain) for dedup

        for company in companies:
            for title in TARGET_TITLES:
                try:
                    results = self._search_person(company.domain, title)
                    for person in results:
                        name = (
                            person.get("full_name")
                            or f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
                        )
                        if not name:
                            continue
                        dedup_key = (name.lower(), company.domain)
                        if dedup_key in seen_keys:
                            continue
                        seen_keys.add(dedup_key)

                        dm = DecisionMaker(
                            name=name,
                            title=person.get("title", title),
                            company_domain=company.domain,
                            linkedin_url=person.get("linkedin_url", person.get("linkedin", "")),
                            email=person.get("email", ""),
                            email_verified=bool(person.get("email", "")),
                            confidence_score=0.0,
                        )
                        decision_makers.append(dm)
                except Exception as exc:
                    logger.warning(
                        "Prospeo lookup failed for {} / '{}': {}", company.domain, title, exc
                    )

        if not decision_makers:
            logger.warning("Prospeo returned 0 decision-makers; using fallback data.")
            return self._fallback(companies)

        logger.success(
            "Prospeo stage complete – {} decision-makers discovered.", len(decision_makers)
        )
        return decision_makers

    # ------------------------------------------------------------------
    # Fallback mock data
    # ------------------------------------------------------------------
    @staticmethod
    def _fallback(companies: list[Company]) -> list[DecisionMaker]:
        """Generate realistic mock DecisionMaker entries for each company."""
        rng = random.Random(42)  # deterministic for reproducibility
        fallback: list[DecisionMaker] = []
        for company in companies:
            for title in TARGET_TITLES[:3]:  # CEO, Founder, CTO
                first = rng.choice(_FALLBACK_FIRST_NAMES)
                last = rng.choice(_FALLBACK_LAST_NAMES)
                name = f"{first} {last}"
                slug = f"{first.lower()}-{last.lower()}"
                fallback.append(
                    DecisionMaker(
                        name=name,
                        title=title,
                        company_domain=company.domain,
                        linkedin_url=f"https://linkedin.com/in/{slug}",
                        email="",
                        email_verified=False,
                        confidence_score=0.0,
                    )
                )
        return fallback
