from typing import Literal
from src.schemas.state import IncidentState

def supervisor_node(state: IncidentState) -> Literal["triage", "telemetry", "codebase", "resolution", "__end__"]:
    """
    Supervisor Agent (Router): Decides which specialist agent should handle the next step based on the incident state.
    """
    print(f"--- SUPERVISOR AGENT --- Current State: {state['current_agent']}")
    
    current = state.get("current_agent", "start")
    
    # 1. New Incident -> Triage
    if current == "start":
        return "triage"
        
    # 2. After Triage -> Get Telemetry/Logs
    if current == "triage":
        return "telemetry"
        
    # 3. After Telemetry -> If Code/Data issue suspected -> Codebase/RCA
    if current == "telemetry":
        # In a real app, the supervisor LLM would read the telemetry anomalies and decide.
        # Here we mock the decision logic.
        if len(state.get("identified_anomalies", [])) > 0:
            return "codebase"
        else:
            return "resolution" # Shortcut to resolution if it's a known infra blip without code traces
            
    # 4. After RCA -> Resolution
    if current == "codebase":
        return "resolution"
        
    # 5. After Resolution -> End Workflow
    if current == "resolution":
        return "__end__"
        
    return "__end__"
