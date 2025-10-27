"""
Local development initialization.
"""

import subprocess
from pathlib import Path

from .config import ProjectConfig
from .manifest import ManifestManager


class InitManager:
    """Manages local development initialization."""
    
    def __init__(self, config: ProjectConfig, manifest: ManifestManager):
        self.config = config
        self.manifest = manifest
    
    def update_project_files(self) -> bool:
        """Update project name in configuration files."""
        try:
            print("Updating project name in configuration files...")
            
            # Update pyproject.toml
            if self.config.pyproject_file.exists():
                content = self.config.pyproject_file.read_text()
                content = content.replace(
                    'name = "bff-template"',
                    f'name = "{self.config.project_name}"'
                )
                self.config.pyproject_file.write_text(content)
            
            # Update makefile
            if self.config.makefile.exists():
                content = self.config.makefile.read_text()
                content = content.replace(
                    'name = "bff-template"',
                    f'name = "{self.config.project_name}"'
                )
                self.config.makefile.write_text(content)
            
            print("✓ Configuration files updated")
            return True
        except Exception as e:
            print(f"Error updating project files: {e}")
            return False
    
    def setup_frontend(self, skip_build: bool = False) -> bool:
        """Setup the frontend React application with Vite."""
        try:
            print("Setting up frontend with Vite...")
            
            # Create frontend directory if it doesn't exist
            self.config.frontend_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if frontend is already initialized
            package_json = self.config.frontend_dir / "package.json"
            if package_json.exists():
                print("Frontend already initialized")
                
                if not skip_build:
                    print("Building frontend...")
                    subprocess.run(
                        ["npm", "run", "build"],
                        cwd=self.config.frontend_dir,
                        check=True
                    )
            else:
                # Create package.json with Vite
                print("Creating Vite React app...")
                package_json_content = """{
  "name": "frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.4.2"
  }
}"""
                package_json.write_text(package_json_content)
                
                # Create vite.config.js
                vite_config = self.config.frontend_dir / "vite.config.js"
                vite_config_content = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
"""
                vite_config.write_text(vite_config_content)
                
                # Set up index.html at root - use existing one if available
                root_index = self.config.frontend_dir / "index.html"
                public_index = self.config.frontend_dir / "init" / "index.html"
                
                if public_index.exists() and not root_index.exists():
                    # Copy the custom index.html from init to root
                    root_index.write_text(public_index.read_text())
                elif not root_index.exists():
                    # Create a default index.html
                    default_index = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#0F172A" />
    <meta name="description" content="Modern web application powered by React" />
    <title>BFF Template</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""
                    root_index.write_text(default_index)
                
                # Create src directory and main entry point
                src_dir = self.config.frontend_dir / "src"
                src_dir.mkdir(exist_ok=True)
                
                main_jsx = src_dir / "main.jsx"
                main_jsx_content = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""
                main_jsx.write_text(main_jsx_content)
                
                # Create a basic App component
                app_jsx = src_dir / "App.jsx"
                app_jsx_content = """function App() {
  return (
    <div>
      <h1>Welcome to React + Vite</h1>
      <p>Your custom index.html is loaded!</p>
    </div>
  )
}

export default App
"""
                app_jsx.write_text(app_jsx_content)
                
                # Install dependencies
                print("Installing dependencies (this may take a few minutes)...")
                subprocess.run(
                    ["npm", "install"],
                    cwd=self.config.frontend_dir,
                    check=True
                )
                
                if not skip_build:
                    print("Building frontend...")
                    subprocess.run(
                        ["npm", "run", "build"],
                        cwd=self.config.frontend_dir,
                        check=True
                    )
            
            print("✓ Frontend setup complete")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error setting up frontend: {e}")
            return False
    
    def setup_backend(self) -> bool:
        """Setup the backend Python dependencies."""
        try:
            print("Setting up backend dependencies...")
            
            # Use uv to sync dependencies
            subprocess.run(["uv", "sync"], cwd=self.config.project_root, check=True)
            
            print("✓ Backend setup complete")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error setting up backend: {e}")
            return False
    
    def initialize(self, skip_frontend_build: bool = False) -> bool:
        """Run full local initialization."""
        print(f"Initializing project: {self.config.project_name}")
        print("")
        
        # Check if already initialized
        if self.manifest.get_state("initialized"):
            print("⚠️  Project is already initialized")
            response = input("Do you want to re-initialize? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                return False
        
        # Create .env file
        self.config.ensure_env_file()
        print("✓ .env file created")
        
        # Update configuration files
        if not self.update_project_files():
            return False
        
        # Setup frontend
        if not self.setup_frontend(skip_build=skip_frontend_build):
            return False
        
        # Setup backend
        if not self.setup_backend():
            return False
        
        # Update manifest
        self.manifest.update_state("initialized", True)
        self.manifest.update_config("project_name", self.config.project_name)
        self.manifest.log_operation("init", {"type": "local"})
        
        print("")
        print("=" * 50)
        print("Local development setup complete!")
        print("=" * 50)
        print("")
        print("Next steps:")
        print(f"  1. Set your Python interpreter to: .venv")
        print(f"  2. Run 'make local' to start the development server")
        print("")
        return True