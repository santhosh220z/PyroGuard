"""PyroGuard Unit Tests - Database Module"""

import sys
import sqlite3
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import tempfile
import os

from app.incidents.incident_db import IncidentDatabase