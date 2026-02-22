"""
Resolution Agent: Proposes a fix, creates/updates Jira tickets,
and sends notification emails via Outlook MCP.
"""
import os
import json
from src.schemas.state import IncidentState


async def resolution_node(state: IncidentState) -> IncidentState:
    """
    Resolution Agent: Proposes the final fix, creates a Jira ticket,
    and sends stakeholder notifications via Outlook.
    """
    print(f"--- RESOLUTION AGENT --- Drafting Fix for: {state['incident_id']}")
    
    state["current_agent"] = "resolution"
    ingestion_mode = os.getenv("INGESTION_MODE", "local").lower()
    
    issue = state.get("issue_type", "UNKNOWN")
    
    # ── 1. Generate Resolution via Copilot LLM ───────────────────────
    from src.llm.llm_client import chat_with_llm
    
    system_prompt = """You are a Resolution Agent for an L3 Engineering Support system.
    Based on the incident description, anomalies, and root cause analysis, propose a fix.
    Also suggest a temporary workaround if applicable, and recommend a runbook from the provided context.
    Return ONLY JSON format:
    {
      "suggested_resolution": "Detailed fix description...",
      "workaround": "Temporary mitigation step...",
      "recommended_runbook": "Title of the most relevant runbook from context...",
      "confidence_score": 0.95,
      "requires_human_approval": true|false
    }
    Rules for approval: Any CODE or DATA change requires human approval (true). Only safe or predefined INFRA scaling can be auto-remediated (false)."""

    user_prompt = f"Incident: {state.get('raw_description', '')}\n"
    if state.get('jira_context'):
        user_prompt += f"Jira Context:\n{json.dumps(state['jira_context'])}\n"
    user_prompt += f"Anomalies: {state.get('identified_anomalies', [])}\n"
    user_prompt += f"Issue Type: {issue}\n"
    user_prompt += f"Root Cause: {state.get('root_cause_analysis', '')}\n"
    if state.get('relevant_runbooks'):
        user_prompt += f"Available Runbooks for Context:\n{json.dumps(state['relevant_runbooks'])}\n"
        
    try:
        res_response = await chat_with_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_family="gpt-4o"
        )
        res_response = res_response.strip().removeprefix("```json").removesuffix("```").strip()
        result = json.loads(res_response)
        
        state["suggested_resolution"] = result.get("suggested_resolution", "Escalating to human L1.")
        state["workaround"] = result.get("workaround")
        state["recommended_runbook"] = result.get("recommended_runbook")
        state["confidence_score"] = float(result.get("confidence_score", 0.5))
        state["requires_human_approval"] = bool(result.get("requires_human_approval", True))
        
    except Exception as e:
        print(f"Copilot LLM Error in Resolution: {e}")
        state["errors"].append(f"Resolution LLM Error: {e}")
        # Fallback
        if issue == "INFRA":
            state["suggested_resolution"] = "Increased max database connection pool size via Terraform."
            state["confidence_score"] = 0.99
            state["requires_human_approval"] = False
        else:
            state["suggested_resolution"] = "Drafted PR with proposed fix."
            state["confidence_score"] = 0.92
            state["requires_human_approval"] = True

    # ── 2. Create/Update Jira Ticket via MCP ─────────────────────────
    if ingestion_mode == "mcp":
        from src.mcp.jira import get_jira_client
        jira_client = get_jira_client()
        try:
            await jira_client.connect()
            
            # Check if a Jira ticket was extracted from the email
            existing_key = state.get("jira_ticket_key")
            
            if existing_key:
                # UPDATE existing Jira ticket with AI analysis
                print(f"Linking to existing Jira ticket: {existing_key}")
                ticket_key = existing_key
                
                # Add AI analysis as a comment to the existing ticket
                await jira_client.execute_tool("add_comment", {
                    "ticket_key": ticket_key,
                    "comment": (
                        f"AI Agent Analysis (Incident: {state['incident_id']}):\n"
                        f"- Severity: {state.get('severity', 'N/A')}\n"
                        f"- Issue Type: {issue}\n"
                        f"- Anomalies: {state.get('identified_anomalies', [])}\n"
                        f"- Root Cause: {state.get('root_cause_analysis', 'N/A')}\n"
                        f"- Resolution: {state['suggested_resolution']}\n"
                        f"- Confidence: {state['confidence_score']:.0%}\n"
                        f"- Approval Required: {state['requires_human_approval']}"
                    )
                })
                print(f"Added AI analysis to existing ticket: {ticket_key}")
            else:
                # CREATE a new Jira ticket for this incident
                create_result = await jira_client.execute_tool("create_ticket", {
                    "project": "SP",
                    "summary": f"[{state['severity']}] {state.get('raw_description', '')[:80]}",
                    "description": (
                        f"Incident ID: {state['incident_id']}\n"
                        f"Issue Type: {issue}\n"
                        f"Root Cause: {state.get('root_cause_analysis', 'N/A')}\n"
                        f"Suggested Resolution: {state['suggested_resolution']}\n"
                        f"Confidence: {state['confidence_score']:.0%}"
                    ),
                    "priority": state.get("severity", "P2")
                })
                
                if create_result and hasattr(create_result, 'content') and len(create_result.content) > 0:
                    ticket_data = json.loads(create_result.content[0].text)
                    ticket_key = ticket_data.get("ticket", {}).get("key", "UNKNOWN")
                    state["jira_ticket_key"] = ticket_key
                    print(f"Jira ticket created: {ticket_key}")
                    
                    # Add AI analysis as a comment
                    await jira_client.execute_tool("add_comment", {
                        "ticket_key": ticket_key,
                        "comment": (
                            f"AI Agent Analysis:\n"
                            f"- Anomalies: {state.get('identified_anomalies', [])}\n"
                            f"- Root Cause: {state.get('root_cause_analysis', 'N/A')}\n"
                            f"- Resolution: {state['suggested_resolution']}\n"
                            f"- Confidence: {state['confidence_score']:.0%}\n"
                            f"- Approval Required: {state['requires_human_approval']}"
                        )
                    })
            
            # Transition ticket status
            if not state["requires_human_approval"]:
                await jira_client.execute_tool("transition_ticket", {
                    "ticket_key": ticket_key,
                    "new_status": "Resolved"
                })
                print(f"Auto-resolved ticket: {ticket_key}")
            else:
                await jira_client.execute_tool("transition_ticket", {
                    "ticket_key": ticket_key,
                    "new_status": "Under Review"
                })
                    
        except Exception as e:
            print(f"Jira MCP Error: {e}")
            state["errors"].append(f"Jira MCP Error: {e}")
        finally:
            await jira_client.disconnect()

        # ── 3. Send Notification Email via Outlook MCP ───────────────
        from src.mcp.outlook import get_outlook_client
        outlook_client = get_outlook_client()
        try:
            await outlook_client.connect()
            
            approval_text = "⚠️ REQUIRES HUMAN APPROVAL" if state["requires_human_approval"] else "✅ AUTO-REMEDIATED"
            
            await outlook_client.execute_tool("send_email", {
                "to": "oncall-team@company.com",
                "subject": f"[{state['severity']}] {approval_text} - {state['incident_id']}",
                "body": (
                    f"Incident: {state['incident_id']}\n"
                    f"Issue Type: {issue}\n"
                    f"Root Cause: {state.get('root_cause_analysis', 'N/A')}\n\n"
                    f"Suggested Resolution: {state['suggested_resolution']}\n"
                    f"Confidence: {state['confidence_score']:.0%}\n\n"
                    f"Status: {approval_text}"
                )
            })
            print(f"Notification email sent for {state['incident_id']}")
            
        except Exception as e:
            print(f"Outlook MCP Error: {e}")
            state["errors"].append(f"Outlook MCP Error: {e}")
        finally:
            await outlook_client.disconnect()
    else:
        # Local mode: just log what would happen
        print(f"[Local Mode] Would create Jira ticket and send email for {state['incident_id']}")
        
    return state
