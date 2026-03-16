"""CLI script to sync graph from Chroma to Neo4j."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.graph_builder import main

if __name__ == "__main__":
    main()
