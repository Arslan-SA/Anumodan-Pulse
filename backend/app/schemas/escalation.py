"""
AICTE FlowOps — Escalation Schemas

Request and response models for deadline escalations and supervisory audit records.
"""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict


class EscalationHistoryResponse(BaseModel):
    """Historical record of an escalation event."""
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    rule_name: str
    escalation_level: int
    escalated_to_role: str
    escalated_to_user_id: Optional[uuid.UUID] = None
    escalated_to_name: Optional[str] = None
    reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
