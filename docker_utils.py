"""
Docker utilities for building and managing containers.
"""

import subprocess
from typing import Optional

from .config import ProjectConfig


class DockerManager:
    """Manages Docker operations."""
    
    def __init__(self, config: ProjectConfig):
        self.config = config
    
    def start_colima(self) -> bool:
        """Start Colima Docker runtime."""
        try:
            print("Starting Colima...")
            subprocess.run(["colima", "start"], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error starting Colima: {e}")
            return False
    
    def stop_colima(self) -> bool:
        """Stop Colima Docker runtime."""
        try:
            print("Stopping Colima...")
            subprocess.run(["colima", "stop"], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error stopping Colima: {e}")
            return False
    
    def build_image(self) -> bool:
        """Build Docker image."""
        try:
            print(f"Building Docker image: {self.config.image_url}")
            subprocess.run(
                ["docker", "build", "-t", self.config.image_url, "."],
                check=True,
                cwd=self.config.project_root
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error building Docker image: {e}")
            return False
    
    def push_image(self) -> bool:
        """Push Docker image to registry."""
        try:
            print(f"Pushing Docker image: {self.config.image_url}")
            subprocess.run(["docker", "push", self.config.image_url], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error pushing Docker image: {e}")
            return False
    
    def stop_container(self, image_url: Optional[str] = None) -> bool:
        """Stop running containers for the image."""
        image_url = image_url or self.config.image_url
        try:
            # Get container IDs
            result = subprocess.run(
                ["docker", "ps", "-a", "-q", "--filter", f"ancestor={image_url}"],
                capture_output=True,
                text=True
            )
            
            container_ids = result.stdout.strip().split('\n')
            container_ids = [cid for cid in container_ids if cid]
            
            if container_ids:
                print(f"Stopping containers: {', '.join(container_ids)}")
                subprocess.run(["docker", "stop"] + container_ids, check=False)
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error stopping containers: {e}")
            return False
    
    def remove_image(self, image_url: Optional[str] = None, force: bool = True) -> bool:
        """Remove Docker image."""
        image_url = image_url or self.config.image_url
        try:
            cmd = ["docker", "rmi", image_url]
            if force:
                cmd.append("--force")
            
            subprocess.run(cmd, check=False, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error removing Docker image: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up Docker resources for this project."""
        self.stop_container()
        self.remove_image()
        return True
