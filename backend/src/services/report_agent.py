import json
from typing import Any

from src.core.logger import logger
from src.services.github import GitHubService
from src.services.llm_client import GroqLLMClient, LLMClientError
from src.schemas.repo_info import RepositoryInfoResponse
from src.services.report_service import ReportService

SYSTEM_PROMPT_AGENT = """You are an expert software architect and security auditor.
You are tasked with generating a comprehensive analysis report for a GitHub repository.
You have access to tools that allow you to explore the repository's file tree and read specific files.

Use the tools to read important configuration files, build scripts, architecture documentation, or key source code files.
Once you have sufficient context, YOU MUST output the final comprehensive markdown report. DO NOT return an empty response. Your final response should ONLY be the markdown report, with NO tool calls.

The final report MUST follow this exact structure, with exactly five '##' sections:
## 1. Project Overview
## 2. Technology Stack
## 3. Repository Structure & Code Organization
## 4. Recent Activity & Maintenance Health
## 5. Recommendations

Constraints:
- Use GitHub Flavored Markdown.
- You can use tables, lists, and bold text.
- Do NOT output any content outside of these 5 sections in your final report.
- Rely on facts you find using the tools. If you cannot find something, state that it is unknown.
"""

MAX_STEPS = 8
MAX_OUTPUT_TOKENS = 4000

agent_tools = [
    {
        "type": "function",
        "function": {
            "name": "list_file_tree",
            "description": "Lists the full recursive file tree of the repository.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the content of a specific file from the repository. Use this to inspect code, configs (like package.json, requirements.txt), and documentation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The exact path to the file to read, e.g., 'src/main.py'"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_pull_request",
            "description": "Creates a new file (or updates an existing one) in a new branch and opens a Pull Request. Use this to suggest fixes, configuration files, or improvements directly to the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to create or update, e.g., '.github/workflows/pages.yml' or 'vercel.json'"
                    },
                    "content": {
                        "type": "string",
                        "description": "The exact content of the file to write."
                    },
                    "commit_message": {
                        "type": "string",
                        "description": "A concise commit message describing the change."
                    },
                    "pr_title": {
                        "type": "string",
                        "description": "The title for the Pull Request."
                    },
                    "pr_body": {
                        "type": "string",
                        "description": "The description body for the Pull Request explaining why this change is suggested."
                    }
                },
                "required": ["file_path", "content", "commit_message", "pr_title", "pr_body"]
            }
        }
    }
]

