"""
Project management CLI tool.

This module provides a comprehensive CLI for managing the project lifecycle:
- Initialization (local setup)
- Deployment (GCP Cloud Run)
- Cleanup (teardown)
- Status tracking via manifest
"""

from .clean import CleanManager
from .config import ProjectConfig
from .deploy import DeployManager
from .docker_utils import DockerManager
from .gcp_utils import GCPManager
from .github_utils import GitHubManager
from .init import InitManager
from .manifest import ManifestManager

__all__ = [
    "CleanManager",
    "ProjectConfig",
    "DeployManager",
    "DockerManager",
    "GCPManager",
    "GitHubManager",
    "InitManager",
    "ManifestManager",
]
