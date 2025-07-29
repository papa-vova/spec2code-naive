"""
Main entry point for the skeleton LangChain application.
Implements steps 4-6 of the analysis branch.
"""
import os
import sys
import argparse
import time
from typing import List, Dict, Any
from core.orchestrator import Orchestrator
from exceptions import PipelineError, InputError, FileNotFoundError, EmptyFileError
from logging_config import setup_pipeline_logging, log_step_start, log_step_complete, log_debug, log_error


class Pipeline:
    """Main pipeline for processing requirements and generating plans."""
    
    def __init__(self, config_root: str = "./config", dry_run: bool = False):
        """Initialize pipeline with config-driven orchestrator."""
        self.config_root = config_root
        self.dry_run = dry_run
        self.logger = None
        
        # Initialize orchestrator
        try:
            self.orchestrator = Orchestrator(config_root, dry_run)
        except Exception as e:
            raise PipelineError(f"Failed to initialize orchestrator: {e}")
    
    def set_logger(self, logger):
        """Set the logger for this pipeline instance."""
        self.logger = logger
        # Also set logger on orchestrator
        if hasattr(self, 'orchestrator'):
            self.orchestrator.set_logger(logger)
    
    def run_pipeline(self, input_description: str) -> Dict[str, Any]:
        """
        Execute the pipeline using the config-driven orchestrator.
        
        Args:
            input_description: Free text description of what should be done
            
        Returns:
            Dictionary containing the orchestrator result
        """
        # Prepare input data for orchestrator
        input_data = {"description": input_description}
        
        # Execute pipeline using orchestrator
        return self.orchestrator.execute_pipeline(input_data)


def main():
    """Main function to run the pipeline with CLI arguments."""
    
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(
            description='SPEC2CODE Pipeline - Generate implementation plans from feature descriptions'
        )
        parser.add_argument(
            '-i', '--input',
            required=True,
            help='Input file containing the feature description'
        )
        parser.add_argument(
            '--log-level',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            help='Set the logging level (default: INFO, can also be set via SPEC2CODE_LOG_LEVEL env var)'
        )
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose logging (equivalent to --log-level DEBUG)'
        )
        parser.add_argument(
            '--config-root',
            default='./config',
            help='Path to configuration directory (default: ./config)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run pipeline with dummy responses (no LLM required)'
        )
        
        args = parser.parse_args()
        input_file = args.input
        
        # Set up logging
        pipeline_logger = setup_pipeline_logging(
            log_level=args.log_level,
            verbose=args.verbose
        )
        logger = pipeline_logger.get_logger("main")
        
        # Check if input file exists
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file '{input_file}' not found.")
        
        # Read input from file
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                input_description = f.read().strip()
            logger.info(f"Reading input from file: {input_file}", extra={
                "component": "FileReader",
                "data": {"file_path": input_file, "file_size": len(input_description)}
            })
        except IOError as e:
            log_error(logger, f"Error reading file '{input_file}': {e}", "FileReader", e)
            raise InputError(f"Error reading file '{input_file}': {e}")
        
        if not input_description:
            raise EmptyFileError(f"Input file '{input_file}' is empty.")
        
        logger.info("Starting SPEC2CODE pipeline execution", extra={
            "component": "Main",
            "data": {"pipeline_type": "CONFIG_DRIVEN"}
        })
        
        # Initialize and run pipeline
        pipeline = Pipeline(config_root=args.config_root, dry_run=args.dry_run)
        pipeline.set_logger(logger)
        
        # Log dry-run mode if active
        if args.dry_run:
            logger.info("Running in DRY-RUN mode - using dummy responses (no LLM required)", extra={
                "component": "Main",
                "data": {"mode": "dry_run"}
            })
        results = pipeline.run_pipeline(input_description)
        
        # TODO: Generate artifacts (files, reports, etc.) instead of console output
        # For now, the application runs silently and relies on JSON logs for monitoring
        
        # Log completion
        logger.info("Pipeline execution completed successfully", extra={
            "component": "Main",
            "data": {
                "execution_successful": results.get('execution_successful', True),
                "pipeline_name": results.get('pipeline_name', 'unknown')
            }
        })
        
    except (FileNotFoundError, EmptyFileError, InputError) as e:
        if 'logger' in locals():
            log_error(logger, f"Input error: {str(e)}", "Main", e)
        else:
            # Fallback if logger not set up yet
            print(f"Input Error: {e}", file=sys.stderr)
        sys.exit(1)

    except PipelineError as e:
        if 'logger' in locals():
            log_error(logger, f"Pipeline error: {str(e)}", "Main", e)
        else:
            print(f"Pipeline Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        if 'logger' in locals():
            log_error(logger, f"Unexpected error: {str(e)}", "Main", e)
        else:
            print(f"Unexpected Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
