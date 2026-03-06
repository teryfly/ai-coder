# Demo 11: Execute Shell Command (Windows)

Execute a series of shell commands on Windows.

## Task Definition

Step [1/1] - Execute shell commands
Action: Execute shell command

```bash
mkdir example\output\shelltest
echo Hello from shell > example\output\shelltest\greeting.txt
dir example\output\shelltest
type example\output\shelltest\greeting.txt
```