import os
import json
from src.schemas.state import IncidentState

async def telemetry_node(state: IncidentState) -> IncidentState:
    """
    Telemetry & Log Analysis Agent: Uses Splunk MCP to pull relevant logs
    based on the timestamp and components.
    """
    print(f"--- TELEMETRY AGENT --- Pulling Logs for: {state['incident_id']}")
    
    state["current_agent"] = "telemetry"
    ingestion_mode = os.getenv("INGESTION_MODE", "local").lower()
    
    if ingestion_mode == "local":
        print("Telemetry Agent: Reading logs from local folder (INGESTION_MODE=local).")
        try:
            scenario_id = state.get("scenario_id", "scenario1_payment_bug")
            base_scenario = scenario_id.split('_')[0]
            local_logs_dir = os.getenv("LOCAL_LOGS_DIR", "data/logs")
            log_path = os.path.join(local_logs_dir, f"{base_scenario}_logs.json")
            
            with open(log_path, "r") as f:
                state["splunk_logs"] = json.load(f)
        except Exception as e:
            print(f"Telemetry File Read Error: {e}")
            state["splunk_logs"] = []
    else:
        print("Telemetry Agent: Querying via Splunk MCP (INGESTION_MODE=mcp).")
        from src.mcp.splunk import get_splunk_client
        client = get_splunk_client()
        try:
            await client.connect()
            # Simple keyword match for the mock server
            query = f"index=main {state.get('scenario_id', '')}"
            result = await client.execute_tool("splunk_search", {"query": query})
            
            # Extract JSON from FastMCP CallToolResult
            if result and hasattr(result, 'content') and len(result.content) > 0:
                text_result = result.content[0].text
                state["splunk_logs"] = json.loads(text_result)
            else:
                state["splunk_logs"] = [{"message": "No specific errors found by MCP."}]
        except Exception as e:
            print(f"Splunk MCP Error: {e}")
            state["errors"].append(f"Splunk MCP Error: {e}")
            state["splunk_logs"] = []
        finally:
            await client.disconnect()
    
    # Mock Anomaly Detection
    state["identified_anomalies"] = ["Exception spike in PaymentService"]
    state["suspected_components"] = ["PaymentGateway", "PaymentService"]
    
    return state
