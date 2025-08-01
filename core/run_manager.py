"""
Run management system for pipeline executions.
Handles unique ID generation, run storage, and metadata management.
"""
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from logging_config import log_debug, log_error


class RunManager:
    """Manages pipeline run storage and retrieval."""
    
    def __init__(self, runs_directory: str = "runs", create_artifacts: bool = True):
        """
        Initialize run manager.
        
        Args:
            runs_directory: Directory to store run artifacts
            create_artifacts: Whether to create run artifacts
        """
        self.runs_directory = Path(runs_directory)
        self.create_artifacts = create_artifacts
        self.logger = None
        
        if self.create_artifacts:
            # Ensure runs directory exists
            self.runs_directory.mkdir(exist_ok=True)
    
    def set_logger(self, logger):
        """Set logger for this run manager instance."""
        self.logger = logger
    
    def generate_run_id(self) -> str:
        """
        Generate a unique run ID.
        
        Returns:
            Unique run ID string
        """
        # Use timestamp + short UUID for readability and uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        run_id = f"{timestamp}_{short_uuid}"
        
        # Ensure uniqueness by checking if directory already exists
        run_dir = self.runs_directory / run_id
        counter = 1
        original_run_id = run_id
        
        while run_dir.exists():
            run_id = f"{original_run_id}_{counter}"
            run_dir = self.runs_directory / run_id
            counter += 1
        
        if self.logger:
            log_debug(self.logger, f"Generated run ID: {run_id}", "RunManager", {
                "run_id": run_id,
                "runs_directory": str(self.runs_directory)
            })
        
        return run_id
    
    def create_run_directory(self, run_id: str) -> Path:
        """
        Create directory for a specific run.
        
        Args:
            run_id: Unique run identifier
            
        Returns:
            Path to the created run directory
        """
        if not self.create_artifacts:
            return None
        
        run_dir = self.runs_directory / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        if self.logger:
            log_debug(self.logger, f"Created run directory: {run_dir}", "RunManager", {
                "run_id": run_id,
                "run_directory": str(run_dir)
            })
        
        return run_dir
    
    def save_run_result(self, run_id: str, result: Dict[str, Any], 
                       config_root: str, input_file: str = None) -> Optional[Path]:
        """
        Save pipeline result and metadata for a run.
        
        Args:
            run_id: Unique run identifier
            result: Pipeline execution result (shared data structure)
            config_root: Path to configuration root used for this run
            input_file: Optional path to input file used
            
        Returns:
            Path to the result file, or None if artifacts disabled
        """
        if not self.create_artifacts:
            return None
        
        run_dir = self.create_run_directory(run_id)
        
        # Save the main result
        result_file = run_dir / "result.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        # Create metadata
        metadata = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "config_root": str(Path(config_root).resolve()),
            "input_file": str(Path(input_file).resolve()) if input_file else None,
            "pipeline_name": result.get("pipeline_name", "unknown"),
            "execution_successful": result.get("execution_successful", False),
            "agent_count": len(result.get("agents", {})),
            "total_execution_time": result.get("metadata", {}).get("execution_time", 0)
        }
        
        # Save metadata
        metadata_file = run_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        if self.logger:
            log_debug(self.logger, f"Saved run result and metadata", "RunManager", {
                "run_id": run_id,
                "result_file": str(result_file),
                "metadata_file": str(metadata_file)
            })
        
        return result_file
    