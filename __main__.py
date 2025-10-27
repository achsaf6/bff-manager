"""
CLI entry point for the project manager.
"""

import argparse
import json
import sys

from .clean import CleanManager
from .config import ProjectConfig
from .deploy import DeployManager
from .init import InitManager
from .manifest import ManifestManager
from .service_account_manager import ServiceAccountManager


def cmd_init(args, config: ProjectConfig, manifest: ManifestManager) -> int:
    """Handle init command."""
    init_manager = InitManager(config, manifest)
    success = init_manager.initialize(skip_frontend_build=args.skip_frontend_build)
    return 0 if success else 1


def cmd_deploy(args, config: ProjectConfig, manifest: ManifestManager) -> int:
    """Handle deploy command."""
    deploy_manager = DeployManager(config, manifest)
    success = deploy_manager.deploy(region=args.region)
    return 0 if success else 1


def cmd_clean(args, config: ProjectConfig, manifest: ManifestManager) -> int:
    """Handle clean command."""
    clean_manager = CleanManager(config, manifest)
    success = clean_manager.clean(skip_local=args.skip_local)
    return 0 if success else 1


def cmd_status(args, config: ProjectConfig, manifest: ManifestManager) -> int:
    """Handle status command."""
    print("")
    print("=" * 60)
    print(f"Project Status: {config.project_name}")
    print("=" * 60)
    print("")
    
    state = manifest.get_all_state()
    print("State:")
    for key, value in state.items():
        status = "✓" if value else "✗"
        print(f"  {status} {key}: {value}")
    
    print("")
    
    config_data = manifest.get_all_config()
    if config_data:
        print("Configuration:")
        for key, value in config_data.items():
            print(f"  {key}: {value}")
        print("")
    
    if args.verbose:
        operations = manifest.get_all_operations()
        if operations:
            print(f"Operations History ({len(operations)} total):")
            for op in operations[-10:]:  # Show last 10
                print(f"  [{op['timestamp']}] {op['operation']}")
                if op.get('details'):
                    print(f"    Details: {op['details']}")
            print("")
    
    return 0


def cmd_history(args, config: ProjectConfig, manifest: ManifestManager) -> int:
    """Handle history command."""
    operations = manifest.get_all_operations()
    
    if not operations:
        print("No operations in history")
        return 0
    
    print("")
    print("=" * 60)
    print(f"Operation History: {config.project_name}")
    print("=" * 60)
    print("")
    
    # Show last N operations
    limit = args.limit or len(operations)
    for op in operations[-limit:]:
        print(f"[{op['timestamp']}] {op['operation']}")
        if op.get('details'):
            if args.json:
                print(f"  {json.dumps(op['details'], indent=2)}")
            else:
                for key, value in op['details'].items():
                    print(f"  {key}: {value}")
        print("")
    
    return 0


def cmd_config(args, config: ProjectConfig, manifest: ManifestManager) -> int:
    """Handle config command."""
    if args.get:
        value = manifest.get_config(args.get)
        if value is not None:
            print(value)
        else:
            print(f"Config key '{args.get}' not found", file=sys.stderr)
            return 1
    elif args.set:
        key, value = args.set.split('=', 1)
        manifest.update_config(key.strip(), value.strip())
        print(f"✓ Set {key} = {value}")
    elif args.list:
        config_data = manifest.get_all_config()
        print("")
        print("Current Configuration:")
        for key, value in config_data.items():
            print(f"  {key}: {value}")
        print("")
    else:
        print("Use --get, --set, or --list to manage configuration", file=sys.stderr)
        return 1
    
    return 0


