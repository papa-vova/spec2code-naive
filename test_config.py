#!/usr/bin/env python3
"""
Configuration testing and validation tool for the agent pipeline system.

Provides CLI commands for:
- Validating all configuration files (syntax, schema, consistency)
- Listing available models and agents
- Checking specific agent or model configurations
- Ensuring config integrity before runtime execution

This tool focuses on STATIC configuration validation, while test_runtime.py
handles DYNAMIC runtime behavior testing.
"""
import argparse
import sys
from pathlib import Path
from config_system.config_loader import ConfigLoader, ConfigValidationError
from logging_config import setup_pipeline_logging, log_step_start, log_step_complete, log_error


def validate_command(args, logger):
    """Validate all configuration files."""
    try:
        log_step_start(logger, "ConfigValidator", "validation", "Starting configuration validation", {
            "config_root": args.config_root
        })
        
        loader = ConfigLoader(args.config_root)
        loader.validate_all_configs()
        
        log_step_complete(logger, "ConfigValidator", "validation", "Configuration validation completed", {
            "status": "success",
            "config_root": args.config_root
        })
        return True
    except ConfigValidationError as e:
        log_error(logger, f"Configuration validation failed: {str(e)}", "ConfigValidator", e)
        return False


def list_command(args, logger):
    """List available models and agents."""
    try:
        log_step_start(logger, "ConfigLister", "listing", "Listing available configurations", {
            "config_root": args.config_root
        })
        
        loader = ConfigLoader(args.config_root)
        models = loader.list_available_models()
        agents = loader.list_available_agents()
        
        log_step_complete(logger, "ConfigLister", "listing", "Configuration listing completed", {
            "models": models,
            "agents": agents,
            "models_count": len(models),
            "agents_count": len(agents)
        })
        return True
    except ConfigValidationError as e:
        log_error(logger, f"Error listing configurations: {str(e)}", "ConfigLister", e)
        return False


def check_command(args, logger):
    """Check specific agent or model configuration."""
    try:
        log_step_start(logger, "ConfigChecker", "checking", "Checking specific configurations", {
            "config_root": args.config_root,
            "model": args.model,
            "agent": args.agent
        })
        
        loader = ConfigLoader(args.config_root)
        check_results = {}
        
        if args.model:
            model_config = loader.load_model_config(args.model)
            check_results["model"] = {
                "name": args.model,
                "provider": model_config.provider,
                "model_name": model_config.model_name,
                "parameters": model_config.parameters,
                "status": "valid"
            }
            
        if args.agent:
            agent_config = loader.load_agent_config(args.agent)
            prompts_config = loader.load_prompts_config(args.agent)
            check_results["agent"] = {
                "name": args.agent,
                "description": agent_config.description,
                "llm": agent_config.llm,
                "tools_count": len(agent_config.tools),
                "agent_type": agent_config.agent_type,
                "prompt_templates_count": len(prompts_config.prompt_templates),
                "status": "valid"
            }
        
        log_step_complete(logger, "ConfigChecker", "checking", "Configuration check completed", check_results)
        return True
    except ConfigValidationError as e:
        log_error(logger, f"Configuration check failed: {str(e)}", "ConfigChecker", e)
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="LangChain Agent Configuration Management CLI",
        epilog="Examples:\n"
               "  %(prog)s validate                    # Validate all configurations\n"
               "  %(prog)s list                       # List available models and agents\n"
               "  %(prog)s check --agent plan_maker   # Check specific agent\n"
               "  %(prog)s --config-root ./my-configs validate  # Use custom config directory",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--config-root", 
        default="./config",
        help="Root directory for configuration files (default: ./config)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set the logging level (default: INFO)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging (equivalent to --log-level DEBUG)"
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
        sys.exit(1)
    
    # Set up logging
    pipeline_logger = setup_pipeline_logging(
        log_level=args.log_level,
        verbose=args.verbose
    )
    logger = pipeline_logger.get_logger("cli_config")
    
    # Execute command
    success = False
    try:
        if args.command == "validate":
            success = validate_command(args, logger)
        elif args.command == "list":
            success = list_command(args, logger)
        elif args.command == "check":
            if not args.model and not args.agent:
                log_error(logger, "Please specify --model or --agent to check", "CLI", None)
                sys.exit(1)
            success = check_command(args, logger)
    except Exception as e:
        log_error(logger, f"Unexpected error: {str(e)}", "CLI", e)
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
