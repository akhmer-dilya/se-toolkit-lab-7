"""Intent-based natural language routing with LLM tool calling.

This module implements the core intent router:
1. Defines all 9 backend endpoints as LLM tool schemas
2. Routes user messages to the LLM with tool definitions
3. Executes tool calls and feeds results back to the LLM
4. Returns the final summarized response
"""

import json
import logging
import sys
from typing import Any

from services.llm_client import LLMClient
from services.lms_api import LMSAPIClient

logger = logging.getLogger(__name__)

# System prompt for the intent router
SYSTEM_PROMPT = """You are an intelligent assistant for a Learning Management System (LMS). 
Your job is to help users understand lab results, student performance, and completion rates.

You have access to tools that query the LMS backend. When a user asks a question:
1. Think about what data you need to answer
2. Call the appropriate tool(s) with the right arguments
3. If you need data from multiple sources, make multiple tool calls
4. Once you have the data, summarize it clearly for the user

Available tools and when to use them:
- get_items: List all labs and tasks. Use when user asks "what labs are available" or needs lab identifiers.
- get_learners: List enrolled students and groups. Use for questions about enrollment or student lists.
- get_scores: Get score distribution (4 buckets) for a specific lab. Use for detailed score breakdowns.
- get_pass_rates: Get per-task average scores and attempt counts for a lab. Use for "show me scores for lab X" or comparing task difficulty.
- get_timeline: Get submissions per day for a lab. Use for questions about submission patterns over time.
- get_groups: Get per-group scores and student counts for a lab. Use for "which group is best" or group comparisons.
- get_top_learners: Get top N learners by score for a lab. Use for "who are the top students" or leaderboards.
- get_completion_rate: Get completion rate percentage for a lab. Use for "how many students completed" questions.
- trigger_sync: Refresh data from autochecker. Use when user explicitly asks to sync/refresh data.

Important rules:
- Always call get_items first if you need to know lab identifiers (like "lab-01", "lab-02", etc.)
- For comparisons across labs (e.g., "which lab has the lowest pass rate"), get all labs first, then call get_pass_rates for each
- Be specific with lab identifiers - use the exact format like "lab-01", "lab-02", etc.
- If the user's message is a greeting, respond warmly and briefly mention what you can help with
- If the user's message is unclear or gibberish, politely ask for clarification and suggest what you can do
- Always provide numerical data when available (percentages, counts, etc.)

Respond with tool calls when you need data, or with a direct answer if you already have enough information."""


