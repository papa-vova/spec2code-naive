#!/usr/bin/env python3
"""Tests for Milestone 5 performance and 3NF audit checks."""

import unittest

from agentic.audits.checks import check_3nf_data_structures, check_performance_guidance
from agentic.audits.gates import run_deterministic_audit


class TestCheck3NF(unittest.TestCase):
    """Unit tests for 3NF data structure checks."""

    def test_skipped_when_require_false(self):
        artifacts = {"ImplementationDesign": {"data_structures": []}}
        errors = check_3nf_data_structures(artifacts, require_3nf=False)
        self.assertEqual(errors, [])

    def test_skipped_when_implementation_design_absent(self):
        artifacts = {"BusinessRequirements": {}}
        errors = check_3nf_data_structures(artifacts, require_3nf=True)
        self.assertEqual(errors, [])

    def test_fails_empty_data_structures_when_required(self):
        artifacts = {"ImplementationDesign": {"modules": [], "data_structures": []}}
        errors = check_3nf_data_structures(artifacts, require_3nf=True)
        self.assertTrue(errors)
        self.assertTrue(any("at least one" in e.lower() for e in errors))

    def test_passes_valid_3nf(self):
        artifacts = {
            "ImplementationDesign": {
                "data_structures": [
                    {"id": "DS-001", "name": "User", "normalization_level": "3NF"}
                ]
            }
        }
        errors = check_3nf_data_structures(artifacts, require_3nf=True)
        self.assertEqual(errors, [])

    def test_fails_non_3nf_without_rationale(self):
        artifacts = {
            "ImplementationDesign": {
                "data_structures": [
                    {"id": "DS-001", "name": "User", "normalization_level": "2NF"}
                ]
            }
        }
        errors = check_3nf_data_structures(artifacts, require_3nf=True)
        self.assertTrue(errors)
        self.assertTrue(any("denormalization_rationale" in e for e in errors))

    def test_passes_non_3nf_with_rationale(self):
        artifacts = {
            "ImplementationDesign": {
                "data_structures": [
                    {
                        "id": "DS-001",
                        "name": "User",
                        "normalization_level": "2NF",
                        "denormalization_rationale": "Read-heavy cache table",
                    }
                ]
            }
        }
        errors = check_3nf_data_structures(artifacts, require_3nf=True)
        self.assertEqual(errors, [])

    def test_fails_missing_normalization_level(self):
        artifacts = {
            "ImplementationDesign": {
                "data_structures": [{"id": "DS-001", "name": "User"}]
            }
        }
        errors = check_3nf_data_structures(artifacts, require_3nf=True)
        self.assertTrue(errors)
        self.assertTrue(any("normalization_level" in e for e in errors))


class TestCheckPerformanceGuidance(unittest.TestCase):
    """Unit tests for performance guidance checks."""

    def test_skipped_when_require_false(self):
        artifacts = {"ImplementationDesign": {}}
        errors = check_performance_guidance(artifacts, require_performance=False)
        self.assertEqual(errors, [])

    def test_skipped_when_implementation_design_absent(self):
        artifacts = {"BusinessRequirements": {}}
        errors = check_performance_guidance(artifacts, require_performance=True)
        self.assertEqual(errors, [])

    def test_fails_no_guidance_when_required(self):
        artifacts = {
            "ImplementationDesign": {
                "modules": [{"name": "M1"}],
                "performance_guidance": [],
            }
        }
        errors = check_performance_guidance(artifacts, require_performance=True)
        self.assertTrue(errors)
        self.assertTrue(any("performance_guidance" in e or "complexity" in e for e in errors))

    def test_passes_with_performance_guidance_entries(self):
        artifacts = {
            "ImplementationDesign": {
                "performance_guidance": [
                    {"module_id": "M1", "complexity": "O(n log n)"}
                ]
            }
        }
        errors = check_performance_guidance(artifacts, require_performance=True)
        self.assertEqual(errors, [])

    def test_passes_with_module_complexity(self):
        artifacts = {
            "ImplementationDesign": {
                "modules": [{"name": "M1", "complexity": "O(n)"}],
                "performance_guidance": [],
            }
        }
        errors = check_performance_guidance(artifacts, require_performance=True)
        self.assertEqual(errors, [])


class TestAuditConfig(unittest.TestCase):
    """Tests that audit config flags are respected."""

    def test_checks_skipped_without_config(self):
        artifacts = {
            "ImplementationDesign": {
                "data_structures": [],
                "performance_guidance": [],
                "modules": [],
            }
        }
        results = run_deterministic_audit(artifacts)
        self.assertTrue(results["passed"])
        self.assertIn("three_nf", results["results"])
        self.assertIn("performance_guidance", results["results"])
        self.assertEqual(results["results"]["three_nf"], [])
        self.assertEqual(results["results"]["performance_guidance"], [])

    def test_checks_run_with_config_enabled(self):
        artifacts = {
            "ImplementationDesign": {
                "data_structures": [],
                "performance_guidance": [],
                "modules": [],
            }
        }
        config = type("AuditConfig", (), {"require_3nf_data_structures": True, "require_performance_guidance": True})()
        results = run_deterministic_audit(artifacts, audit_config=config)
        self.assertFalse(results["passed"])
        self.assertTrue(results["results"]["three_nf"])
        self.assertTrue(results["results"]["performance_guidance"])

    def test_audit_results_structure(self):
        artifacts = {
            "ImplementationDesign": {
                "data_structures": [{"id": "DS-1", "normalization_level": "3NF"}],
                "performance_guidance": [{"module_id": "M1", "complexity": "O(1)"}],
                "modules": [],
            }
        }
        config = type("AuditConfig", (), {"require_3nf_data_structures": True, "require_performance_guidance": True})()
        results = run_deterministic_audit(artifacts, audit_config=config)
        self.assertTrue(results["passed"])
        self.assertEqual(results["results"]["three_nf"], [])
        self.assertEqual(results["results"]["performance_guidance"], [])


if __name__ == "__main__":
    unittest.main()
