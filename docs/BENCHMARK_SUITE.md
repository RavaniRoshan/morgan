# Morgan Benchmark Suite

This suite contains canonical tasks to evaluate Morgan's performance compared to other agents like Claude Code or Cursor.

## Metrics
1. **Wall-clock time**: Time from prompt to final answer.
2. **Token Efficiency**: Total input and output tokens consumed.
3. **Autonomy Rate**: Percentage of runs completed without human intervention.
4. **Accuracy**: Did the agent correctly fulfill the prompt?

## Tasks

### 1. The "Hello World" Scaffold
**Prompt**: "Create a basic Python package structure for a math utility library. Include a module `math_utils.py` with an add and subtract function, and write a test file `test_math.py` using pytest. Run the tests to ensure they pass."
**Expected Outcome**: Files created correctly. Tests pass.
**Baseline (Claude Code)**: ~45 seconds, 8k tokens.

### 2. Refactoring a Monolith
**Prompt**: "Refactor the 1000-line `app.py` script into a modular directory structure with `routes/`, `models/`, and `services/`. Update all imports and ensure the server still starts."
**Expected Outcome**: Clean separation of concerns. No broken imports.
**Baseline (Claude Code)**: ~120 seconds, 35k tokens.

### 3. Background Integration Test
**Prompt**: "Start a Redis server in the background using docker. Write a Python script that connects to it and sets a key. Run the script, verify the key, and clean up the server."
**Expected Outcome**: Background process management handles the container correctly.
**Baseline (Claude Code)**: ~90 seconds, 15k tokens.
