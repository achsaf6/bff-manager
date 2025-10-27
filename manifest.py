"""
Manifest management for tracking project operations.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class ManifestManager:
    """Manages the project manifest file to track operations."""
    
    def __init__(self, manifest_path: str = "manager/.manifest"):
        self.manifest_path = Path(manifest_path)
        self._ensure_manifest_exists()
    
    def _ensure_manifest_exists(self) -> None:
        """Create manifest file if it doesn't exist."""
        if not self.manifest_path.exists():
            self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
            initial_data = {
                "created_at": datetime.now().isoformat(),
                "operations": [],
                "state": {
                    "initialized": False,
                    "deployed": False,
                    "docker_built": False,
                    "service_account_created": False,
                    "github_secrets_configured": False,
                },
                "config": {}
            }
            self._write_manifest(initial_data)
    
    def _read_manifest(self) -> Dict[str, Any]:
        """Read the manifest file."""
        with open(self.manifest_path, 'r') as f:
            return json.load(f)
    
    def _write_manifest(self, data: Dict[str, Any]) -> None:
        """Write data to the manifest file."""
        with open(self.manifest_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def log_operation(self, operation: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log an operation to the manifest."""
        manifest = self._read_manifest()
        
        operation_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "details": details or {}
        }
        
        manifest["operations"].append(operation_entry)
        self._write_manifest(manifest)
    
    def update_state(self, key: str, value: Any) -> None:
        """Update a state value in the manifest."""
        manifest = self._read_manifest()
        manifest["state"][key] = value
        self._write_manifest(manifest)
    
    def get_state(self, key: str) -> Any:
        """Get a state value from the manifest."""
        manifest = self._read_manifest()
        return manifest["state"].get(key)
    
    def update_config(self, key: str, value: Any) -> None:
        """Update a config value in the manifest."""
        manifest = self._read_manifest()
        manifest["config"][key] = value
        self._write_manifest(manifest)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a config value from the manifest."""
        manifest = self._read_manifest()
        return manifest["config"].get(key, default)
    
    def get_all_operations(self) -> list:
        """Get all logged operations."""
        manifest = self._read_manifest()
        return manifest["operations"]
    
    def get_all_state(self) -> Dict[str, Any]:
        """Get all state values."""
        manifest = self._read_manifest()
        return manifest["state"]
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all config values."""
        manifest = self._read_manifest()
        return manifest["config"]
    
    def reset_manifest(self) -> None:
        """Reset the manifest to initial state."""
        if self.manifest_path.exists():
            os.remove(self.manifest_path)
        self._ensure_manifest_exists()
