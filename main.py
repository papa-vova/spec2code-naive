"""
Main entry point for the skeleton LangChain application.
Implements steps 4-6 of the analysis branch.
"""
import os
import sys
import argparse
from typing import List, Dict, Any
from agents.plan_maker import PlanMakerAgent
from agents.plan_critique_generator import create_report_generators
from agents.plan_critique_comparator import MetricComparatorAgent


class Pipeline:
    """Main pipeline implementation."""
    
    def __init__(self, n_reports: int = 4):
        # Skeleton implementation without LLM dependencies
        self.plan_maker = PlanMakerAgent()
        self.report_generators = create_report_generators(n=n_reports)
        self.metric_comparator = MetricComparatorAgent()
        self.n_reports = n_reports
    
    def run_pipeline(self, input_description: str) -> Dict[str, Any]:
        """
        Execute the complete pipeline.
        
        Args:
            input_description: Free text description of what should be done
            
        Returns:
            Dictionary containing all results and final metric decision
        """
        print("=== PIPELINE EXECUTION ===")
        print(f"Input description: {input_description[:100]}{'...' if len(input_description) > 100 else ''}")
        
        # Step: Make a plan of implementing the whole set of steps
        print("\n--- Step: Creating Implementation Plan ---")
        implementation_plan = self.plan_maker.create_plan(input_description)
        print(f"Plan created: {len(implementation_plan)} characters")
        
        # Step: Produce N independent critical reports on the plan's consistency
        print(f"\n--- Step: Generating {self.n_reports} Independent Reports ---")
        reports = []
        for i, generator in enumerate(self.report_generators):
            print(f"Generating report {i+1}/{self.n_reports}: {generator.report_type.value}")
            report = generator.generate_report(implementation_plan)
            reports.append(report)
            print(f"  Score: {report['score']}, Type: {report['type']}")
        
        # Step: Do an independent comparison of the reports and generate a metric
        print("\n--- Step: Comparing Reports and Generating Metric ---")
        comparison_result = self.metric_comparator.compare_reports(reports)
        
        print(f"Final Metric: {comparison_result['metric']}")
        print(f"Consistency: {comparison_result['consistency']}")
        print(f"Status: {comparison_result['status']}")
        print(f"Reason: {comparison_result['reason']}")
        
        # Check if metric is OK (decision point from flow)
        metric_ok = self.metric_comparator.is_metric_ok(comparison_result)
        print(f"\nMetric OK? {metric_ok}")
        
        if not metric_ok:
            print("-> Would loop back to 'Make a plan' step")
        else:
            print("-> Would proceed to implementation branch")
        
        return {
            "input_description": input_description,
            "implementation_plan": implementation_plan,
            "reports": reports,
            "comparison_result": comparison_result,
            "metric_ok": metric_ok,
            "next_action": "loop_back" if not metric_ok else "proceed"
        }


def main():
    """Main function to run the pipeline with CLI arguments."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='SPEC2CODE Pipeline - Generate implementation plans from feature descriptions'
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input file containing the feature description'
    )
    
    args = parser.parse_args()
    input_file = args.input
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.", file=sys.stderr)
        sys.exit(1)
    
    # Read input from file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            input_description = f.read().strip()
        print(f"Reading input from: {input_file}")
    except Exception as e:
        print(f"Error reading file '{input_file}': {e}", file=sys.stderr)
        sys.exit(1)
    
    if not input_description:
        print(f"Error: Input file '{input_file}' is empty.", file=sys.stderr)
        sys.exit(1)
    
    print("SPEC2CODE NAIVE FLOW - PIPELINE SKELETON")
    print("=====================================")
    
    # Initialize and run pipeline
    pipeline = Pipeline(n_reports=4)
    results = pipeline.run_pipeline(input_description)
    
    print("\n=== EXECUTION SUMMARY ===")
    print(f"Input description length: {len(results['input_description'])} chars")
    print(f"Plan length: {len(results['implementation_plan'])} chars")
    print(f"Reports generated: {len(results['reports'])}")
    print(f"Final metric: {results['comparison_result']['metric']}")
    print(f"Metric OK: {results['metric_ok']}")
    print(f"Next action: {results['next_action']}")
    
    # Show detailed results
    print("\n=== DETAILED RESULTS ===")
    print("\nImplementation Plan:")
    print(results['implementation_plan'])
    
    print(f"\nReports Summary:")
    for i, report in enumerate(results['reports']):
        print(f"  {i+1}. {report['type']}: Score {report['score']} - {report['summary']}")
    
    print(f"\nComparison Details:")
    details = results['comparison_result']['details']
    print(f"  Individual scores: {details['individual_scores']}")
    print(f"  Score variance: {details['score_variance']}")
    print(f"  Top concerns: {details['aggregated_concerns'][:3]}")
    print(f"  Top recommendations: {details['aggregated_recommendations'][:3]}")


if __name__ == "__main__":
    main()
