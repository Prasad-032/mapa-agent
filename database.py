import asyncpg, os

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(os.environ["DB_CONNECTION_STRING"], min_size=1, max_size=5)
    return _pool

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title TEXT NOT NULL,
                priority TEXT DEFAULT 'MED',
                due_date TEXT,
                status TEXT DEFAULT 'open',
                agent_id TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS calendar_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title TEXT NOT NULL,
                start_time TEXT,
                duration_m INTEGER DEFAULT 30,
                attendees TEXT[],
                task_ref UUID,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS notes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title TEXT NOT NULL,
                content TEXT,
                tags TEXT[],
                linked_task UUID,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS workflow_runs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                intent TEXT,
                agents_used TEXT[],
                duration_ms INTEGER,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
