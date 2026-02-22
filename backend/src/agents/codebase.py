import os
from src.schemas.state import IncidentState

async def codebase_node(state: IncidentState) -> IncidentState:
    """
    Codebase & RCA Agent: Uses GitHub/GitLab MCP to read source files
    matching the anomalies found by Telemetry.
    """
    print(f"--- CODEBASE & RCA AGENT --- Inspecting: {state['suspected_components']}")
    
    state["current_agent"] = "codebase"
    ingestion_mode = os.getenv("INGESTION_MODE", "local").lower()
    
    if ingestion_mode == "local":
        print("Codebase Agent: Reading source from local folder (INGESTION_MODE=local).")
        try:
            scenario_id = state.get("scenario_id", "scenario1_payment_bug")
            local_code_dir = os.getenv("LOCAL_CODE_DIR", "data/codebase")
            
            if "scenario1" in scenario_id:
                filepath = os.path.join(local_code_dir, "PaymentService.java")
                filename = "PaymentService.java"
            else:
                filepath = os.path.join(local_code_dir, "db_config.tf")
                filename = "db_config.tf"
                
            with open(filepath, "r") as f:
                content = f.read()
            state["code_snippets"] = [{"file": filename, "content": content}]
        except Exception as e:
            print(f"Codebase File Read Error: {e}")
            state["code_snippets"] = []
    else:
        print("Codebase Agent: Reading source via GitHub MCP (INGESTION_MODE=mcp).")
        from src.mcp.github import get_github_client
        client = get_github_client()
        try:
            await client.connect()
            
            # Simple simulation of deriving the target file from the scenario
            scenario_id = state.get("scenario_id", "scenario1_payment_bug")
            github_repo = os.getenv("GITHUB_REPO", "owner/repo")
            
            if "scenario1" in scenario_id:
                target_file = "src/main/java/com/company/PaymentService.java"
            else:
                target_file = "infrastructure/db_config.tf"
                
            # Calling the mcp server tool
            result = await client.execute_tool("get_file_contents", {
                "owner": github_repo.split('/')[0] if '/' in github_repo else "owner",
                "repo": github_repo.split('/')[1] if '/' in github_repo else "repo",
                "path": target_file
            })
            
            if result and hasattr(result, 'content') and len(result.content) > 0:
                content = result.content[0].text
                state["code_snippets"] = [{"file": target_file, "content": content}]
            else:
                state["code_snippets"] = []
                
        except Exception as e:
            print(f"GitHub MCP Error: {e}")
            state["errors"].append(f"GitHub MCP Error: {e}")
            state["code_snippets"] = []
        finally:
            await client.disconnect()
    
    # ── Generate RCA via Copilot LLM ─────────────────────────────────
    from src.llm.llm_client import chat_with_llm
    import json
    
    system_prompt = """You are a Codebase & RCA Agent for an L3 Engineering Support system.
    Your job is to analyze the incident description, telemetry logs, and codebase snippets to determine the root cause.
    Determine the issue_type (CODE or INFRA) and provide a concise root_cause_analysis.
    Return ONLY JSON format: {"issue_type": "CODE|INFRA", "root_cause_analysis": "..."}"""
    
    user_prompt = f"Incident Description:\n{state.get('raw_description', '')}\n\n"
    if state.get('splunk_logs'):
        user_prompt += f"Splunk Logs:\n{json.dumps(state['splunk_logs'])}\n\n"
    if state.get('code_snippets'):
        user_prompt += f"Code Snippets:\n{json.dumps(state['code_snippets'])}\n\n"
        
    try:
        rca_response = await chat_with_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_family="gpt-4o" # Complex reasoning
        )
        # Parse JSON
        rca_response = rca_response.strip().removeprefix("```json").removesuffix("```").strip()
        result = json.loads(rca_response)
        state["issue_type"] = result.get("issue_type", "CODE")
        state["root_cause_analysis"] = result.get("root_cause_analysis", "Unable to determine root cause.")
    except Exception as e:
        print(f"Copilot LLM Error in Codebase: {e}")
        state["errors"].append(f"Codebase LLM Error: {e}")
        # Fallback
        if "down" in state["raw_description"].lower():
            state["issue_type"] = "INFRA"
            state["root_cause_analysis"] = "Database connection pool exhausted due to spike in traffic."
        else:
            state["issue_type"] = "CODE"
            state["root_cause_analysis"] = "NullPointerException when fetching user balance."
            
    return state
