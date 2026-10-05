"""Start the chat UI from the repository root: uv run --group ui python -m ui [chainlit options, e.g. --port 8001]

Chainlit's config, readme and uploaded files live in ui/; the working directory stays the
repository root, where the agent keeps its SEC and Tavily caches.
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("CHAINLIT_APP_ROOT", str(HERE))  # read when chainlit is imported

from chainlit.cli import cli  # noqa: E402

cli(["run", str(HERE / "app.py"), *sys.argv[1:]])
