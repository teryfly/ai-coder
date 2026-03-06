# Demo 3: Patch File - Step 1 (Create Initial)

Create configuration file to be patched.

## Task Definition

Step [1/1] - Create configuration file
Action: Create file
File Path: example/output/app_config.py

```python
"""Application configuration."""

DEBUG = False
PORT = 8080
HOST = "localhost"
DATABASE = "sqlite:///app.db"

def get_config():
    """Return configuration dictionary."""
    return {
        "debug": DEBUG,
        "port": PORT,
        "host": HOST,
        "database": DATABASE
    }
```
