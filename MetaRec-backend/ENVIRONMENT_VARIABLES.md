# Environment variables

- for Azure OpenAI client (used in `agent/`)
    - `OPENAI_API_KEY`:
    - `AZURE_OPENAI_ENDPOINT`
    - `AZURE_OPENAI_API_VERSION`
    - `AZURE_AGENT_PLANNING_MODEL` 
    - `AZURE_AGENT_SUMMARY_MODEL` 
    
- for OpenAI client (used in `llm_service.py`)
    - `LLM_BASE_URL`
    - `LLM_API_KEY`
    - `LLM_MODEL` (model name)
    - `AGENT_PLANNING_MODEL` fallback when Azure OpenAI client cannot be created
    - `AGENT_SUMMARY_MODEL` fallback when Azure OpenAI client cannot be created
    
- for serpapi api (used in `agent/agent_mcp/`)
    - `SERPAPI_KEY`

- for xiaohongshu (used in `agent/agent_mcp/agent_xiaohongshu.py`)
    - `TIKHUB_API_KEY`
    - `API_302_KEY`

