"""
DeepAgent implementation using LangGraph.
Manages the reasoning loop, tool execution, and state.
"""
import logging
import operator
from typing import TypedDict, Annotated, List, Union, Sequence

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from arc.config import get_config
from arc.core.llm import get_llm
from arc.mcp.client import get_mcp_manager

# Import Tools
from arc.tools.system_tools import (
    open_app, close_app, list_running_apps,
    type_text_keyboard, press_key, click_screen,
    screenshot_screen
)
from arc.tools.whatsapp import open_whatsapp, send_whatsapp_message

# MCP Tools will be dynamic

logger = logging.getLogger(__name__)

# --- State Definition ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # We can add more state here like 'context', 'scratchpad' etc.

class ARCAgent:
    def __init__(self):
        self.config = get_config()
        self.llm = get_llm()
        self.mcp_manager = get_mcp_manager()
        self.tools = []
        self.app = None # The compiled graph

    async def initialize(self):
        """
        Initialize tools and build the graph.
        """
        # 1. Gather all tools
        # Static tools
        self.tools = [
            open_app, close_app, list_running_apps,
            type_text_keyboard, press_key, click_screen, screenshot_screen,
            open_whatsapp, send_whatsapp_message
        ]
        
        # MCP Tools
        # Note: In a real system we would need to wrap MCP JSON tools into LangChain Tool objects
        # For simplicity here, we will just list the static tools.
        # Integrating dynamic MCP tools into LangGraph requires mapping them to BaseTool
        # This is a complex step usually handled by adapters. 
        # We will assume mcp_manager tools are compatible or skipped for this simplified implementation step.
        
        # For this implementation, we rely on the static system tools.
        # Future TODO: Map mcp_manager.get_all_tools() -> [BaseTool]
        
        # 2. Bind tools to LLM
        # Some local LLMs might not support bind_tools well, need fallback/prompt engineering
        if self.config.llm.backend in ["openai", "ollama"]: # OpenAI-compat usually supports function calling
             self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
             # LlamaCpp or others might need prompt engineering if no native tool calling
             logger.warning("Enhancing LLM with tools for non-OpenAI backend requires prompt engineering. Using raw bind_tools hoping for support.")
             self.llm_with_tools = self.llm.bind_tools(self.tools)

        # 3. Build Graph
        workflow = StateGraph(AgentState)

        # Define Nodes
        workflow.add_node("agent", self._call_model)
        workflow.add_node("action", ToolNode(self.tools))

        # Define Edges
        workflow.set_entry_point("agent")
        
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "action",
                "end": END
            }
        )
        
        workflow.add_edge("action", "agent")

        self.app = workflow.compile()
        logger.info("ARCAgent initialized.")

    def _call_model(self, state: AgentState):
        messages = state['messages']
        # Add system prompt if it's the first message? 
        # Typically handled by ensuring history starts with SystemMessage or prepending here.
        # Let's prepend if missing.
        if not messages or not isinstance(messages[0], SystemMessage):
            system_prompt = self._get_system_prompt()
            messages = [SystemMessage(content=system_prompt)] + list(messages)
            
        response = self.llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def _should_continue(self, state: AgentState):
        messages = state['messages']
        last_message = messages[-1]
        
        if last_message.tool_calls:
            return "continue"
        return "end"

    def _get_system_prompt(self) -> str:
        return """You are ARC (Autonomous Reasoning Companion), a capable and proactive AI assistant.
        
You have access to the user's local system, browser, and various tools.
Your goal is to help the user achieve their tasks efficiently.

CAPABILITIES:
- System Control: Open/close apps, type text, click, screenshot.
- Browser: Navigate, read pages (via MCP).
- Messaging: WhatsApp (via Browser).

RULES:
1. Always confirm before taking destructive actions (like closing apps).
2. If a tool fails, explain why and suggest alternatives.
3. Be concise and professional.
4. If you need to perform a multi-step task, explain your plan first.

Current context: User is on Mac OS.
"""

    async def ainvoke(self, message: str):
        if not self.app:
            await self.initialize()
            
        inputs = {"messages": [HumanMessage(content=message)]}
        result = await self.app.ainvoke(inputs)
        return result["messages"][-1].content

async def build_agent() -> ARCAgent:
    agent = ARCAgent()
    await agent.initialize()
    return agent
