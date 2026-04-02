import json, os, httpx
from database import get_pool

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

async def call_llm(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            NVIDIA_URL,
            headers={"Authorization": f"Bearer {NVIDIA_API_KEY}", "Accept": "application/json"},
            json={
                "model": "meta/llama-4-maverick-17b-128e-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 500
            }
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

async def coordinator_agent(user_input: str) -> dict:
    prompt = f"""You are a coordinator agent. Return ONLY valid JSON, no explanation.
Structure:
{{
  "intent": "brief description",
  "agents": ["task","calendar","notes"],
  "task": {{"title":"...","priority":"HIGH|MED|LOW","due_date":"..."}},
  "calendar": {{"title":"...","start_time":"...","duration_m":30,"attendees":[]}},
  "notes": {{"title":"...","content":"...","tags":[]}}
}}
Only include keys for agents needed. User request: {user_input}"""
    text = await call_llm(prompt)
    text = text.strip().replace("```json","").replace("```","").strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])

async def task_agent(params: dict) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO tasks (title, priority, due_date, agent_id) VALUES ($1,$2,$3,'task-agent') RETURNING id, title, priority, due_date, status",
            params.get("title","Untitled Task"),
            params.get("priority","MED"),
            params.get("due_date","TBD")
        )
    return dict(row)

async def calendar_agent(params: dict) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO calendar_events (title, start_time, duration_m, attendees) VALUES ($1,$2,$3,$4) RETURNING id, title, start_time, duration_m",
            params.get("title","Untitled Event"),
            params.get("start_time","TBD"),
            params.get("duration_m", 30),
            params.get("attendees",[])
        )
    return dict(row)

async def notes_agent(params: dict) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO notes (title, content, tags) VALUES ($1,$2,$3) RETURNING id, title, tags",
            params.get("title","Untitled Note"),
            params.get("content",""),
            params.get("tags",[])
        )
    return dict(row)
