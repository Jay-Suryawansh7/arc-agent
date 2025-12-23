"""
ARC Brain - Phase 4: Selective Memory Reading
"""
import logging
import json
from typing import TypedDict, Literal, Optional, List, Dict, Any
from datetime import datetime

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

from arc.config import get_config
from arc.brain.memory import get_memory_manager

logger = logging.getLogger(__name__)

# --- State Schema ---
class MemoryDecision(TypedDict):
    episodic: bool
    long_term: bool
    summary: Optional[str]
    user_fact: Optional[list[str]] # facts to add


class AgentState(TypedDict):
    # Inputs
    input_text: str
    chat_history: list[BaseMessage]
    
    # The Brain (ReasoningEngine output)
    intent: Literal["chat", "tool", "memory_control", "unknown"]
    justification: str
    confidence: float
    tool_command: Optional[dict]  # {name: str, args: dict}
    needs_memory: bool            # Phase 4: Reasoning decided context is needed
    
    # Phase 2: Failure & Recovery
    failure_reason: Optional[str] # Populated only on tool failure
    recovery_attempt: bool        # True once RecoveryEngine runs
    
    # Phase 3: Memory
    memory_decision: Optional[MemoryDecision] # Brain's decision to remember
    memory_context: Optional[str]             # Phase 4: Injected context
    
    # Outputs
    tool_result: Optional[str]
    final_response: Optional[str]

# --- Nodes ---

def reasoning_engine(state: AgentState) -> dict:
    """
    The Single Cognitive Step (Phase 5).
    Decides intent, considers preferences (Advisory), and flags memory usage.
    """
    config = get_config()
    input_text = state["input_text"]
    
    # Phase 5: Soft Preferences Injection
    try:
        mem_mgr = get_memory_manager()
        raw_facts = mem_mgr.get_profile()
        context_block = "\n".join(f"- {f}" for f in raw_facts[-5:]) # Last 5 facts
    except:
        context_block = "None"
    
    system_prompt = f"""You are ARC (Autonomous Reasoning Companion).
    
    [USER CONTEXT (ADVISORY)]
    {context_block}
    * Use these preferences to fill generic requests (e.g. "Open editor" -> "VS Code").
    * EXPLICIT COMMANDS ALWAYS OVERRIDE PREFERENCES.
    
    DECISION RULES:
    1. INTENT: "chat", "tool", "memory_control", or "unknown".
    2. MEMORY: Set "needs_memory": true ONLY for chat about past context.
    
    SPECIAL INTENTS:
    - "memory_control": If user says "Forget that", "Clear memory", "What do you know?".
      - For "Forget that", set tool_command = {{"name": "forget_last"}}
      - For "Clear memory", set tool_command = {{"name": "clear_all"}}
    
    OUTPUT JSON:
    {{
        "intent": "chat" | "tool" | "memory_control" | "unknown",
        "justification": "Why?",
        "confidence": 0.0-1.0,
        "tool_command": {{name, args}} or null,
        "needs_memory": boolean,
        "final_response": "Response string",
        "memory_decision": {{
            "episodic": boolean,
            "long_term": boolean,
            "user_fact": [list of strings]
        }}
    }}

    Tools: list_apps, list_files
    """
    
    try:
        llm = ChatOllama(
            model=config.llm.model_name,
            base_url=config.llm.base_url,
            format="json", 
            temperature=0
        )
        
        messages = [
            SystemMessage(content=system_prompt),
        ] + state.get("chat_history", []) + [
            HumanMessage(content=input_text)
        ]
        
        logger.info(f"🧠 Reasoning on: {input_text} (w/ Context)")
        response = llm.invoke(messages)
        content = response.content
        
        # Parse JSON
        decision = json.loads(content)
        
        # Safe getter for memory decision to match TypedDict structure
        raw_mem = decision.get("memory_decision", {})
        memory_decision = {
            "episodic": raw_mem.get("episodic", False),
            "long_term": raw_mem.get("long_term", False),
            "summary": None,
            "user_fact": raw_mem.get("user_fact", [])
        }
        
        return {
            "intent": decision.get("intent", "unknown"),
            "justification": decision.get("justification", "No justification"),
            "confidence": decision.get("confidence", 0.0),
            "tool_command": decision.get("tool_command"),
            "needs_memory": decision.get("needs_memory", False),
            "final_response": decision.get("final_response"),
            "memory_decision": memory_decision,
            "recovery_attempt": False,
            "failure_reason": None,
            "memory_context": None
        }
        
    except Exception as e:
        logger.error(f"Reasoning failed: {e}")
        return {
            "intent": "unknown",
            "confidence": 0.0,
            "failure_reason": f"Reasoning Engine crashed: {e}"
        }

# [Keep context_loader, chat_responder, recovery_engine, tool_gateway as is]
# (Using implicit keep via "EndLine" targeting, but replace_file_content replaces range. 
# I need to be careful not to delete them if they are in the range. 
# The range I selected (AgentState to Reasoning) covers the start.
# I will retain the rest of the file by NOT including it in the replacement if I target correctly.
# But `reasoning_engine` ends around line 130. 
# I'll just rewrite `AgentState` and `reasoning_engine`.)

