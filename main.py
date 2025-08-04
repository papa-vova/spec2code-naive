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
from core.run_manager import RunManager
from config_system.config_loader import ConfigLoader
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
            
            # Initialize run manager based on pipeline settings
            pipeline_config = self.orchestrator.pipeline_config
            self.run_manager = RunManager(
                runs_directory=pipeline_config.settings.runs_directory,
                create_artifacts=pipeline_config.settings.create_run_artifacts
            )
        except Exception as e:
            raise PipelineError(f"Failed to initialize orchestrator: {e}")
    
    def set_logger(self, logger):
        """Set the logger for this pipeline instance."""
        self.logger = logger
        # Also set logger on orchestrator and run manager
        if hasattr(self, 'orchestrator'):
            self.orchestrator.set_logger(logger)
        if hasattr(self, 'run_manager'):
            self.run_manager.set_logger(logger)
    
    def run_pipeline(self, input_description: str, input_file: str = None) -> Dict[str, Any]:
        """
        Execute the pipeline using the config-driven orchestrator.
        
        Args:
            input_description: File content that was read from the input file
            input_file: Source file path (for metadata tracking)
            
        Returns:
            Dictionary containing the orchestrator result with run_id
        """
        # Generate unique run ID
        run_id = self.run_manager.generate_run_id()
        
        # Prepare input data for orchestrator with proper structure
        input_data = {
            "content": input_description,
            "source": os.path.basename(input_file),
            "size": len(input_description)
        }
        
        # Execute pipeline using orchestrator
        result = self.orchestrator.execute_pipeline(input_data)
        
        # Add run ID to result
        result["run_id"] = run_id
        
        # Save run artifacts if enabled
        if self.run_manager.create_artifacts:
            self.run_manager.save_run_result(
                run_id=run_id,
                result=result,
                config_root=self.config_root,
                input_file=input_file
            )
            
            if self.logger:
                log_debug(self.logger, f"Run artifacts saved for run ID: {run_id}", "Pipeline", {
                    "run_id": run_id,
                    "runs_directory": self.run_manager.runs_directory
                })
        
        return result


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
        
        # Load pipeline configuration early to get the correct log level
        config_loader = ConfigLoader(args.config_root)
        pipeline_config = config_loader.load_pipeline_config()
        
        # Set up logging using pipeline's log_level setting (not command line)
        pipeline_logger = setup_pipeline_logging(
            log_level=pipeline_config.settings.log_level,
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
        results = pipeline.run_pipeline(input_description, input_file)
        
        # TODO: Generate artifacts (files, reports, etc.) instead of console output
        # For now, the application runs silently and relies on JSON logs for monitoring
        
        # Log completion with run ID
        run_id = results.get('run_id', 'unknown')
        logger.info("Pipeline execution completed successfully", extra={
            "component": "Main",
            "data": {
                "execution_successful": results.get('execution_successful', True),
                "pipeline_name": results.get('pipeline_name', 'unknown'),
                "run_id": run_id
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
