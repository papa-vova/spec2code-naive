"""
Step 6: Do an independent comparison of the reports and generate a metric
"""
from typing import List, Dict, Any
import statistics


class MetricComparatorAgent:
    """Agent responsible for comparing reports and generating consistency metrics."""
    
    def __init__(self):
        self.weights = {
            "Technical Feasibility": 0.3,
            "Resource Adequacy": 0.25,
            "Timeline Realism": 0.25,
            "Dependency Analysis": 0.2
        }
    
    def compare_reports(self, reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare multiple independent reports and generate a consistency metric.
        
        Args:
            reports: List of report dictionaries from ReportGeneratorAgents
            
        Returns:
            Dictionary containing comparison results and metric
        """
        if not reports:
            return {
                "metric": 0.0,
                "status": "FAIL",
                "reason": "No reports provided",
                "details": {}
            }
        
        # Extract scores from reports
        scores = []
        report_summary = {}
        
        for report in reports:
            score = report.get("score", 0.0)
            report_type = report.get("type", "Unknown")
            scores.append(score)
            
            report_summary[report_type] = {
                "score": score,
                "summary": report.get("summary", ""),
                "concerns": report.get("concerns", []),
                "recommendations": report.get("recommendations", [])
            }
        
        # Calculate weighted average if weights are available
        weighted_score = 0.0
        total_weight = 0.0
        
        for report in reports:
            report_type = report.get("type", "Unknown")
            weight = self.weights.get(report_type, 0.1)  # Default weight for unknown types
            score = report.get("score", 0.0)
            
            weighted_score += score * weight
            total_weight += weight
        
        if total_weight > 0:
            final_metric = weighted_score / total_weight
        else:
            final_metric = statistics.mean(scores) if scores else 0.0
        
        # Calculate consistency (how much scores agree)
        score_variance = statistics.variance(scores) if len(scores) > 1 else 0.0
        consistency = max(0.0, 10.0 - score_variance)  # Higher variance = lower consistency
        
        # Determine status based on metric and consistency
        status = self._determine_status(final_metric, consistency)
        
        # Aggregate concerns and recommendations
        all_concerns = []
        all_recommendations = []
        
        for report in reports:
            all_concerns.extend(report.get("concerns", []))
            all_recommendations.extend(report.get("recommendations", []))
        
        return {
            "metric": round(final_metric, 2),
            "consistency": round(consistency, 2),
            "status": status,
            "reason": self._get_status_reason(final_metric, consistency),
            "details": {
                "individual_scores": scores,
                "weighted_average": round(final_metric, 2),
                "score_variance": round(score_variance, 2),
                "report_count": len(reports),
                "report_summary": report_summary,
                "aggregated_concerns": list(set(all_concerns)),  # Remove duplicates
                "aggregated_recommendations": list(set(all_recommendations))
            }
        }
    
    def _determine_status(self, metric: float, consistency: float) -> str:
        """Determine overall status based on metric and consistency."""
        if metric >= 7.0 and consistency >= 7.0:
            return "PASS"
        elif metric >= 5.0 and consistency >= 5.0:
            return "REVIEW"
        else:
            return "FAIL"
    
    def _get_status_reason(self, metric: float, consistency: float) -> str:
        """Get human-readable reason for the status."""
        if metric >= 7.0 and consistency >= 7.0:
            return "Plan shows high quality and report consensus"
        elif metric >= 5.0 and consistency >= 5.0:
            return "Plan is acceptable but needs review and improvements"
        elif metric < 5.0:
            return "Plan quality is below acceptable threshold"
        elif consistency < 5.0:
            return "Reports show significant disagreement on plan quality"
        else:
            return "Plan requires significant revision"
    
    def is_metric_ok(self, comparison_result: Dict[str, Any]) -> bool:
        """
        Check if the metric meets the 'metric ok?' condition from the flow.
        
        Args:
            comparison_result: Result from compare_reports method
            
        Returns:
            Boolean indicating if metric is acceptable
        """
        return comparison_result.get("status") == "PASS"
