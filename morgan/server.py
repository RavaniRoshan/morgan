"""Morgan Web Server — FastAPI + SSE monitoring UI."""

import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Morgan UI")

html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Morgan Autonomy Dashboard</title>
    <style>
        body { font-family: Inter, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 2rem; }
        h1 { color: #38bdf8; }
        #log { background: #1e293b; padding: 1rem; border-radius: 8px; font-family: monospace; height: 60vh; overflow-y: scroll; }
        .log-entry { margin-bottom: 0.5rem; }
        .system { color: #94a3b8; }
        .action { color: #a3e635; }
        .error { color: #f87171; }
    </style>
</head>
<body>
    <h1>Morgan Dashboard</h1>
    <div id="log"></div>
    <script>
        const evtSource = new EventSource("/stream");
        const logDiv = document.getElementById("log");
        evtSource.onmessage = function(event) {
            const el = document.createElement("div");
            el.className = "log-entry " + event.type;
            el.textContent = event.data;
            logDiv.appendChild(el);
            logDiv.scrollTop = logDiv.scrollHeight;
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return html_content

async def log_generator():
    """Mock generator that would hook into morgan's audit logs."""
    yield "data: Morgan Web UI initialized.\\n\\n"
    while True:
        await asyncio.sleep(5)
        yield "data: Heartbeat... waiting for events.\\n\\n"

@app.get("/stream")
async def stream_logs(request: Request):
    return StreamingResponse(log_generator(), media_type="text/event-stream")

def start_server(port: int = 8080):
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    start_server()
