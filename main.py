"""
Main entry point for the skeleton LangChain application.
Implements steps 4-6 of the analysis branch.
"""
import os
import sys
import argparse
import time
from typing import List, Dict, Any
from config_system.config_loader import ConfigLoader, ConfigValidationError
from config_system.agent_factory import AgentFactory
from exceptions import (
    PipelineError, InputError, FileNotFoundError, EmptyFileError,
    PlanGenerationError, ReportGenerationError, MetricComparisonError
)
from logging_config import setup_pipeline_logging, log_step_start, log_step_complete, log_debug, log_error


class Pipeline:
    """Main pipeline for processing requirements and generating plans."""
    
    def __init__(self, config_root: str = "./config", dry_run: bool = False):
        """Initialize pipeline with config-driven agent creation."""
        self.config_root = config_root
        self.dry_run = dry_run
        
        # Initialize config loader and agent factory
        self.config_loader = ConfigLoader(config_root)
        self.agent_factory = AgentFactory(self.config_loader)
        
        # Declarative list of required agents
        required_agents = [
            "plan_maker",
            "plan_critique_generator", 
            "plan_critique_comparator"
        ]
        
        # Create all agents from the list
        try:
            self.agents = self.agent_factory.create_agents(required_agents, dry_run)
            
            # Access agents cleanly
            self.plan_maker = self.agents['plan_maker']
            self.report_generator = self.agents['plan_critique_generator']  # Single instance for now
            self.comparator = self.agents['plan_critique_comparator']
            
        except ConfigValidationError as e:
            if dry_run:
                logger.warning(f"Config validation failed in dry-run mode: {e}")
                # In dry-run mode, we can still proceed with minimal setup
                self.plan_maker = None
                self.report_generator = None
                self.comparator = None
            else:
                raise PipelineError(f"Failed to initialize agents: {e}")
        
        # Pipeline settings
        self.n_reports = 1  # Single report generator for now
        self.logger = None
    
    def set_logger(self, logger):
        """Set the logger for this pipeline instance."""
        self.logger = logger
    
    def run_pipeline(self, input_description: str) -> Dict[str, Any]:
        """
        Execute the complete pipeline.
        
        Args:
            input_description: Free text description of what should be done
            
        Returns:
            Dictionary containing all results and final metric decision
            
        Raises:
            PlanGenerationError: If plan creation fails
            ReportGenerationError: If report generation fails
            MetricComparisonError: If metric comparison fails
        """
        try:
            # Log pipeline start
            if self.logger:
                log_step_start(self.logger, "Pipeline", "execution", "Starting pipeline execution", {
                    "input_length": len(input_description),
                    "input_preview": input_description[:100] + ("..." if len(input_description) > 100 else "")
                })
            
            # Step: Make a plan of implementing the whole set of steps
            plan_start_time = time.time()
            try:
                if self.logger:
                    log_step_start(self.logger, "PlanMaker", "plan_generation", "Creating implementation plan")
                
                implementation_plan = self.plan_maker.create_plan(input_description)
                
                plan_duration = (time.time() - plan_start_time) * 1000
                if self.logger:
                    log_step_complete(self.logger, "PlanMaker", "plan_generation", "Plan creation completed", {
                        "plan_length": len(implementation_plan)
                    }, plan_duration)
                    
            except Exception as e:
                if self.logger:
                    log_error(self.logger, f"Plan generation failed: {str(e)}", "PlanMaker", e)
                raise PlanGenerationError(f"Failed to create implementation plan: {str(e)}")
            
            # Step: Generate critical report on the plan's consistency
            reports_start_time = time.time()
            reports = []
            try:
                if self.logger:
                    log_step_start(self.logger, "ReportGenerator", "report_generation", 
                                 "Generating critical report on plan")
                
                # Generate single report for now
                report_start_time = time.time()
                
                if self.logger:
                    log_debug(self.logger, "Generating critical report", "ReportGenerator", {
                            "report_type": self.report_generator.report_type.value
                        })
                    
                report = self.report_generator.generate_report(implementation_plan)
                reports.append(report)
                
                report_duration = (time.time() - report_start_time) * 1000
                if self.logger:
                    log_debug(self.logger, "Report completed", "ReportGenerator", {
                        "score": report['score'],
                        "type": report['type'],
                        "duration_ms": report_duration
                    })
                        
                reports_duration = (time.time() - reports_start_time) * 1000
                if self.logger:
                    log_step_complete(self.logger, "ReportGenerator", "report_generation", 
                                    "All reports generated", {
                                        "reports_count": len(reports)
                                    }, reports_duration)
                    
            except Exception as e:
                if self.logger:
                    log_error(self.logger, f"Report generation failed: {str(e)}", "ReportGenerator", e)
                raise ReportGenerationError(f"Failed to generate reports: {str(e)}")
            
            # Step: Do an independent comparison of the reports and generate a metric
            comparison_start_time = time.time()
            try:
                if self.logger:
                    log_step_start(self.logger, "MetricComparator", "metric_comparison", 
                                 "Comparing reports and generating metric")
                
                comparison_result = self.comparator.compare_reports(reports)
                
                comparison_duration = (time.time() - comparison_start_time) * 1000
                if self.logger:
                    log_step_complete(self.logger, "MetricComparator", "metric_comparison", 
                                    "Metric comparison completed", {
                                        "metric": comparison_result['metric'],
                                        "consistency": comparison_result['consistency'],
                                        "status": comparison_result['status']
                                    }, comparison_duration)
                    
            except Exception as e:
                if self.logger:
                    log_error(self.logger, f"Metric comparison failed: {str(e)}", "MetricComparator", e)
                raise MetricComparisonError(f"Failed to compare reports: {str(e)}")
            
            # Check if metric is OK (decision point from flow)
            metric_ok = self.comparator.is_metric_ok(comparison_result)
            
            # Log final decision
            if self.logger:
                next_action = "loop_back" if not metric_ok else "proceed"
                log_step_complete(self.logger, "Pipeline", "execution", "Pipeline execution completed", {
                    "metric_ok": metric_ok,
                    "next_action": next_action,
                    "final_metric": comparison_result['metric'],
                    "final_status": comparison_result['status']
                })
            
            return {
                "input_description": input_description,
                "implementation_plan": implementation_plan,
                "reports": reports,
                "comparison_result": comparison_result,
                "metric_ok": metric_ok,
                "next_action": "loop_back" if not metric_ok else "proceed"
            }
            
        except (PlanGenerationError, ReportGenerationError, MetricComparisonError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Catch any unexpected errors and wrap them
            raise PipelineError(f"Unexpected error in pipeline execution: {str(e)}")


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
            "data": {"pipeline_type": "NAIVE_FLOW"}
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
                "execution_successful": True,
                "final_metric": results['comparison_result']['metric'],
                "metric_ok": results['metric_ok']
            }
        })
        
    except (FileNotFoundError, EmptyFileError, InputError) as e:
        if 'logger' in locals():
            log_error(logger, f"Input error: {str(e)}", "Main", e)
        else:
            # Fallback if logger not set up yet
            print(f"Input Error: {e}", file=sys.stderr)
        sys.exit(1)
    except (PlanGenerationError, ReportGenerationError, MetricComparisonError) as e:
        if 'logger' in locals():
            log_error(logger, f"Pipeline error: {str(e)}", "Main", e)
        else:
            print(f"Pipeline Error: {e}", file=sys.stderr)
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
