# Demo 3: Patch File - Step 2 (Apply Patches)

Apply search/replace patches to configuration.

## Task Definition

Step [1/1] - Update configuration values
Action: Patch file
File Path: example/output/app_config.py

```
<<<< SEARCH
DEBUG = False
==== REPLACE
DEBUG = True
>>>>

<<<< SEARCH
PORT = 8080
==== REPLACE
PORT = 3000
>>>>

<<<< SEARCH
HOST = "localhost"
==== REPLACE
HOST = "0.0.0.0"
>>>>
```
