from pydantic import BaseModel
from typing import Optional

class IncidentRequest(BaseModel):
    source: str
    raw_description: Optional[str] = ""
    scenario_id: Optional[str] = "scenario1_payment_bug"
