"""Morgan sandbox module — sandbox provider interface + local subprocess adapter."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str


import subprocess
import os
import signal
from typing import Dict, Optional
from morgan.config import Config

@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str

class LocalSandbox:
    """Sandbox provider interface for isolated command execution (Local Subprocess)."""
    
    _background_tasks: Dict[int, subprocess.Popen] = {}

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self.workspace_dir = self.config.workspace_dir

    def run_background(self, command: str, cwd: str | None = None) -> int:
        """Execute *command* in the background, returning the PID."""
        from morgan.tools import resolve_and_validate
        
        target_cwd = resolve_and_validate(cwd or ".", self.workspace_dir)
        
        # Start process with its own process group so we can kill its children
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=str(target_cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        
        os.set_blocking(process.stdout.fileno(), False)
        
        pid = process.pid
        self._background_tasks[pid] = process
        return pid

    def get_output(self, pid: int) -> str:
        """Read available output from a background task."""
        if pid not in self._background_tasks:
            return f"Error: No background task with PID {pid}"
            
        process = self._background_tasks[pid]
        
        if process.poll() is not None:
            output = process.stdout.read() or ""
            del self._background_tasks[pid]
            return f"Task exited with code {process.returncode}.\nOutput:\n{output}"
            
        try:
            # Read all available non-blocking output
            output = process.stdout.read() or ""
            return output
        except Exception:
            return ""

    def kill(self, pid: int) -> str:
        """Terminate a background task and all its children."""
        if pid not in self._background_tasks:
            return f"Error: No background task with PID {pid}"
            
        process = self._background_tasks[pid]
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=2)
        except Exception:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except Exception:
                pass
                
        del self._background_tasks[pid]
        return f"Task {pid} terminated."

    @classmethod
    def cleanup_all(cls) -> None:
        """Kill all tracked background processes. Usually called on exit."""
        for pid in list(cls._background_tasks.keys()):
            try:
                process = cls._background_tasks[pid]
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except Exception:
                pass
        cls._background_tasks.clear()

class DockerSandbox:
    """Sandbox provider that executes commands inside an ephemeral Docker container."""
    
    def __init__(self, config: Config | None = None, image: str = "python:3.12-slim") -> None:
        self.config = config or Config()
        self.workspace_dir = self.config.workspace_dir
        self.image = image
        self.container_name = f"morgan_sandbox_{os.getpid()}"
        self._ensure_container()

    def _ensure_container(self) -> None:
        """Start the background container if it isn't running."""
        # Simple check if container exists
        res = subprocess.run(f"docker ps -q -f name={self.container_name}", shell=True, capture_output=True, text=True)
        if not res.stdout.strip():
            logger.info("Starting Docker sandbox: %s", self.container_name)
            subprocess.run(
                f"docker run -d --name {self.container_name} -v {self.workspace_dir}:/workspace -w /workspace {self.image} tail -f /dev/null",
                shell=True,
                check=True
            )

    def run_background(self, command: str, cwd: str | None = None) -> int:
        """Execute a command in the container via docker exec."""
        target_cwd = cwd or "/workspace"
        
        # We use a trick: start a detached docker exec and capture its PID in the host...
        # But for a real system we'd manage the exec session. For now we use the LocalSandbox pattern
        # by running the docker exec command as a local background process.
        docker_cmd = f"docker exec -w {target_cwd} {self.container_name} sh -c '{command}'"
        
        process = subprocess.Popen(
            docker_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid,
            bufsize=1,
            universal_newlines=True
        )
        os.set_blocking(process.stdout.fileno(), False)
        
        LocalSandbox._background_tasks[process.pid] = process
        return process.pid

    def get_output(self, pid: int) -> str:
        # We delegate output reading to LocalSandbox since the wrapper is running locally
        return LocalSandbox().get_output(pid)

    def kill(self, pid: int) -> str:
        return LocalSandbox().kill(pid)
        
    def cleanup(self) -> None:
        """Stop and remove the container."""
        subprocess.run(f"docker rm -f {self.container_name}", shell=True, capture_output=True)

import atexit
atexit.register(LocalSandbox.cleanup_all)