def cmd_service_account(args, config: ProjectConfig, manifest: ManifestManager) -> int:
    """Handle service account command."""
    sa_manager = ServiceAccountManager(config, manifest)
    
    if args.action == 'create':
        success = sa_manager.create()
        return 0 if success else 1
    
    elif args.action == 'delete':
        response = input(f"Are you sure you want to delete the service account '{config.service_account_email}'? (yes/N): ")
        if response.lower() != 'yes':
            print("Aborted")
            return 1
        success = sa_manager.delete()
        return 0 if success else 1
    
    elif args.action == 'add-permissions':
        roles = None
        if args.roles:
            roles = args.roles
        success = sa_manager.add_permissions(roles)
        return 0 if success else 1
    
    elif args.action == 'remove-permissions':
        roles = None
        if args.roles:
            roles = args.roles
        response = input(f"Are you sure you want to remove permissions from '{config.service_account_email}'? (yes/N): ")
        if response.lower() != 'yes':
            print("Aborted")
            return 1
        success = sa_manager.remove_permissions(roles)
        return 0 if success else 1
    
    else:
        print(f"Unknown action: {args.action}", file=sys.stderr)
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Project Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m manager init                    # Initialize local development
  python -m manager deploy                  # Deploy to GCP
  python -m manager deploy --region us-east1  # Deploy to specific region
  python -m manager status                  # Show project status
  python -m manager status -v               # Show detailed status
  python -m manager history                 # Show operation history
  python -m manager clean                   # Clean up all resources
  python -m manager clean --skip-local      # Clean GCP/GitHub but keep local files
  python -m manager config --list           # List all config values
  python -m manager config --get region     # Get a config value
  python -m manager config --set key=value  # Set a config value
  python -m manager service-account create  # Create service account
  python -m manager service-account delete  # Delete service account
  python -m manager service-account add-permissions  # Add default permissions
  python -m manager service-account add-permissions --roles roles/run.admin roles/storage.admin
  python -m manager service-account remove-permissions  # Remove default permissions
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Init command
    parser_init = subparsers.add_parser('init', help='Initialize local development')
    parser_init.add_argument(
        '--skip-frontend-build',
        action='store_true',
        help='Skip building the frontend after initialization'
    )
    
    # Deploy command
    parser_deploy = subparsers.add_parser('deploy', help='Deploy to Google Cloud Platform')
    parser_deploy.add_argument(
        '--region',
        type=str,
        help='GCP region for deployment (default: europe-west4)'
    )
    
    # Clean command
    parser_clean = subparsers.add_parser('clean', help='Clean up project resources')
    parser_clean.add_argument(
        '--skip-local',
        action='store_true',
        help='Skip deleting local files (only clean GCP and GitHub)'
    )
    
    # Status command
    parser_status = subparsers.add_parser('status', help='Show project status')
    parser_status.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed status including recent operations'
    )
    
    # History command
    parser_history = subparsers.add_parser('history', help='Show operation history')
    parser_history.add_argument(
        '--limit',
        type=int,
        help='Limit number of operations to show'
    )
    parser_history.add_argument(
        '--json',
        action='store_true',
        help='Show details in JSON format'
    )
    
    # Config command
    parser_config = subparsers.add_parser('config', help='Manage configuration')
    config_group = parser_config.add_mutually_exclusive_group()
    config_group.add_argument(
        '--get',
        type=str,
        help='Get a configuration value'
    )
    config_group.add_argument(
        '--set',
        type=str,
        help='Set a configuration value (format: key=value)'
    )
    config_group.add_argument(
        '--list',
        action='store_true',
        help='List all configuration values'
    )
    
    # Service account command
    parser_sa = subparsers.add_parser('service-account', help='Manage GCP service account')
    sa_subparsers = parser_sa.add_subparsers(dest='action', help='Service account action')
    sa_subparsers.required = True
    
    sa_create = sa_subparsers.add_parser('create', help='Create a new service account')
    
    sa_delete = sa_subparsers.add_parser('delete', help='Delete the service account')
    
    sa_add = sa_subparsers.add_parser('add-permissions', help='Add IAM roles to service account')
    sa_add.add_argument(
        '--roles',
        nargs='+',
        help='Specific roles to add (default: standard deployment roles)'
    )
    
    sa_remove = sa_subparsers.add_parser('remove-permissions', help='Remove IAM roles from service account')
    sa_remove.add_argument(
        '--roles',
        nargs='+',
        help='Specific roles to remove (default: standard deployment roles)'
    )

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize configuration and manifest
    config = ProjectConfig()
    manifest = ManifestManager()
    
    # Route to appropriate command handler
    commands = {
        'init': cmd_init,
        'deploy': cmd_deploy,
        'clean': cmd_clean,
        'status': cmd_status,
        'history': cmd_history,
        'config': cmd_config,
        'service-account': cmd_service_account,
    }
    
    handler = commands.get(args.command)
    if handler:
        try:
            return handler(args, config, manifest)
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user")
            return 130
        except Exception as e:
            print(f"\nError: {e}", file=sys.stderr)
            return 1
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

