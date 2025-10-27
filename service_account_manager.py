"""
Service account management for Google Cloud Platform.
"""

import subprocess
from typing import List, Optional

from .config import ProjectConfig
from .manifest import ManifestManager


class ServiceAccountManager:
    """Manages GCP service account lifecycle and permissions."""
    
    def __init__(self, config: ProjectConfig, manifest: ManifestManager):
        self.config = config
        self.manifest = manifest
    
    def exists(self) -> bool:
        """Check if the service account already exists."""
        try:
            subprocess.run([
                "gcloud", "iam", "service-accounts", "describe",
                self.config.service_account_email,
                f"--project={self.config.gcp_project_id}"
            ], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def create(self) -> bool:
        """Create a GCP service account."""
        # Check if already exists
        if self.exists():
            print(f"✓ Service account already exists: {self.config.service_account_email}")
            self.manifest.log_operation("create_service_account", {
                "email": self.config.service_account_email,
                "status": "already_exists"
            })
            return True
        
        try:
            print(f"Creating service account: {self.config.service_account_email}")
            subprocess.run([
                "gcloud", "iam", "service-accounts", "create",
                f"{self.config.project_name}-sa",
                f"--display-name={self.config.project_name} Service Account",
                f"--project={self.config.gcp_project_id}"
            ], check=True)
            
            self.manifest.log_operation("create_service_account", {
                "email": self.config.service_account_email
            })
            print("✓ Service account created successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Error creating service account: {e}")
            return False
    
    def delete(self) -> bool:
        """Delete the GCP service account."""
        try:
            print(f"Deleting service account: {self.config.service_account_email}")
            subprocess.run([
                "gcloud", "iam", "service-accounts", "delete",
                self.config.service_account_email,
                "--quiet"
            ], check=False)
            
            self.manifest.log_operation("delete_service_account", {
                "email": self.config.service_account_email
            })
            print("✓ Service account deleted successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Error deleting service account: {e}")
            return False
    
    def add_permissions(self, roles: Optional[List[str]] = None) -> bool:
        """Add IAM roles to the service account."""
        if roles is None:
            roles = [
                "roles/artifactregistry.writer",
                "roles/run.developer",
                "roles/iam.serviceAccountUser"
            ]
        
        try:
            for role in roles:
                print(f"Adding role: {role}")
                subprocess.run([
                    "gcloud", "projects", "add-iam-policy-binding",
                    self.config.gcp_project_id,
                    f"--member=serviceAccount:{self.config.service_account_email}",
                    f"--role={role}"
                ], check=True)
            
            self.manifest.log_operation("add_permissions", {
                "email": self.config.service_account_email,
                "roles": roles
            })
            print("✓ Permissions added successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Error adding permissions: {e}")
            return False
    
    def remove_permissions(self, roles: Optional[List[str]] = None) -> bool:
        """Remove IAM roles from the service account."""
        if roles is None:
            roles = [
                "roles/run.admin",
                "roles/iam.serviceAccountUser",
                "roles/storage.admin",
                "roles/artifactregistry.admin",
                "roles/run.developer"
            ]
        
        try:
            for role in roles:
                print(f"Removing role: {role}")
                subprocess.run([
                    "gcloud", "projects", "remove-iam-policy-binding",
                    self.config.gcp_project_id,
                    f"--member=serviceAccount:{self.config.service_account_email}",
                    f"--role={role}",
                    "--quiet"
                ], check=True)
            
            self.manifest.log_operation("remove_permissions", {
                "email": self.config.service_account_email,
                "roles": roles
            })
            print("✓ Permissions removed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Error removing permissions: {e}")
            return False
    
    def create_key(self, key_file: str = "sa-key.json") -> bool:
        """Create a service account key."""
        try:
            print(f"Creating service account key: {key_file}")
            subprocess.run([
                "gcloud", "iam", "service-accounts", "keys", "create",
                key_file,
                f"--iam-account={self.config.service_account_email}"
            ], check=True)
            
            self.manifest.log_operation("create_key", {
                "email": self.config.service_account_email,
                "key_file": key_file
            })
            print("✓ Service account key created successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Error creating service account key: {e}")
            return False
    
    def setup(self) -> bool:
        """Setup service account with default permissions."""
        print("")
        print("Setting up service account...")
        
        # Create service account
        if not self.create():
            return False
        
        # Add permissions
        if not self.add_permissions():
            return False
        
        self.manifest.update_state("service_account_created", True)
        return True
