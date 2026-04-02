import asyncio, time, os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import init_db, get_pool
from agents import coordinator_agent, task_agent, calendar_agent, notes_agent

app = FastAPI(title="MAPA - Multi-Agent Productivity Assistant")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def startup():
    await init_db()

class WorkflowRequest(BaseModel):
    message: str

@app.get("/")
async def root():
    return {"status": "MAPA Agent System running", "version": "1.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/workflow")
async def run_workflow(req: WorkflowRequest):
    try:
        start = time.time()
        plan = await coordinator_agent(req.message)
        results = {}
        agents_used = ["coordinator"] + plan.get("agents", [])
        tasks = []
        if "task" in plan.get("agents", []) and "task" in plan:
            tasks.append(("task", task_agent(plan["task"])))
        if "calendar" in plan.get("agents", []) and "calendar" in plan:
            tasks.append(("calendar", calendar_agent(plan["calendar"])))
        if "notes" in plan.get("agents", []) and "notes" in plan:
            tasks.append(("notes", notes_agent(plan["notes"])))
        if tasks:
            names, coros = zip(*tasks)
            outputs = await asyncio.gather(*coros)
            results = {name: output for name, output in zip(names, outputs)}
        duration_ms = int((time.time() - start) * 1000)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO workflow_runs (intent, agents_used, duration_ms) VALUES ($1,$2::text[],$3)",
                plan.get("intent", req.message), agents_used, duration_ms
            )
        return {"intent": plan.get("intent"), "agents_used": agents_used, "results": results, "duration_ms": duration_ms}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks")
async def get_tasks():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 20")
    return [dict(r) for r in rows]

@app.get("/events")
async def get_events():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM calendar_events ORDER BY created_at DESC LIMIT 20")
    return [dict(r) for r in rows]

@app.get("/notes")
async def get_notes():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM notes ORDER BY created_at DESC LIMIT 20")
    return [dict(r) for r in rows]

@app.get("/workflows")
async def get_workflows():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM workflow_runs ORDER BY created_at DESC LIMIT 20")
    return [dict(r) for r in rows]

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

@app.get("/ui")
async def serve_ui():
    return FileResponse("index.html")
