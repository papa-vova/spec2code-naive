#!/usr/bin/env python3
"""
Primary runtime regression test suite for the agent pipeline system.

This is the MAIN test file for all runtime behavior validation including:
- Unified data structure implementation
- Multi-input agent support
- Pipeline execution flow
- Data integrity and no duplication
- Input/output standardization
- Template handling logic
- Mixed input scenarios

ALL new features and changes should be validated by adding tests to this file.
This ensures comprehensive regression testing and system integrity.
"""

import unittest
import tempfile
import os
import sys
import yaml
from pathlib import Path
from unittest.mock import Mock, patch

from core.orchestrator import Orchestrator
from config_system.config_loader import ConfigLoader, PipelineAgentConfig
from exceptions import PipelineError
from logging_config import setup_pipeline_logging, log_step_start, log_step_complete, log_error


class TestUnifiedDataStructure(unittest.TestCase):
    """Test the new unified data structure implementation."""
    
    def setUp(self):
        """Set up test environment with temporary config directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_root = Path(self.temp_dir)
        
        # Create directory structure
        (self.config_root / "models").mkdir()
        (self.config_root / "agents").mkdir()
        
        # Create test model config
        model_config = {
            "name": "test_model",
            "provider": "test",
            "model_name": "test-model",
            "parameters": {"temperature": 0.7}
        }
        with open(self.config_root / "models" / "test_model.yaml", "w") as f:
            yaml.dump(model_config, f)
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def create_test_agent_config(self, agent_name: str):
        """Create a test agent configuration."""
        agent_dir = self.config_root / "agents" / agent_name
        agent_dir.mkdir()
        
        # Agent config
        agent_config = {
            "name": agent_name,
            "description": f"Test agent {agent_name}",
            "llm": "test_model",
            "tools": [],
            "memory": {"_type": "buffer"},
            "agent_type": "zero-shot-react-description"
        }
        with open(agent_dir / "agent.yaml", "w") as f:
            yaml.dump(agent_config, f)
        
        # Prompts config
        prompts_config = {
            "system_message": f"You are {agent_name}",
            "human_message_template": "Process this: {input}",
            "prompt_templates": {
                "default": f"Default template for {agent_name}: {{input}}"
            }
        }
        with open(agent_dir / "prompts.yaml", "w") as f:
            yaml.dump(prompts_config, f)
    
    def create_test_pipeline_config(self, agents_config: list):
        """Create a test pipeline configuration."""
        pipeline_config = {
            "pipeline": {
                "name": "test_pipeline",
                "description": "Test pipeline for unified data structure",
                "agents": agents_config,
                "execution": {"mode": "sequential"},
                "settings": {"log_level": "INFO"}
            }
        }
        with open(self.config_root / "pipeline.yaml", "w") as f:
            yaml.dump(pipeline_config, f)

        # Agentic role model profiles are required in the current architecture.
        role_profiles = {
            agent["name"]: {"model": "test_model"}
            for agent in agents_config
        }
        with open(self.config_root / "agentic.yaml", "w") as f:
            yaml.dump({"role_model_profiles": role_profiles}, f)
    
    def test_pipeline_agent_config_single_input(self):
        """Test PipelineAgentConfig with single input."""
        config = PipelineAgentConfig(
            name="test_agent",
            inputs=["pipeline_input"],
            prompt_templates="default"
        )
        
        self.assertEqual(config.name, "test_agent")
        self.assertEqual(config.inputs, ["pipeline_input"])
        self.assertEqual(config.prompt_templates, "default")
    
    def test_pipeline_agent_config_multiple_inputs(self):
        """Test PipelineAgentConfig with multiple inputs."""
        config = PipelineAgentConfig(
            name="test_agent",
            inputs=["agent1", "agent2"],
            prompt_templates=["template1", "template2"]
        )
        
        self.assertEqual(config.inputs, ["agent1", "agent2"])
        self.assertIsInstance(config.prompt_templates, list)
    
    @patch('core.orchestrator.AgentFactory')
    @patch('config_system.config_loader.ConfigLoader.load_pipeline_config')
    @patch('core.orchestrator.Orchestrator._validate_pipeline_config')
    def test_prepare_agent_input_single_source(self, mock_validate, mock_pipeline_config, mock_factory):
        """Test _prepare_agent_input with single input source."""
        # Mock pipeline config
        mock_config = Mock()
        mock_config.agents = []
        mock_pipeline_config.return_value = mock_config
        
        # Setup
        orchestrator = Orchestrator(str(self.config_root), dry_run=True)
        
        # Create test pipeline data
        pipeline_data = {
            "pipeline_input": {"test": "data"},
            "agents": {
                "agent1": {
                    "output": {"result": "agent1_output"},
                    "metadata": {"agent_name": "agent1"}
                }
            }
        }
        
        # Test with pipeline_input
        agent_config = PipelineAgentConfig(
            name="test_agent",
            inputs=["pipeline_input"]
        )
        result = orchestrator._prepare_agent_input(pipeline_data, agent_config)
        expected = {"input": {"test": "data"}}
        self.assertEqual(result, expected)
        
        # Test with agent output
        agent_config = PipelineAgentConfig(
            name="test_agent",
            inputs=["agent1"]
        )
        result = orchestrator._prepare_agent_input(pipeline_data, agent_config)
        expected = {"input": {"result": "agent1_output"}}
        self.assertEqual(result, expected)
    
    @patch('core.orchestrator.AgentFactory')
    @patch('config_system.config_loader.ConfigLoader.load_pipeline_config')
    @patch('core.orchestrator.Orchestrator._validate_pipeline_config')
    def test_prepare_agent_input_multiple_sources(self, mock_validate, mock_pipeline_config, mock_factory):
        """Test _prepare_agent_input with multiple input sources."""
        # Mock pipeline config
        mock_config = Mock()
        mock_config.agents = []
        mock_pipeline_config.return_value = mock_config
        
        # Setup
        orchestrator = Orchestrator(str(self.config_root), dry_run=True)
        
        # Create test pipeline data
        pipeline_data = {
            "pipeline_input": {"test": "data"},
            "agents": {
                "agent1": {
                    "output": {"result": "agent1_output"},
                    "metadata": {"agent_name": "agent1"}
                },
                "agent2": {
                    "output": {"result": "agent2_output"},
                    "metadata": {"agent_name": "agent2"}
                }
            }
        }
        
        # Test with multiple agents
        agent_config = PipelineAgentConfig(
            name="test_agent",
            inputs=["agent1", "agent2"]
        )
        result = orchestrator._prepare_agent_input(pipeline_data, agent_config)
        expected = {
            "input": {
                "agent1": {"result": "agent1_output"},
                "agent2": {"result": "agent2_output"}
            }
        }
        self.assertEqual(result, expected)
        
        # Test with mixed sources
        agent_config = PipelineAgentConfig(
            name="test_agent",
            inputs=["pipeline_input", "agent1"]
        )
        result = orchestrator._prepare_agent_input(pipeline_data, agent_config)
        expected = {
            "input": {
                "pipeline_input": {"test": "data"},
                "agent1": {"result": "agent1_output"}
            }
        }
        self.assertEqual(result, expected)
    
    @patch('core.orchestrator.AgentFactory')
    @patch('config_system.config_loader.ConfigLoader.load_pipeline_config')
    @patch('core.orchestrator.Orchestrator._validate_pipeline_config')
    def test_prepare_agent_input_invalid_source(self, mock_validate, mock_pipeline_config, mock_factory):
        """Test _prepare_agent_input with invalid input source."""
        # Mock pipeline config
        mock_config = Mock()
        mock_config.agents = []
        mock_pipeline_config.return_value = mock_config
        
        orchestrator = Orchestrator(str(self.config_root), dry_run=True)
        
        pipeline_data = {
            "pipeline_input": {"test": "data"},
            "agents": {}
        }
        
        agent_config = PipelineAgentConfig(
            name="test_agent",
            inputs=["nonexistent_agent"]
        )
        
        with self.assertRaises(PipelineError) as context:
            orchestrator._prepare_agent_input(pipeline_data, agent_config)
        
        self.assertIn("Invalid input source 'nonexistent_agent'", str(context.exception))
    
    def test_unified_data_structure_no_duplication(self):
        """Test that the unified data structure eliminates duplication."""
        # Create test agents
        self.create_test_agent_config("agent1")
        self.create_test_agent_config("agent2")
        
        # Create pipeline config
        agents_config = [
            {"name": "agent1", "inputs": ["pipeline_input"]},
            {"name": "agent2", "inputs": ["agent1"]}
        ]
        self.create_test_pipeline_config(agents_config)
        
        # Mock the agent execution
        with patch('core.orchestrator.AgentFactory') as mock_factory:
            mock_agent = Mock()
            mock_agent.execute.return_value = {
                "output": {"agent_response": "test result"},
                "metadata": {"execution_time": 100}
            }
            mock_factory.return_value.create_agent_with_model.return_value = mock_agent
            
            orchestrator = Orchestrator(str(self.config_root), dry_run=True)
            
            # Execute pipeline
            result = orchestrator.execute_pipeline({"input": "test"})
            
            # Verify structure
            self.assertIn("agents", result)
            self.assertIn("agent1", result["agents"])
            self.assertIn("agent2", result["agents"])
            
            # Verify no duplication - each agent's data appears only once
            agent1_data = result["agents"]["agent1"]
            self.assertIn("output", agent1_data)
            self.assertIn("metadata", agent1_data)
            
            # Verify metadata includes input sources
            self.assertIn("input_sources", agent1_data["metadata"])
            self.assertEqual(agent1_data["metadata"]["input_sources"], "pipeline_input")  # String for pipeline input
            
            agent2_data = result["agents"]["agent2"]
            self.assertEqual(agent2_data["metadata"]["input_sources"], ["agent1"])  # Array for agent input
    
    def test_config_validation_with_new_format(self):
        """Test that config validation works with the new format."""
        # Create test agents
        self.create_test_agent_config("agent1")
        self.create_test_agent_config("agent2")
        
        # Create valid pipeline config
        agents_config = [
            {"name": "agent1", "inputs": ["pipeline_input"]},
            {"name": "agent2", "inputs": ["agent1"]}
        ]
        self.create_test_pipeline_config(agents_config)
        
        # Should not raise any exceptions
        config_loader = ConfigLoader(str(self.config_root))
        pipeline_config = config_loader.load_pipeline_config()
        
        self.assertEqual(len(pipeline_config.agents), 2)
        self.assertEqual(pipeline_config.agents[0].inputs, ["pipeline_input"])
        self.assertEqual(pipeline_config.agents[1].inputs, ["agent1"])


def main():
    """Main entry point for runtime regression tests."""
    # Set up logging
    pipeline_logger = setup_pipeline_logging(
        log_level="INFO",
        verbose=False
    )
    logger = pipeline_logger.get_logger("test_runtime")
    
    try:
        log_step_start(logger, "TestRunner", "runtime_tests", "Starting runtime regression tests", {
            "test_suite": "test_runtime.py",
            "purpose": "regression_testing"
        })
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(sys.modules[__name__])
        
        # Run tests silently for CI/CD (no stdout output except logs)
        import io
        runner = unittest.TextTestRunner(verbosity=0, stream=io.StringIO())
        result = runner.run(suite)
        
        # Determine success
        success = result.wasSuccessful()
        
        # Log results
        test_info = {
            "tests_run": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0,
            "success": success
        }
        
        if success:
            log_step_complete(logger, "TestRunner", "runtime_tests", 
                            "All runtime regression tests passed", test_info)
        else:
            log_error(logger, "Some runtime regression tests failed", "TestRunner", None)
            
            # Log failure details
            for test, traceback in result.failures:
                log_error(logger, f"Test failure: {test}", "TestRunner", None)
            
            for test, traceback in result.errors:
                log_error(logger, f"Test error: {test}", "TestRunner", None)
        
        # Exit with appropriate code for CI/CD
        sys.exit(0 if success else 1)
        
    except Exception as e:
        log_error(logger, f"Unexpected error during test execution: {str(e)}", "TestRunner", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
