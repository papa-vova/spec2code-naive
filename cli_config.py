#!/usr/bin/env python3
"""
CLI tool for managing LangChain agent configurations.
Validates configs and provides management commands.
"""
import argparse
import sys
from pathlib import Path
from config_system.config_loader import ConfigLoader, ConfigValidationError


def validate_command(args):
    """Validate all configuration files."""
    try:
        loader = ConfigLoader(args.config_root)
        loader.validate_all_configs()
        print("[OK] All configurations are valid!")
        return True
    except ConfigValidationError as e:
        print(f"[ERROR] Configuration validation failed: {e}")
        return False


def list_command(args):
    """List available models and agents."""
    try:
        loader = ConfigLoader(args.config_root)
        
        print("Available Models:")
        models = loader.list_available_models()
        for model in models:
            print(f"  - {model}")
        
        print("\nAvailable Agents:")
        agents = loader.list_available_agents()
        for agent in agents:
            print(f"  - {agent}")
            
        return True
    except ConfigValidationError as e:
        print(f"[ERROR] Error listing configs: {e}")
        return False


def check_command(args):
    """Check specific agent or model configuration."""
    try:
        loader = ConfigLoader(args.config_root)
        
        if args.model:
            model_config = loader.load_model_config(args.model)
            print(f"[OK] Model '{args.model}' configuration is valid:")
            print(f"  Type: {model_config._type}")
            print(f"  Model: {model_config.model_name}")
            print(f"  Temperature: {model_config.temperature}")
            
        if args.agent:
            agent_config = loader.load_agent_config(args.agent)
            prompts_config = loader.load_prompts_config(args.agent)
            print(f"[OK] Agent '{args.agent}' configuration is valid:")
            print(f"  Description: {agent_config.description}")
            print(f"  LLM: {agent_config.llm}")
            print(f"  Tools: {len(agent_config.tools)}")
            print(f"  Agent Type: {agent_config.agent_type}")
            print(f"  Prompt Templates: {len(prompts_config.prompt_templates)}")
            
        return True
    except ConfigValidationError as e:
        print(f"[ERROR] Configuration check failed: {e}")
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="LangChain Agent Configuration Management CLI"
    )
    parser.add_argument(
        "--config-root", 
        default="./config",
        help="Root directory for configuration files (default: ./config)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", 
        help="Validate all configuration files"
    )
    
    # List command
    list_parser = subparsers.add_parser(
        "list", 
        help="List available models and agents"
    )
    
    # Check command
    check_parser = subparsers.add_parser(
        "check", 
        help="Check specific agent or model configuration"
    )
    check_parser.add_argument("--model", help="Model name to check")
    check_parser.add_argument("--agent", help="Agent name to check")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        print("\n" + "="*60)
        print("AVAILABLE COMMANDS:")
        print("="*60)
        
        print("\nVALIDATE")
        print("   Validates all YAML configuration files for syntax and structure")
        print("   Usage: python cli_config.py validate")
        print("   Example: python cli_config.py validate")
        
        print("\nLIST")
        print("   Lists all available models and agents from configuration")
        print("   Usage: python cli_config.py list")
        print("   Example: python cli_config.py list")
        
        print("\nCHECK")
        print("   Checks and displays details for specific model or agent")
        print("   Usage: python cli_config.py check [--model MODEL_NAME] [--agent AGENT_NAME]")
        print("   Examples:")
        print("     python cli_config.py check --model openai_gpt4")
        print("     python cli_config.py check --agent plan_maker")
        print("     python cli_config.py check --model openai_gpt4 --agent plan_maker")
        
        print("\n" + "="*60)
        print("GLOBAL OPTIONS:")
        print("="*60)
        print("  --config-root PATH    Specify custom config directory (default: ./config)")
        print("  --help               Show this help message")
        
        print("\n" + "="*60)
        print("EXAMPLES:")
        print("="*60)
        print("  # Validate all configurations")
        print("  python cli_config.py validate")
        print("")
        print("  # List available resources")
        print("  python cli_config.py list")
        print("")
        print("  # Check specific configurations")
        print("  python cli_config.py check --agent plan_maker")
        print("  python cli_config.py check --model openai_gpt4")
        print("")
        print("  # Use custom config directory")
        print("  python cli_config.py --config-root ./my-configs validate")
        print("")
        sys.exit(1)
    
    # Execute command
    success = False
    if args.command == "validate":
        success = validate_command(args)
    elif args.command == "list":
        success = list_command(args)
    elif args.command == "check":
        if not args.model and not args.agent:
            print("[ERROR] Please specify --model or --agent to check")
            sys.exit(1)
        success = check_command(args)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