async def run_agent_loop(github_token: str, owner: str, repo: str) -> dict[str, Any]:
    """
    Runs the multi-tool agent loop to generate a comprehensive report.
    Returns a dictionary with:
      - report_markdown (str)
      - prompt_tokens (int)
      - completion_tokens (int)
      - model_used (str)
      - trace (list of str)
    """
    logger.info(f"Agent loop started for {owner}/{repo}")
    
    # Get basic repo info to get default branch and base context
    repo_info: RepositoryInfoResponse = await GitHubService.get_repository_info(
        token=github_token,
        owner=owner,
        repo=repo,
    )
    
    if not repo_info.success:
        raise Exception(repo_info.message or f"Could not fetch {owner}/{repo}")
        
    default_branch = repo_info.basic_info.default_branch or "main"
    base_context = ReportService._summarize_repo_info(repo_info)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_AGENT},
        {"role": "user", "content": f"Analyze the repository '{owner}/{repo}'. Here is the initial high-level context:\n\n{base_context}\n\nNow explore the files as needed to write a detailed report."}
    ]
    
    llm = GroqLLMClient()
    total_prompt_tokens = 0
    total_completion_tokens = 0
    trace = []
    
    for step in range(MAX_STEPS):
        logger.info(f"Agent loop step {step + 1}/{MAX_STEPS} for {owner}/{repo}")
        
        try:
            # For intermediate steps, we only need a few tokens for tool calls.
            # Setting this low prevents hitting TPM (Tokens Per Minute) rate limits on free tiers
            # since providers like Groq calculate TPM as (prompt_tokens + max_tokens).
            step_max_tokens = min(4000, max(500, 8000 - total_prompt_tokens - 500))
            
            result = await llm.chat_completion(
                messages=messages,
                temperature=0.2,
                max_tokens=step_max_tokens,
                tools=agent_tools
            )
        except LLMClientError as e:
            # If the LLM call fails, we abort the loop
            raise e
            
        total_prompt_tokens += result.get("prompt_tokens", 0)
        total_completion_tokens += result.get("completion_tokens", 0)
        used_model = result.get("model")
        
        tool_calls = result.get("tool_calls")
        content = result.get("content")
        
        if tool_calls:
            # Add assistant message with tool calls
            # OpenAI API requires sending the assistant message with tool_calls back
            # We use the raw_message to preserve provider-specific fields (like Gemini's thought_signature)
            raw_msg = result.get("raw_message")
            if raw_msg:
                # Pydantic v2 model_dump
                messages.append(raw_msg.model_dump(exclude_none=True))
            else:
                assistant_msg = {
                    "role": "assistant",
                    "content": content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in tool_calls
                    ]
                }
                messages.append(assistant_msg)
            
            for tc in tool_calls:
                func_name = tc.function.name
                call_id = tc.id
                
                logger.info(f"Agent tool call: {func_name}")
                
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                    
                tool_result = ""
                if func_name == "list_file_tree":
                    trace.append(f"list_file_tree()")
                    tool_result = await GitHubService.list_file_tree_recursive(
                        token=github_token,
                        owner=owner,
                        repo=repo,
                        branch=default_branch
                    )
                elif func_name == "read_file":
                    path = args.get("path", "")
                    trace.append(f"read_file({path})")
                    if not path:
                        tool_result = "Error: path argument missing."
                    else:
                        tool_result = await GitHubService.read_file_content(
                            token=github_token,
                            owner=owner,
                            repo=repo,
                            path=path
                        )
                elif func_name == "create_pull_request":
                    file_path = args.get("file_path", "")
                    content_str = args.get("content", "")
                    commit_msg = args.get("commit_message", "Automated suggestion by AI Agent")
                    pr_title = args.get("pr_title", "Automated AI Suggestion")
                    pr_body = args.get("pr_body", "This PR was generated by DeployBridge AI.")
                    
                    trace.append(f"create_pull_request({file_path})")
                    if not file_path or not content_str:
                        tool_result = "Error: file_path and content arguments are required."
                    else:
                        tool_result = await GitHubService.create_file_and_pull_request(
                            token=github_token,
                            owner=owner,
                            repo=repo,
                            file_path=file_path,
                            content=content_str,
                            commit_message=commit_msg,
                            pr_title=pr_title,
                            pr_body=pr_body
                        )
                else:
                    tool_result = f"Error: unknown tool {func_name}"
                
                # Add tool result message
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": func_name,
                    "content": str(tool_result)[:30000] # Cap tool response to avoid massive contexts
                })
                
        else:
            # No tool calls, we have the final report
            logger.info(f"Agent loop finished at step {step + 1}")
            
            # Append trace to the bottom of the markdown
            trace_markdown = "\n\n---\n**Agent Trace:**\n"
            if not trace:
                trace_markdown += "- No tools used (fallback to initial context)"
            else:
                for t in trace:
                    trace_markdown += f"- `{t}`\n"
            trace_markdown += f"- Total reasoning rounds: {step + 1}\n"
            
            final_markdown = content + trace_markdown
            
            return {
                "report_markdown": final_markdown,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "model_used": used_model,
                "trace": trace
            }
            
    # If we exhaust MAX_STEPS, force a final generation without tools
    logger.warning(f"Agent hit MAX_STEPS ({MAX_STEPS}). Forcing final report.")
    messages.append({
        "role": "user",
        "content": "You have reached the maximum number of tool steps. Output the final markdown report NOW based on the context you have gathered so far."
    })
    
    result = await llm.chat_completion(
        messages=messages,
        temperature=0.2,
        max_tokens=MAX_OUTPUT_TOKENS,
        tools=None # No tools allowed, force content
    )
    
    total_prompt_tokens += result.get("prompt_tokens", 0)
    total_completion_tokens += result.get("completion_tokens", 0)
    used_model = result.get("model")
    
    content = result.get("content", "")
    
    trace_markdown = "\n\n---\n**Agent Trace:**\n"
    for t in trace:
        trace_markdown += f"- `{t}`\n"
    trace_markdown += f"- Total reasoning rounds: {MAX_STEPS} (Maxed out)\n"
    
    final_markdown = content + trace_markdown
    
    return {
        "report_markdown": final_markdown,
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "model_used": used_model,
        "trace": trace
    }
