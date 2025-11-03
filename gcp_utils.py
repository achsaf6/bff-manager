"""
Google Cloud Platform utilities.
"""

import subprocess
from typing import List, Optional

from .config import ProjectConfig


class GCPManager:
    """Manages Google Cloud Platform operations."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
    
    def create_service_account(self) -> bool:
        """Create a GCP service account."""
        try:
            print(f"Creating service account: {self.config.service_account_email}")
            subprocess.run([
                "gcloud", "iam", "service-accounts", "create",
                f"{self.config.project_name}-sa",
                f"--display-name={self.config.project_name} Service Account",
                f"--project={self.config.gcp_project_id}"
            ], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating service account: {e}")
            return False
    
    def grant_iam_roles(self, roles: Optional[List[str]] = None) -> bool:
        """Grant IAM roles to the service account."""
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
                print(f"Granting role: {role}")
                subprocess.run([
                    "gcloud", "projects", "add-iam-policy-binding",
                    self.config.gcp_project_id,
                    f"--member=serviceAccount:{self.config.service_account_email}",
                    f"--role={role}"
                ], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error granting IAM roles: {e}")
            return False
    
    def delete_service_account(self) -> bool:
        """Delete the GCP service account."""
        try:
            print(f"Deleting service account: {self.config.service_account_email}")
            subprocess.run([
                "gcloud", "iam", "service-accounts", "delete",
                self.config.service_account_email,
                "--quiet"
            ], check=False)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error deleting service account: {e}")
            return False
    
    def create_service_account_key(self, key_file: str = "sa-key.json") -> bool:
        """Create a service account key."""
        try:
            print(f"Creating service account key: {key_file}")
            subprocess.run([
                "gcloud", "iam", "service-accounts", "keys", "create",
                key_file,
                f"--iam-account={self.config.service_account_email}"
            ], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating service account key: {e}")
            return False
    
    def deploy_to_cloud_run(self, region: Optional[str] = None) -> bool:
        """Deploy to Cloud Run."""
        region = region or self.config.default_region
        
        try:
            print(f"Deploying to Cloud Run in region: {region}")
            subprocess.run([
                "gcloud", "run", "deploy", self.config.project_name,
                f"--image={self.config.image_url}",
                f"--region={region}",
                "--platform=managed",
                f"--project={self.config.gcp_project_id}",
                "--ingress=internal-and-cloud-load-balancing",
                "--allow-unauthenticated"
            ], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error deploying to Cloud Run: {e}")
            return False
    
    def delete_cloud_run_service(self, region: Optional[str] = None) -> bool:
        """Delete Cloud Run service."""
        region = region or self.config.default_region
        
        try:
            print(f"Deleting Cloud Run service: {self.config.project_name}")
            subprocess.run([
                "gcloud", "run", "services", "delete",
                self.config.project_name,
                f"--region={region}",
                f"--project={self.config.gcp_project_id}",
                "--quiet"
            ], check=False)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error deleting Cloud Run service: {e}")
            return False

