import time
from morgan.config import Config
from morgan.tools import bash_background, bash_output, kill_shell
import morgan.sandbox

def test_bash_background(workspace: Config) -> None:
    # Run a simple sleep command
    res = bash_background("echo 'started' && sleep 5 && echo 'done'", config=workspace)
    assert "Started background task with PID:" in res
    
    # Extract PID
    pid = int(res.split(":")[-1].strip())
    
    # Read output
    time.sleep(0.5)
    out = bash_output(pid, config=workspace)
    assert "started" in out
    
    # Kill process
    kill_res = kill_shell(pid, config=workspace)
    assert "terminated" in kill_res

def test_bash_output_finished_task(workspace: Config) -> None:
    res = bash_background("echo 'quick'", config=workspace)
    pid = int(res.split(":")[-1].strip())
    
    time.sleep(0.5)
    out = bash_output(pid, config=workspace)
    assert "quick" in out
    assert "Task exited with code 0" in out
