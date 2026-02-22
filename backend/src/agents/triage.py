import os
import re
from src.schemas.state import IncidentState

# Regex pattern for Jira ticket keys (e.g., SP-301, PROJ-123, INCIDENT-4567)
JIRA_TICKET_PATTERN = re.compile(r'\b([A-Z][A-Z0-9]+-\d+)\b')

async def triage_node(state: IncidentState) -> IncidentState:
    """
    Triage Agent: Analyzes the raw incident description, classifies severity,
    and fetches historical context via RAG.
    """
    print(f"--- TRIAGE AGENT --- Analyzing Incident: {state['incident_id']}")
    
    ingestion_mode = os.getenv("INGESTION_MODE", "local").lower()
    
    images = []
    
    # Optional: Override input description with local file if in LOCAL mode
    if ingestion_mode == "local":
        print("Triage Agent: Reading incident description from local folder (INGESTION_MODE=local).")
        try:
            from src.mcp.email_parser import parse_email
            import glob
            
            scenario_id = state.get("scenario_id", "scenario1_payment_bug")
            local_email_dir = os.getenv("LOCAL_EMAIL_DIR", "data/emails")
            
            # Find the file regardless of extension (.eml, .msg, .txt)
            matching_files = glob.glob(os.path.join(local_email_dir, f"{scenario_id}.*"))
            
            if matching_files:
                email_file = matching_files[0]
                print(f"Parsing email file: {email_file}")
                email_data = parse_email(email_file)
                state['raw_description'] = f"Subject: {email_data['subject']}\n\n{email_data['body']}"
                images = email_data['images']
            else:
                print(f"Warning: No email file found for scenario '{scenario_id}' in {local_email_dir}")
        except Exception as e:
            print(f"Triage File Read Error: {e}")
    else:
        # MCP mode: Use Outlook MCP to search and fetch emails
        print("Triage Agent: Fetching incident email via Outlook MCP (INGESTION_MODE=mcp).")
        from src.mcp.outlook import get_outlook_client
        import json
        client = get_outlook_client()
        try:
            await client.connect()
            # Search for relevant incident emails
            search_result = await client.execute_tool("search_emails", {
                "query": state.get("raw_description", "error"),
                "max_results": 1
            })
            if search_result and hasattr(search_result, 'content') and len(search_result.content) > 0:
                emails = json.loads(search_result.content[0].text)
                if emails:
                    # Fetch full email content
                    email_id = emails[0].get("id", "")
                    full_email = await client.execute_tool("get_email", {"email_id": email_id})
                    if full_email and hasattr(full_email, 'content') and len(full_email.content) > 0:
                        email_data = json.loads(full_email.content[0].text)
                        state['raw_description'] = f"Subject: {email_data.get('subject', '')}\n\n{email_data.get('body', '')}"
                        print(f"Fetched email: {email_data.get('subject', 'N/A')}")
        except Exception as e:
            print(f"Outlook MCP Error: {e}")
            state["errors"].append(f"Outlook MCP Error: {e}")
        finally:
            await client.disconnect()

    # ── Extract Jira ticket key and fetch details ──────────────────
    desc = state.get('raw_description', '')
    jira_matches = JIRA_TICKET_PATTERN.findall(desc)
    state['jira_ticket_key'] = None
    state['jira_context'] = None
    
    if jira_matches:
        jira_key = jira_matches[0]
        state['jira_ticket_key'] = jira_key
        print(f"Triage Agent: Linked to existing Jira ticket: {jira_key}")
        
        # Fetch full Jira context via MCP
        if ingestion_mode == "mcp":
            from src.mcp.jira import get_jira_client
            import json
            jira_client = get_jira_client()
            try:
                await jira_client.connect()
                ticket_res = await jira_client.execute_tool("get_issue", {"issue_key": jira_key})
                if ticket_res and hasattr(ticket_res, 'content') and len(ticket_res.content) > 0:
                    state['jira_context'] = json.loads(ticket_res.content[0].text)
                    print(f"Fetched full Jira context for {jira_key}")
            except Exception as e:
                print(f"Jira MCP Error: {e}")
                state["errors"].append(f"Jira MCP Error: {e}")
            finally:
                await jira_client.disconnect()
            
    # Initialize LLM via VSCode Copilot Proxy
    from src.llm.llm_client import chat_with_llm
    
    system_prompt = """You are a Triage Agent for an L1/L2 Production Support system.
    Your job is to analyze the raw incident description and determine the severity (P1, P2, P3).
    Return ONLY the severity level: P1, P2, or P3."""
    
    user_prompt = f"Incident Description:\n{state.get('raw_description', '')}"
    if state.get('jira_context'):
        import json
        user_prompt += f"\n\nJira Context:\n{json.dumps(state['jira_context'])}"
    
    # Execute LLM
    try:
        severity_response = await chat_with_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_family="gpt-4o-mini" # Fast classification
        )
        severity = severity_response.strip()
        # Fallback if the LLM gets conversational
        if "P1" in severity: severity = "P1"
        elif "P2" in severity: severity = "P2"
        elif "P3" in severity: severity = "P3"
        else: severity = "P2"
    except Exception as e:
        print(f"Copilot LLM Error in Triage: {e}")
        severity = "P1" if "down" in state.get('raw_description', '').lower() else "P2"
        state["errors"].append(f"Triage LLM Error: {str(e)}")

    # Update state
    state["severity"] = severity
    state["current_agent"] = "triage"
    
    # Use RAG service to find similar historical tickets and runbooks
    from src.mcp.rag import rag_service
    try:
        desc = state.get('raw_description', '')
        state["similar_historical_tickets"] = await rag_service.search_similar_tickets(desc)
        state["relevant_runbooks"] = await rag_service.retrieve_runbooks(desc)
    except Exception as e:
        print(f"RAG Service Error: {e}")
        state["similar_historical_tickets"] = []
        state["relevant_runbooks"] = []
    
    return state
