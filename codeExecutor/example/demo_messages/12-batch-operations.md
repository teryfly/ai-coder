
# Demo 12: Batch Operations

Complete workflow demonstrating multiple operations.

## Task Definition

Step [1/8] - Create project root
Action: Create folder
File Path: example/output/webapp

------

Step [2/8] - Create src folder
Action: Create folder
File Path: example/output/webapp/src

------

Step [3/8] - Create main application file
Action: Create file
File Path: example/output/webapp/src/app.py

```python
"""Main application module."""

from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "Hello, World!"

if __name__ == "__main__":
    app.run(debug=True)
```

------

Step [4/8] - Create configuration file
Action: Create file
File Path: example/output/webapp/src/config.py

```python
"""Application configuration."""

DEBUG = False
PORT = 5000
HOST = "localhost"
```

------

Step [5/8] - Update configuration to enable debug
Action: Patch file
File Path: example/output/webapp/src/config.py

```
<<<< SEARCH
DEBUG = False
==== REPLACE
DEBUG = True
>>>>
```

------

Step [6/8] - Create requirements file
Action: Create file
File Path: example/output/webapp/requirements.txt

```
flask==2.3.0
python-dotenv==1.0.0
```

------

Step [7/8] - Create README
Action: Create file
File Path: example/output/webapp/README.md

```markdown
# Web Application

A simple Flask web application.

## Installation

\`\`\`bash
pip install -r requirements.txt
\`\`\`

## Usage

\`\`\`bash
python src/app.py
\`\`\`

## Features

- Simple web server
- Debug mode enabled
- Easy configuration
```

------

Step [8/8] - Add license section to README
Action: Append to file
File Path: example/output/webapp/README.md

```markdown

## License

MIT License - See LICENSE file for details.
```