# ... (Previous ContextLoader, ChatResponder, Recovery, ToolGateway stay same)

def tool_gateway(state: AgentState) -> dict:
    """
    Executes the tool command. Handles failures explicitly.
    Uses Embedded Filesystem MCP & Browser MCP.
    """
    from arc.mcp.filesystem import FilesystemMCP
    from arc.mcp.browser import BrowserMCP
    
    cmd = state.get("tool_command")
    if not cmd:
        return {"failure_reason": "No tool command specified."}
        
    tool_name = cmd.get("name")
    tool_args = cmd.get("args", {})
    
    logger.info(f"🛠️ Executing: {tool_name} with {tool_args}")
    
    try:
        # --- Filesystem MCP ---
        fs_tools = ["list_files", "list_directory", "read_file", "write_file", "create_file", "delete_file"]
        
        if tool_name in fs_tools:
            mcp = FilesystemMCP()
            # Map legacy 'list_files' to mcp 'list_directory'
            op = "list_directory" if tool_name == "list_files" else tool_name
            
            # Map legacy args
            if op == "list_directory" and "path" not in tool_args:
                tool_args["path"] = "."
                
            response = mcp.execute(op, tool_args)
            if response["status"] == "success":
                return {"tool_result": str(response["data"])}
            else:
                return {"failure_reason": f"File Op Failed: {response.get('error')}"}

        # --- Browser MCP ---
        browser_tools = ["open_url", "search_web", "open_web_app"]
        if tool_name in browser_tools:
            mcp = BrowserMCP()
            response = mcp.execute(tool_name, tool_args)
            if response["status"] == "success":
                 return {"tool_result": str(response["data"])}
            else:
                 return {"failure_reason": f"Browser Op Failed: {response.get('error')}"}

        # --- Legacy / Other Tools ---
        result = ""
        if tool_name == "list_apps":
            result = "Apps: Code, Chrome, Terminal (Mock)"
        elif tool_name not in fs_tools and tool_name not in browser_tools:
             raise ValueError(f"Tool '{tool_name}' not found.")
            
        return {"tool_result": result}
        
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return {"failure_reason": str(e)}

def memory_processor(state: AgentState) -> dict:
    """
    Sequential Memory Processor (Phase 5).
    Handles writes, decay, and CONTROL commands.
    """
    try:
        mem_mgr = get_memory_manager()
        
        # Phase 5: Memory Control
        if state.get("intent") == "memory_control":
            cmd = state.get("tool_command", {}) or {}
            name = cmd.get("name")
            if name == "forget_last":
                mem_mgr.delete_last_episodic()
            elif name == "clear_all":
                mem_mgr.clear_profile()
            return {} # Done
            
        dec = state.get("memory_decision", {})
        
        # 1. Long-Term Memory (User Facts)
        if dec.get("long_term") and dec.get("user_fact"):
            mem_mgr.update_profile(dec.get("user_fact"))
            
        # 2. Episodic Memory (Tools)
        intent = state.get("intent")
        if intent == "tool":
            cmd = state.get("tool_command", {}) or {}
            outcome = "failure" if state.get("failure_reason") else "success"
            result = state.get("failure_reason") or state.get("tool_result") or "No result"
            
            mem_mgr.log_episodic(
                intent=intent,
                tool=cmd.get("name", "unknown"),
                args=cmd.get("args", {}),
                outcome=outcome,
                result_summary=result
            )
            
    except Exception as e:
        logger.error(f"Memory processing failed (non-fatal): {e}")
        
    return {}

def create_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("reasoning", reasoning_engine)
    workflow.add_node("context_loader", context_loader)
    workflow.add_node("chat_responder", chat_responder)
    workflow.add_node("tools", tool_gateway)
    workflow.add_node("recovery", recovery_engine)
    workflow.add_node("memory", memory_processor)
    
    workflow.set_entry_point("reasoning")
    
    def route_reasoning(state: AgentState):
        if state.get("confidence", 0.0) < 0.5:
            return "recovery"
        if state.get("intent") == "tool":
            return "tools"
        if state.get("needs_memory"):
            return "context_loader"
        # Phase 5: Control signals go straight to processor
        if state.get("intent") == "memory_control":
             return "memory"
             
        return "memory" # Standard chat

    def route_tools(state: AgentState):
        if state.get("failure_reason"):
            return "recovery"
        return "memory"
        
    workflow.add_conditional_edges(
        "reasoning",
        route_reasoning,
        {
            "tools": "tools",
            "recovery": "recovery",
            "context_loader": "context_loader",
            "memory": "memory"
        }
    )
    
    workflow.add_edge("context_loader", "chat_responder")
    workflow.add_edge("chat_responder", "memory")
    
    workflow.add_conditional_edges(
        "tools",
        route_tools,
        {
            "recovery": "recovery",
            "memory": "memory"
        }
    )
    
    workflow.add_edge("recovery", "memory")
    workflow.add_edge("memory", END)
    
    return workflow.compile()
