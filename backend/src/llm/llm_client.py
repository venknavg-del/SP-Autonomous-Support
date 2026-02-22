import os
import aiohttp
from typing import List, Dict, Any, Optional

COPILOT_PROXY_URL = os.getenv("COPILOT_PROXY_URL", "http://127.0.0.1:9100/v1/chat")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "copilot").lower()

async def chat_with_llm(
    system_prompt: str, 
    user_prompt: str, 
    model_family: str = "gpt-4o"
) -> str:
    """
    Sends a chat request to the configured LLM provider.
    Supported providers: copilot (via VSCode extension), anthropic, openai. 
    """
    if LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import SystemMessage, HumanMessage
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or api_key == "mock_key":
            raise ValueError("Valid ANTHROPIC_API_KEY must be set in .env when LLM_PROVIDER is 'anthropic'")
            
        mapping = {"gpt-4o-mini": "claude-3-haiku-20240307", "gpt-4o": "claude-3-5-sonnet-20240620"}
        model = mapping.get(model_family, "claude-3-5-sonnet-20240620")
        
        llm = ChatAnthropic(
            model=model,
            temperature=0.1,
            anthropic_api_key=api_key
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await llm.ainvoke(messages)
        return response.content

    elif LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Valid OPENAI_API_KEY must be set in .env when LLM_PROVIDER is 'openai'")
            
        llm = ChatOpenAI(
            model=model_family,
            temperature=0.1,
            openai_api_key=api_key
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await llm.ainvoke(messages)
        return response.content

    # Default to Copilot Proxy via VSCode Extension
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model_family": model_family
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(COPILOT_PROXY_URL, json=payload, timeout=120.0) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"LLM Proxy error ({response.status}): {error_text}")
                
                data = await response.json()
                return data.get("content", "")
    except aiohttp.ClientError as e:
        print(f"[Copilot Client] Connection error: {e}. Is the VSCode extension running?")
        raise RuntimeError(f"Failed to connect to LLM Proxy at {COPILOT_PROXY_URL}") from e
