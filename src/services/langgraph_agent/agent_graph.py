import json
import logging
from typing import TypedDict

logger = logging.getLogger(__name__)

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from tools import TOOL_DESCRIPTIONS, analyse_property_image, query_similar_listings

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)


class AgentState(TypedDict):
    query: str
    plan: list[dict]
    tool_results: dict
    reasoning_steps: list[str]
    answer: str
    tools_used: list[str]


PLANNER_PROMPT = f"""You are a real estate AI agent. Decide which tools to call for the user query. 
Available tools: 
- query_similar_listings(description: str): {TOOL_DESCRIPTIONS["query_similar_listings"]} 
- analyse_property_image(image_url: str): {TOOL_DESCRIPTIONS["analyse_property_image"]} 

Respond ONLY with a valid JSON array of tool calls. 
Each item must be: {{"tool": "<name>", "args": {{"<param>": "<value>"}}}} 
If no tools are needed, respond with: [] 

Rules: 
- A query may require ZERO, ONE, or BOTH tools.
- Use query_similar_listings for market/history/comparison/similar listings/ questions even if no full listing description is provided.
  or any request asking about available, past, or comparable real estate data.
- Use analyse_property_image whenever visual/image information is requested and a URL is present.
- Extract arguments only from explicit query content.
- Do NOT invent missing data.
""" 

SYNTHESISER_PROMPT = """You are a senior real estate analyst.
Use the tool results below to write a comprehensive answer. Include ALL of the following that apply:

1. Similar past listings (if query_similar_listings was called):
   - List every similar property returned: title, type, description, asking price.
   - Write a market insight paragraph comparing the new listing to each similar property by name.

2. Image analysis (if analyse_property_image was called):
   - For each image analysed, report the room type and condition score.

Be detailed. Include all data from the tool results. Do not invent information not present in the results."""

# The planner node will decide which tools to call based on the query.
async def planner_node(state: AgentState) -> dict:
    response = await _llm.ainvoke([
        SystemMessage(content=PLANNER_PROMPT),
        HumanMessage(content=state["query"]),
    ])
    try:
        raw = response.content.strip() # Its include code block markdown, so we need to extract the JSON part
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        plan = json.loads(raw)
        if not isinstance(plan, list):
            plan = []
    except Exception:
        plan = []

    tool_names = [t["tool"] for t in plan] or ["none"]
    logger.info("Planner decided: %s", tool_names)
    return {
        "plan": plan,
        "reasoning_steps": [f"Decided to call: {tool_names}"],
    }

# The tool executor node will take the plan from the planner, execute the tools, and store the results.
async def tool_executor_node(state: AgentState) -> dict:
    results = {}
    steps = list(state["reasoning_steps"])
    tools_used = []

            # Example plan:
            # [
            #   {
            #     "tool": "analyse_property_image",
            #     "args": {
            #       "image_url": "https://a.jpg"
            #     }
            #   },
            #   {
            #     "tool": "query_similar_listings",
            #     "args": {
            #       "description": "luxury apartment"
            #     }
            #   }
            # ]
    for call in state["plan"]:
        tool_name = call.get("tool", "")
        args = call.get("args", {})
        try:
            if tool_name == "query_similar_listings":
                result = await query_similar_listings(**args)
            elif tool_name == "analyse_property_image":
                result = await analyse_property_image(**args)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
            if tool_name in results:
                if isinstance(results[tool_name], list):
                    results[tool_name].append(result)
                else:
                    results[tool_name] = [results[tool_name], result]
            else:
                results[tool_name] = result
            tools_used.append(tool_name)
            steps.append(f"Called {tool_name} → received response")
            logger.info("Tool %s succeeded", tool_name)
        except Exception as e:
            results[tool_name] = {"error": str(e)}
            steps.append(f"Called {tool_name} → error: {e}")
            logger.error("Tool %s failed: %s", tool_name, e)

    return {"tool_results": results, "tools_used": tools_used, "reasoning_steps": steps}

# The synthesiser node will take the original query and the tool results, and generate a final answer.
async def synthesiser_node(state: AgentState) -> dict: 
    context = (
        f"User query: {state['query']}\n\n"
        f"Tool results:\n{json.dumps(state['tool_results'], indent=2)}"
    )
    response = await _llm.ainvoke([
        SystemMessage(content=SYNTHESISER_PROMPT),
        HumanMessage(content=context),
    ])
    steps = list(state["reasoning_steps"])
    steps.append("Synthesised final answer")
    logger.info("Synthesiser done. Answer length: %d chars", len(response.content))
    return {"answer": response.content, "reasoning_steps": steps}


def _build_graph():
    g = StateGraph(AgentState)
    g.add_node("planner", planner_node)
    g.add_node("tool_executor", tool_executor_node)
    g.add_node("synthesiser", synthesiser_node)
    g.set_entry_point("planner")
    g.add_edge("planner", "tool_executor")
    g.add_edge("tool_executor", "synthesiser")
    g.add_edge("synthesiser", END)
    return g.compile()


_graph = _build_graph()

# The main function to run the agent with a user query. It will return the final answer along with the reasoning steps and tool results.
async def run_agent(query: str) -> dict:
    return await _graph.ainvoke({
        "query": query,
        "plan": [],
        "tool_results": {},
        "reasoning_steps": [],
        "answer": "",
        "tools_used": [],
    })
