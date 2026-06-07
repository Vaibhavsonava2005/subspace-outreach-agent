# -*- coding: utf-8 -*-
"""
Pipeline Data Models
====================

Production-grade dataclasses for the cold outreach pipeline.
All models include validation, serialization, and type safety.

Created by Vaibhav Sonava
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Company:
    """Represents a target company discovered via Ocean.io or similar sources."""

    domain: str
    name: str = ""
    industry: str = ""
    employee_count: int = 0
    description: str = ""

    def __post_init__(self) -> None:
        if not self.domain or not self.domain.strip():
            raise ValueError("Company domain must be a non-empty string.")
        self.domain = self.domain.strip().lower()
        self.name = self.name.strip()
        self.industry = self.industry.strip()
        if self.employee_count < 0:
            self.employee_count = 0

    def to_dict(self) -> dict:
        """Serialize the Company to a plain dictionary."""
        return asdict(self)


@dataclass
class DecisionMaker:
    """Represents a key decision-maker found at a target company."""

    name: str
    title: str
    company_domain: str
    linkedin_url: str = ""
    email: str = ""
    email_verified: bool = False
    confidence_score: float = 0.0

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("DecisionMaker name must be a non-empty string.")
        if not self.company_domain or not self.company_domain.strip():
            raise ValueError("DecisionMaker company_domain must be a non-empty string.")
        self.name = self.name.strip()
        self.title = self.title.strip()
        self.company_domain = self.company_domain.strip().lower()
        self.linkedin_url = self.linkedin_url.strip()
        self.email = self.email.strip().lower() if self.email else ""
        self.confidence_score = max(0.0, min(1.0, self.confidence_score))

    def to_dict(self) -> dict:
        """Serialize the DecisionMaker to a plain dictionary."""
        return asdict(self)


@dataclass
class EmailDraft:
    """Represents a composed (and optionally sent) outreach email."""

    to_email: str
    to_name: str
    subject: str
    body_html: str
    company_domain: str
    decision_maker_title: str

    def __post_init__(self) -> None:
        if not self.to_email or not self.to_email.strip():
            raise ValueError("EmailDraft to_email must be a non-empty string.")
        if not self.subject or not self.subject.strip():
            raise ValueError("EmailDraft subject must be a non-empty string.")
        self.to_email = self.to_email.strip().lower()
        self.to_name = self.to_name.strip()
        self.subject = self.subject.strip()
        self.company_domain = self.company_domain.strip().lower()
        self.decision_maker_title = self.decision_maker_title.strip()

    def to_dict(self) -> dict:
        """Serialize the EmailDraft to a plain dictionary (HTML body truncated for readability)."""
        data = asdict(self)
        if len(data.get("body_html", "")) > 500:
            data["body_html_preview"] = data["body_html"][:500] + "…"
        return data


@dataclass
class PipelineResult:
    """Aggregated result produced by a full pipeline run."""

    input_domain: str
    companies_found: list[Company] = field(default_factory=list)
    decision_makers: list[DecisionMaker] = field(default_factory=list)
    emails_enriched: list[DecisionMaker] = field(default_factory=list)
    emails_sent: list[EmailDraft] = field(default_factory=list)
    stage_timings: dict[str, float] = field(default_factory=dict)
    total_duration: float = 0.0
    success: bool = False

    def __post_init__(self) -> None:
        if not self.input_domain or not self.input_domain.strip():
            raise ValueError("PipelineResult input_domain must be a non-empty string.")
        self.input_domain = self.input_domain.strip().lower()

    def to_dict(self) -> dict:
        """Serialize the full pipeline result to a plain dictionary."""
        return {
            "input_domain": self.input_domain,
            "companies_found": [c.to_dict() for c in self.companies_found],
            "decision_makers": [dm.to_dict() for dm in self.decision_makers],
            "emails_enriched": [dm.to_dict() for dm in self.emails_enriched],
            "emails_sent": [e.to_dict() for e in self.emails_sent],
            "stage_timings": self.stage_timings,
            "total_duration": round(self.total_duration, 3),
            "success": self.success,
        }
