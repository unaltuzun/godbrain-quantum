# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
SERAPH Memory Cloud Backup
Automatic backup of memories to Google Cloud Storage for immortality.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import gzip
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from google.cloud import storage
    HAS_GCS = True
except ImportError:
    HAS_GCS = False


ROOT = Path(__file__).parent.parent


class MemoryBackup:
    """
    Cloud backup system for Seraph memories.
    
    Features:
    - Automatic daily backups to GCS
    - Compressed storage (gzip)
    - Point-in-time recovery
    - Export/Import functionality
    
    Usage:
        backup = MemoryBackup()
        await backup.backup_now()  # Manual backup
        await backup.restore_latest()  # Restore from cloud
    """
    
    BUCKET_NAME = "godbrain-seraph-memory"
    BACKUP_PREFIX = "seraph_memory_"
    LOCAL_BACKUP_DIR = ROOT / "seraph" / "memory" / "backups"
    
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "project-9ad1ce66-06b2-4a7f-bad")
        self._client = None
        self._bucket = None
        self.LOCAL_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    def _get_client(self):
        """Get or create GCS client."""
        if not HAS_GCS:
            return None
        
        if self._client is None:
            try:
                self._client = storage.Client(project=self.project_id)
            except Exception:
                return None
        return self._client
    
    def _get_bucket(self):
        """Get or create GCS bucket."""
        client = self._get_client()
        if not client:
            return None
        
        if self._bucket is None:
            try:
                self._bucket = client.bucket(self.BUCKET_NAME)
                if not self._bucket.exists():
                    self._bucket = client.create_bucket(self.BUCKET_NAME, location="us-central1")
            except Exception:
                return None
        return self._bucket
    
    def _get_local_memory_path(self) -> Path:
        """Get path to local memory file."""
        return ROOT / "seraph" / "memory" / "long_term.json"
    
    async def backup_now(self, memory_data: Optional[Dict] = None) -> Optional[str]:
        """
        Create an immediate backup.
        
        Args:
            memory_data: Optional memory data dict, otherwise reads from file
        
        Returns:
            Backup filename if successful
        """
        # Get memory data
        if memory_data is None:
            local_path = self._get_local_memory_path()
            if local_path.exists():
                with open(local_path, "r") as f:
                    memory_data = json.load(f)
            else:
                memory_data = {}
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.BACKUP_PREFIX}{timestamp}.json.gz"
        
        # Compress data
        json_data = json.dumps(memory_data, indent=2)
        compressed = gzip.compress(json_data.encode("utf-8"))
        
        # Save locally first
        local_backup = self.LOCAL_BACKUP_DIR / filename
        with open(local_backup, "wb") as f:
            f.write(compressed)
        
        # Upload to GCS if available
        bucket = self._get_bucket()
        if bucket:
            try:
                blob = bucket.blob(f"backups/{filename}")
                blob.upload_from_filename(str(local_backup))
                print(f"☁️ Memory backup uploaded: {filename}")
            except Exception as e:
                print(f"⚠️ Cloud backup failed (local saved): {e}")
        
        return filename
    
    async def restore_latest(self) -> Optional[Dict]:
        """
        Restore from the latest backup.
        
        Returns:
            Restored memory data dict
        """
        bucket = self._get_bucket()
        
        if bucket:
            try:
                # Find latest backup in GCS
                blobs = list(bucket.list_blobs(prefix="backups/"))
                if blobs:
                    blobs.sort(key=lambda b: b.name, reverse=True)
                    latest = blobs[0]
                    
                    # Download and decompress
                    compressed = latest.download_as_bytes()
                    json_data = gzip.decompress(compressed).decode("utf-8")
                    memory_data = json.loads(json_data)
                    
                    # Save to local
                    local_path = self._get_local_memory_path()
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(local_path, "w") as f:
                        json.dump(memory_data, f, indent=2)
                    
                    print(f"☁️ Restored from cloud: {latest.name}")
                    return memory_data
            except Exception as e:
                print(f"⚠️ Cloud restore failed, trying local: {e}")
        
        # Fallback to local backups
        local_backups = sorted(self.LOCAL_BACKUP_DIR.glob("*.json.gz"), reverse=True)
        if local_backups:
            with gzip.open(local_backups[0], "rt") as f:
                memory_data = json.load(f)
            
            # Save to active location
            local_path = self._get_local_memory_path()
            with open(local_path, "w") as f:
                json.dump(memory_data, f, indent=2)
            
            print(f"💾 Restored from local: {local_backups[0].name}")
            return memory_data
        
        return None
    
    async def list_backups(self) -> list:
        """List all available backups."""
        backups = []
        
        # Cloud backups
        bucket = self._get_bucket()
        if bucket:
            try:
                for blob in bucket.list_blobs(prefix="backups/"):
                    backups.append({
                        "name": blob.name,
                        "location": "cloud",
                        "size": blob.size,
                        "created": blob.time_created.isoformat() if blob.time_created else None
                    })
            except Exception:
                pass
        
        # Local backups
        for f in self.LOCAL_BACKUP_DIR.glob("*.json.gz"):
            backups.append({
                "name": f.name,
                "location": "local",
                "size": f.stat().st_size,
                "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
        
        return sorted(backups, key=lambda b: b["name"], reverse=True)
    
    async def export_memories(self, output_path: Optional[Path] = None) -> Path:
        """Export all memories to a downloadable file."""
        local_path = self._get_local_memory_path()
        
        if not local_path.exists():
            raise FileNotFoundError("No memories to export")
        
        if output_path is None:
            output_path = ROOT / "exports" / f"seraph_memories_{datetime.now().strftime('%Y%m%d')}.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(local_path, "r") as src:
            data = json.load(src)
        
        with open(output_path, "w") as dst:
            json.dump(data, dst, indent=2)
        
        return output_path
    
    async def import_memories(self, input_path: Path, merge: bool = True) -> int:
        """
        Import memories from a file.
        
        Args:
            input_path: Path to JSON file
            merge: If True, merge with existing. If False, replace.
        
        Returns:
            Number of memories imported
        """
        with open(input_path, "r") as f:
            import_data = json.load(f)
        
        local_path = self._get_local_memory_path()
        
        if merge and local_path.exists():
            with open(local_path, "r") as f:
                existing = json.load(f)
            existing.update(import_data)
            final_data = existing
        else:
            final_data = import_data
        
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "w") as f:
            json.dump(final_data, f, indent=2)
        
        return len(import_data)


class AutoBackupDaemon:
    """Background daemon for automatic daily backups."""
    
    def __init__(self, backup: MemoryBackup):
        self.backup = backup
        self._running = False
        self._task = None
    
    async def start(self, interval_hours: int = 24):
        """Start the auto-backup daemon."""
        self._running = True
        
        while self._running:
            try:
                await self.backup.backup_now()
                print(f"✅ Auto-backup completed at {datetime.now().isoformat()}")
            except Exception as e:
                print(f"❌ Auto-backup failed: {e}")
            
            await asyncio.sleep(interval_hours * 3600)
    
    def stop(self):
        """Stop the daemon."""
        self._running = False


# Global instance
_backup: Optional[MemoryBackup] = None


def get_memory_backup() -> MemoryBackup:
    """Get or create global backup instance."""
    global _backup
    if _backup is None:
        _backup = MemoryBackup()
    return _backup


if __name__ == "__main__":
    import sys
    import asyncio
    
    async def run():
        if "--demo" in sys.argv:
            print("Memory Backup Demo")
            print("=" * 60)
            backup = MemoryBackup()
            print("\nCreating demo backup...")
            filename = await backup.backup_now({"test": "memory", "timestamp": datetime.now().isoformat()})
            print(f"Created: {filename}")
        else:
            # Real backup mode (for CronJob)
            print("🚀 Starting Seraph Memory Backup...")
            backup = MemoryBackup()
            try:
                filename = await backup.backup_now()  # Loads from file automatically
                if filename:
                    print(f"✅ Success: {filename}")
                else:
                    print("⚠️ Backup finished locally only (no GCS)")
            except Exception as e:
                print(f"❌ Backup Failed: {e}")
                sys.exit(1)
    
    asyncio.run(run())
