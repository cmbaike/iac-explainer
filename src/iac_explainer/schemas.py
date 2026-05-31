from enum import Enum
from pydantic import BaseModel, Field

class Severity(str, Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class ResourceExplanation(BaseModel):
    resource_type: str          # e.g. "aws_s3_bucket"
    name: str                   # the Terraform name
    purpose: str = Field(..., description="One sentence, plain English")

class CostEstimate(BaseModel):
    low_usd_monthly: float
    high_usd_monthly: float
    confidence: Severity        # reuse: info=very rough ... high=fairly confident
    caveats: list[str]          # always populated; cost is never exact

class SecurityFinding(BaseModel):
    severity: Severity
    resource: str
    issue: str
    recommendation: str

class Analysis(BaseModel):
    summary: str = Field(..., description="One paragraph, plain English, no jargon")
    resources: list[ResourceExplanation]
    cost: CostEstimate
    security_findings: list[SecurityFinding]
    overall_risk: Severity