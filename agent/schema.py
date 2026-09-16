"""Pydantic v2 models for one researched app (PROJECT_BRIEF.md section 4).

Design rule: only id/name/category are required. Every LLM-produced field has an
honest "unknown"-shaped default, so a partial model response still parses, gets
flagged for a human, and never crashes a 100-app run.

Two deliberate deviations from the brief, recorded in docs/DECISIONS.md:
  D12  ApiBreadth gains `unknown` -- `none` asserts "this app has no API", which
       is a different claim from "we did not determine breadth".
  D13  Missing evidence is a computed flag, not a validation error. Raising here
       would force a repair loop whose only escape is inventing a URL, which
       CLAUDE.md forbids. Missing evidence is a finding, not a parse failure.
"""

from __future__ import annotations

import html
from enum import Enum
from typing import Annotated, Any, Literal, Optional

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


# --------------------------------------------------------------------------
# Enums -- the LLM must choose from these, no free text.
# --------------------------------------------------------------------------

class AuthMethod(str, Enum):
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC = "basic"
    BEARER_TOKEN = "bearer_token"
    JWT = "jwt"
    HMAC_SIGNATURE = "hmac_signature"
    OTHER = "other"
    NONE = "none"


class Access(str, Enum):
    SELF_SERVE_FREE = "self_serve_free"
    SELF_SERVE_TRIAL = "self_serve_trial"
    PAID_PLAN = "paid_plan"
    ADMIN_APPROVAL = "admin_approval"
    PARTNER_GATED = "partner_gated"
    NO_PUBLIC_API = "no_public_api"


class ApiType(str, Enum):
    REST = "rest"
    GRAPHQL = "graphql"
    WEBSOCKET = "websocket"
    SOAP = "soap"
    SDK_ONLY = "sdk_only"
    CLI_OR_LIBRARY = "cli_or_library"
    NONE = "none"


class ApiBreadth(str, Enum):
    BROAD = "broad"
    MODERATE = "moderate"
    NARROW = "narrow"
    NONE = "none"
    UNKNOWN = "unknown"  # added -- see D12


class YesNoUnknown(str, Enum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class ExistingMcp(str, Enum):
    OFFICIAL = "official"
    COMMUNITY = "community"
    NONE_FOUND = "none_found"


class Verdict(str, Enum):
    READY = "ready"
    READY_WITH_FRICTION = "ready_with_friction"
    NEEDS_OUTREACH = "needs_outreach"
    NOT_VIABLE = "not_viable"


class Blocker(str, Enum):
    NONE = "none"
    PAID_PLAN = "paid_plan"
    PARTNER_PROGRAM = "partner_program"
    APP_REVIEW = "app_review"
    ADMIN_APPROVAL = "admin_approval"
    NO_PUBLIC_API = "no_public_api"
    SPARSE_DOCS = "sparse_docs"
    LOCAL_ONLY_TOOL = "local_only_tool"
    OTHER = "other"


class PassName(str, Enum):
    V1 = "v1"
    V2 = "v2"


# Evidence may be attached to any of these; the first five are *required*
# (brief section 4) and drive the evidence-support metric on the page.
EvidenceField = Literal[
    "auth_methods", "access", "api_type", "existing_mcp", "verdict",
    "webhooks", "api_breadth", "openapi_spec", "other",
]

EVIDENCE_REQUIRED_FIELDS: tuple[str, ...] = (
    "auth_methods", "access", "api_type", "existing_mcp", "verdict",
)


# --------------------------------------------------------------------------
# Word-limit validators (shared, so the rule lives in one place)
# --------------------------------------------------------------------------

def _max_words(limit: int):
    """Collapse whitespace, then reject if over `limit` words.

    Returning the cleaned string means this doubles as a normaliser, which
    matters for Loop A quote matching against fetched page text.
    """
    def check(value: str) -> str:
        # Model quotes are copied from rendered pages, so HTML entities ride
        # along ("&amp;"). Unescape here: this text is rendered as text later.
        cleaned = " ".join(html.unescape(value).split())
        count = len(cleaned.split())
        if count > limit:
            raise ValueError(f"must be <= {limit} words, got {count}")
        return cleaned
    return check


OneLiner = Annotated[str, AfterValidator(_max_words(15))]
Quote = Annotated[str, AfterValidator(_max_words(40))]


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------

class Evidence(BaseModel):
    """A verbatim quote from a page that was actually fetched."""

    model_config = ConfigDict(extra="ignore")

    field: EvidenceField
    url: str
    quote: Quote = ""


class AppRecord(BaseModel):
    """One researched app.

    Invariant after research.py runs: `verdict` is never None on disk, because
    rules.apply_rules() always fills it. It is Optional on the model so that a
    model response that omits it still parses (None = "the LLM did not answer").

    `verification` is filled by verify.py (P5); shape:
        {"<field>": {"status": "supported|unsupported|unreachable",
                     "method": "httpx|webfetch|playwright",
                     "checked_at": "<iso8601>"}}
    Left as a loose dict at P1 because verify.py does not exist yet.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    # From apps.csv -- never LLM-generated.
    id: int
    name: str
    category: str

    # Researched fields -- all optional, all default to an honest "unknown".
    one_liner: OneLiner = ""
    docs_url: Optional[str] = None
    auth_methods: list[AuthMethod] = Field(default_factory=list)
    primary_auth: Optional[AuthMethod] = None
    access: Optional[Access] = None
    access_notes: str = ""
    api_type: list[ApiType] = Field(default_factory=list)
    api_breadth: ApiBreadth = ApiBreadth.UNKNOWN
    openapi_spec: YesNoUnknown = YesNoUnknown.UNKNOWN
    existing_mcp: ExistingMcp = ExistingMcp.NONE_FOUND
    mcp_url: Optional[str] = None
    webhooks: YesNoUnknown = YesNoUnknown.UNKNOWN
    sandbox_or_test_mode: YesNoUnknown = YesNoUnknown.UNKNOWN
    rate_limits_documented: YesNoUnknown = YesNoUnknown.UNKNOWN
    on_composio: YesNoUnknown = YesNoUnknown.UNKNOWN  # from composio_check, not the LLM
    verdict: Optional[Verdict] = None
    blocker: Optional[Blocker] = None
    blocker_notes: Optional[str] = None
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    needs_human: bool = False
    needs_human_reason: Optional[str] = None
    pass_: PassName = Field(default=PassName.V1, alias="pass")
    verification: dict[str, Any] = Field(default_factory=dict)

    # Derived by us, not by the LLM.
    missing_evidence_for: list[str] = Field(default_factory=list)
    rule_id: Optional[str] = None  # which rule set the verdict (R1..R6)

    @model_validator(mode="after")
    def _compute_evidence_gaps(self) -> "AppRecord":
        """Compute, never raise -- see D13."""
        covered = {e.field for e in self.evidence}
        self.missing_evidence_for = [
            f for f in EVIDENCE_REQUIRED_FIELDS if f not in covered
        ]
        if self.missing_evidence_for and not self.needs_human:
            self.needs_human = True
            self.needs_human_reason = "missing_evidence: " + ",".join(
                self.missing_evidence_for
            )
        return self


def dump_record(record: AppRecord) -> dict[str, Any]:
    """Serialise with the brief's field names (pass_ -> pass) and JSON-safe enums."""
    return record.model_dump(by_alias=True, mode="json")
