from typing import TypedDict, List, Optional, Any, Dict

class IncidentState(TypedDict):
    """
    State representing the lifecycle of a production incident through the LangGraph agents.
    """
    # Core incident details
    incident_id: str
    scenario_id: Optional[str] # Used in file mode to mock different issues (e.g. 'scenario1', 'scenario2')
    source: str # e.g., "jira", "splunk_alert", "email"
    raw_description: str
    severity: Optional[str] # P1, P2, P3
    
    # Enrichment from Triage
    similar_historical_tickets: List[Dict[str, Any]]
    relevant_runbooks: List[Dict[str, Any]]
    
    # Telemetry data
    splunk_logs: List[Dict[str, Any]]
    identified_anomalies: List[str]
    
    # Codebase & RCA
    suspected_components: List[str]
    code_snippets: List[Dict[str, Any]]
    root_cause_analysis: str
    issue_type: Optional[str] # "CODE", "DATA", "INFRA"
    
    # Resolution
    suggested_resolution: str
    workaround: Optional[str]
    recommended_runbook: Optional[str]
    confidence_score: float
    requires_human_approval: bool
    human_approved: Optional[bool]
    jira_ticket_key: Optional[str]  # Extracted from email or created by Resolution Agent
    jira_context: Optional[Dict[str, Any]] # Full Jira ticket details
    
    # Workflow control
    current_agent: str
    errors: List[str]

