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
    intent: Literal["chat", "tool", "unknown"]
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
    The Single Cognitive Step (Phase 4).
    Decides intent AND whether memory is needed.
    """
    config = get_config()
    input_text = state["input_text"]
    
    system_prompt = """You are ARC (Autonomous Reasoning Companion).
    
    DECISION RULES:
    1. INTENT: "chat", "tool", or "unknown".
    2. MEMORY: Set "needs_memory": true ONLY if the user asks about:
       - Past interactions ("what did I just do?", "last command")
       - Personal details ("what is my name?", "who am I?")
       - Implicit context ("remember that?", "like before")
       OTHERWISE set false. Default is FALSE.
    
    OUTPUT JSON:
    {
        "intent": "chat" | "tool" | "unknown",
        "justification": "Why?",
        "confidence": 0.0-1.0,
        "tool_command": {name, args} or null,
        "needs_memory": boolean,
        "final_response": "Response string (used only if needs_memory is false)",
        "memory_decision": {
            "episodic": boolean (log this tool use?),
            "long_term": boolean (explicit 'remember this'),
            "user_fact": [list of strings]
        }
    }

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
        
        logger.info(f"🧠 Reasoning on: {input_text}")
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
            "needs_memory": decision.get("needs_memory", False), # Phase 4
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

def context_loader(state: AgentState) -> dict:
    """
    Phase 4: Loads memory context if Reasoning requested it.
    """
    try:
        mem_mgr = get_memory_manager()
        context_parts = []
        
        # 1. User Profile
        facts = mem_mgr.get_profile()
        if facts:
            context_parts.append("USER PROFILE:\n" + "\n".join(f"- {f}" for f in facts))
            
        # 2. Recent Episodic (Last 3)
        history = mem_mgr.get_recent_episodic(limit=3)
        if history:
            history_str = "\n".join([f"- {h['timestamp']}: {h['tool']} ({h['outcome']})" for h in history])
            context_parts.append("RECENT ACTIVITY:\n" + history_str)
            
        final_context = "\n\n".join(context_parts) if context_parts else "No relevant memory found."
        logger.info(f"📚 Context Loaded ({len(final_context)} chars)")
        
        return {"memory_context": final_context}
        
    except Exception as e:
        logger.error(f"Context load failed: {e}")
        return {"memory_context": "Error loading memory."}

def chat_responder(state: AgentState) -> dict:
    """
    Phase 4: Generates response using injected memory context.
    """
    config = get_config()
    context = state.get("memory_context", "")
    input_text = state["input_text"]
    
    system_prompt = f"""You are ARC. Repond to the user using the provided context.
    
    [MEMORY CONTEXT]
    {context}
    
    [INSTRUCTION]
    Answer naturally. Do not explicitly say "According to my memory".
    """
    
    try:
        llm = ChatOllama(
            model=config.llm.model_name,
            base_url=config.llm.base_url,
            temperature=0.7
        )
        
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=input_text)
        ])
        
        return {"final_response": response.content}
    except Exception as e:
        return {"final_response": "I tried to remember, but something went wrong."}

def recovery_engine(state: AgentState) -> dict:
    """
    The Reporter. Explains what went wrong or asks for clarification.
    """
    config = get_config()
    failure_reason = state.get("failure_reason")
    confidence = state.get("confidence", 1.0)
    
    logger.warning(f"⚠️ Entering Recovery. Fail: {failure_reason}, Conf: {confidence}")
    
    system_prompt = """You are ARC's Recovery System.
    Something went wrong or the agent was unsure.
    Explain the error or ask for clarification.
    DO NOT plan actions.
    """
    
    prompt = f"Context: User said '{state['input_text']}'.\n"
    if failure_reason:
        prompt += f"Error: {failure_reason}"
    else:
        prompt += f"Issue: Low confidence ({confidence})."
        
    try:
        llm = ChatOllama(
            model=config.llm.model_name,
            base_url=config.llm.base_url,
            temperature=0.3
        )
        
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt)
        ])
        
        return {
            "final_response": response.content,
            "recovery_attempt": True
        }
    except Exception as e:
         return {
            "final_response": "I encountered a critical error and cannot recover.",
            "recovery_attempt": True
        }

def tool_gateway(state: AgentState) -> dict:
    """
    Executes the tool command. Handles failures explicitly.
    """
    cmd = state.get("tool_command")
    if not cmd:
        return {"failure_reason": "No tool command specified."}
        
    tool_name = cmd.get("name")
    tool_args = cmd.get("args", {})
    
    logger.info(f"🛠️ Executing: {tool_name} with {tool_args}")
    
    try:
        # Hardcoded tools
        result = ""
        if tool_name == "list_apps":
            result = "Apps: Code, Chrome, Terminal (Mock)"
        elif tool_name == "list_files":
            import os
            files = os.listdir(".")[:5]
            result = f"Files: {', '.join(files)}"
        else:
            raise ValueError(f"Tool '{tool_name}' not found.")
            
        return {"tool_result": result}
        
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return {"failure_reason": str(e)}

def memory_processor(state: AgentState) -> dict:
    """
    Sequential Memory Processor.
    Writes to disk if criteria are met. No LLM calls.
    Safety: Best-effort only. Failures logged but ignored.
    """
    try:
        mem_mgr = get_memory_manager()
        dec = state.get("memory_decision", {})
        
        # 1. Long-Term Memory (User Facts)
        # Strict check: Must be flagged by reasoning + have facts
        if dec.get("long_term") and dec.get("user_fact"):
            mem_mgr.update_profile(dec.get("user_fact"))
            
        # 2. Episodic Memory (Tools)
        # Criteria: It was a tool attempt, outcome is known (success or fail)
        # We ignore 'chat' intent for episodic memory
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
        
    return {} # Side-effect only, no state update needed really

# --- Graph Definition ---

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
        # 1. Low Confidence -> Recovery
        if state.get("confidence", 0.0) < 0.5:
            return "recovery"
            
        # 2. Tool Intent -> Tools
        if state.get("intent") == "tool":
            return "tools"
            
        # 3. Chat Intent
        if state.get("needs_memory"):
            return "context_loader"
        else:
            return "memory" # Standard chat, directly to memory/end

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
    
    # Context Path: Loader -> Responder -> Memory
    workflow.add_edge("context_loader", "chat_responder")
    workflow.add_edge("chat_responder", "memory")
    
    # Tool Path
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
