import os
import sys

# Add src to sys.path
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from sync_db2 import sync

class SyncService:
    def __init__(self, db_path):
        self.db_path = db_path

    def run_sync(self, selection):
        try:
            sync(selection)
            return {"success": True, "message": f"Synchronization for {selection} complete."}
        except Exception as e:
            return {"success": False, "error": str(e)}
