from langgraph.graph import StateGraph, END
from src.schemas.state import IncidentState

from src.agents.supervisor import supervisor_node
from src.agents.triage import triage_node
from src.agents.telemetry import telemetry_node
from src.agents.codebase import codebase_node
from src.agents.resolution import resolution_node

def build_incident_graph() -> StateGraph:
    """
    Builds and compiles the Multi-Agent Supervisor workflow using LangGraph.
    """
    print("Building Agentic Orchestrator Graph...")
    
    # 1. Define the State Graph with our Schema
    workflow = StateGraph(IncidentState)
    
    # 2. Add Nodes (Agents)
    workflow.add_node("triage", triage_node)
    workflow.add_node("telemetry", telemetry_node)
    workflow.add_node("codebase", codebase_node)
    workflow.add_node("resolution", resolution_node)
    
    # 3. Add Edges (Routing)
    # The supervisor dictates the path based on conditional edges from each node back to the supervisor,
    # or in a simpler sequential flow, we just connect them directly based on the supervisor's output.
    
    # Example sequential flow defined by the supervisor routing logic above:
    workflow.set_entry_point("triage")
    workflow.add_edge("triage", "telemetry")
    workflow.add_conditional_edges(
        "telemetry",
        supervisor_node, # The router function
        {
            "codebase": "codebase",
            "resolution": "resolution"
        }
    )
    workflow.add_edge("codebase", "resolution")
    workflow.add_edge("resolution", END)
    
    # 4. Compile the graph
    app = workflow.compile()
    return app
    
# Export a pre-compiled instance for the API
incident_orchestrator = build_incident_graph()