def get_tool_definitions() -> list[dict[str, Any]]:
    """Define all 9 backend endpoints as LLM tool schemas."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_items",
                "description": "List of labs and tasks. Use to discover available lab identifiers.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_learners",
                "description": "Enrolled students and groups. Use for questions about enrollment or student lists.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_scores",
                "description": "Score distribution (4 buckets) for a specific lab.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier, e.g. 'lab-01', 'lab-02'",
                        },
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_pass_rates",
                "description": "Per-task average scores and attempt counts for a lab.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier, e.g. 'lab-01', 'lab-02'",
                        },
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_timeline",
                "description": "Submissions per day for a lab. Use for timeline/pattern analysis.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier, e.g. 'lab-01', 'lab-02'",
                        },
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_groups",
                "description": "Per-group scores and student counts for a lab. Use for group comparisons.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier, e.g. 'lab-01', 'lab-02'",
                        },
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_top_learners",
                "description": "Top N learners by score for a lab. Use for leaderboards.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier, e.g. 'lab-01', 'lab-02'",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of top learners to return, e.g. 5, 10",
                            "default": 5,
                        },
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_completion_rate",
                "description": "Completion rate percentage for a lab.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier, e.g. 'lab-01', 'lab-02'",
                        },
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "trigger_sync",
                "description": "Refresh data from autochecker. Use when user asks to sync/refresh data.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
    ]


def execute_tool(tool_name: str, arguments: dict[str, Any], api_client: LMSAPIClient) -> Any:
    """Execute a tool call by mapping to LMS API methods.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Arguments passed by the LLM
        api_client: LMS API client instance
        
    Returns:
        Result from the API call
    """
    tool_handlers = {
        "get_items": lambda: api_client.get_items(),
        "get_learners": lambda: api_client.get_learners(),
        "get_scores": lambda: api_client.get_analytics_scores(arguments.get("lab", "")),
        "get_pass_rates": lambda: api_client.get_analytics_pass_rates(arguments.get("lab", "")),
        "get_timeline": lambda: api_client.get_analytics_timeline(arguments.get("lab", "")),
        "get_groups": lambda: api_client.get_analytics_groups(arguments.get("lab", "")),
        "get_top_learners": lambda: api_client.get_analytics_top_learners(
            arguments.get("lab", ""), 
            arguments.get("limit", 5)
        ),
        "get_completion_rate": lambda: api_client.get_analytics_completion_rate(arguments.get("lab", "")),
        "trigger_sync": lambda: api_client.sync_pipeline(),
    }
    
    handler = tool_handlers.get(tool_name)
    if not handler:
        return {"error": f"Unknown tool: {tool_name}"}
    
    try:
        return handler()
    except Exception as e:
        return {"error": str(e)}


def route_message(user_message: str, llm_client: LLMClient, api_client: LMSAPIClient, debug: bool = False) -> str:
    """Route a user message through the LLM intent router.
    
    This implements the conversation loop:
    1. Send user message + tool definitions to LLM
    2. LLM returns tool calls (or direct response)
    3. Execute tool calls and get results
    4. Feed results back to LLM
    5. LLM produces final answer
    
    Args:
        user_message: The user's natural language message
        llm_client: LLM client instance
        api_client: LMS API client instance
        debug: If True, print debug info to stderr
        
    Returns:
        Final response string
    """
    def debug_log(msg: str) -> None:
        if debug:
            print(msg, file=sys.stderr)
    
    # Initialize conversation with user message
    messages = [
        {"role": "user", "content": user_message}
    ]
    
    # Get tool definitions
    tools = get_tool_definitions()
    
    # Maximum iterations to prevent infinite loops
    max_iterations = 5
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # Call LLM
        response = llm_client.chat(
            messages=messages,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
        )
        
        # Check if LLM wants to call tools
        tool_calls = response.get("tool_calls", [])
        
        if not tool_calls:
            # LLM returned a direct response (no tools needed)
            content = response.get("content", "")
            if content:
                return content
            else:
                return "I'm not sure how to help with that. Try asking about labs, scores, pass rates, or student performance."
        
        # Execute tool calls
        tool_results = []
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            tool_name = function.get("name", "unknown")
            # Parse arguments - they come as a JSON string
            args_str = function.get("arguments", "{}")
            try:
                arguments = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                arguments = {}
            
            debug_log(f"[tool] LLM called: {tool_name}({arguments})")
            
            # Execute the tool
            result = execute_tool(tool_name, arguments, api_client)
            tool_results.append({
                "tool_call_id": tool_call.get("id", ""),
                "name": tool_name,
                "result": result,
            })
            
            debug_log(f"[tool] Result: {len(str(result))} chars")
        
        # Add assistant's message with tool calls to conversation
        messages.append({
            "role": "assistant",
            "content": response.get("content", ""),
            "tool_calls": tool_calls,
        })
        
        # Feed tool results back to LLM
        for tr in tool_results:
            messages.append({
                "role": "tool",
                "tool_call_id": tr["tool_call_id"],
                "content": json.dumps(tr["result"], default=str) if not isinstance(tr["result"], str) else tr["result"],
                "name": tr["name"],
            })
        
        debug_log(f"[summary] Feeding {len(tool_results)} tool result(s) back to LLM")
    
    # If we reach max iterations, return what we have
    return "I'm having trouble processing this request. Please try rephrasing your question."


def get_keyboard_buttons() -> list[list[dict[str, str]]]:
    """Get inline keyboard buttons for common queries.
    
    Returns:
        List of button rows, each row is a list of button dicts
    """
    return [
        [
            {"text": "📚 Available Labs", "callback_data": "btn_labs"},
            {"text": "📊 Lab Scores", "callback_data": "btn_scores"},
        ],
        [
            {"text": "🏆 Lowest Pass Rate", "callback_data": "btn_lowest"},
            {"text": "👥 Top Students", "callback_data": "btn_top"},
        ],
        [
            {"text": "🔄 Sync Data", "callback_data": "btn_sync"},
            {"text": "❓ Help", "callback_data": "btn_help"},
        ],
    ]
