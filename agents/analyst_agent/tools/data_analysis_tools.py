from pydantic import BaseModel, Field


class AnalysisInsight(BaseModel):
    """Individual insight from data analysis."""

    insight: str = Field(..., description="The key insight discovered")
    confidence: float = Field(..., description="Confidence level from 0.0 to 1.0")
    supporting_evidence: list[str] = Field(..., description="Evidence supporting the insight")


class DataAnalysisResponse(BaseModel):
    """Structured response from data analysis."""

    analysis_type: str = Field(..., description="Type of analysis performed")
    data_description: str = Field(..., description="Description of the analyzed data")
    insights: list[AnalysisInsight] = Field(..., description="Key insights discovered")
    recommendations: list[str] = Field(..., description="Actionable recommendations")
    overall_confidence: float = Field(..., description="Overall confidence in analysis")


class VisualizationSuggestion(BaseModel):
    """Structured visualization suggestions."""

    data_type: str = Field(..., description="Type of data being visualized")
    analysis_goal: str = Field(..., description="Goal of the analysis")
    recommended_visualizations: list[str] = Field(..., description="Recommended chart types")
    reasoning: str = Field(..., description="Reasoning for visualization choices")
    implementation_tips: list[str] = Field(..., description="Tips for implementation")


def data_analysis_tool(
    data_description: str, analysis_type: str = "summary"
) -> DataAnalysisResponse:
    """
    Analyze data and provide structured insights based on the description.

    Args:
        data_description: Description of the data to analyze
        analysis_type: Type of analysis (summary, trends, patterns, comparison)

    Returns:
        DataAnalysisResponse: Structured analysis results with insights and recommendations
    """
    analysis_templates = {
        "summary": DataAnalysisResponse(
            analysis_type="summary",
            data_description=data_description,
            insights=[
                AnalysisInsight(
                    insight="Dataset appears well-structured for comprehensive analysis",
                    confidence=0.85,
                    supporting_evidence=[
                        "Data description indicates clear structure and organization",
                        "Multiple analysis dimensions available for exploration",
                    ],
                )
            ],
            recommendations=[
                "Perform initial data quality assessment and cleaning",
                "Explore basic statistics and distributions for key variables",
                "Identify any missing values or outliers that need addressing",
            ],
            overall_confidence=0.85,
        ),
        "trends": DataAnalysisResponse(
            analysis_type="trends",
            data_description=data_description,
            insights=[
                AnalysisInsight(
                    insight=(
                        "Strong potential for identifying temporal patterns and growth trajectories"
                    ),
                    confidence=0.78,
                    supporting_evidence=[
                        "Data suggests measurable changes over time",
                        "Suitable for time series decomposition and trend analysis",
                    ],
                )
            ],
            recommendations=[
                "Apply moving averages or exponential smoothing to identify underlying trends",
                "Test for stationarity using Dickey-Fuller test if time series data",
                "Look for seasonal patterns using autocorrelation analysis",
            ],
            overall_confidence=0.78,
        ),
    }

    return analysis_templates.get(analysis_type, analysis_templates["summary"])


def visualization_suggestion_tool(data_type: str, analysis_goal: str) -> VisualizationSuggestion:
    """
    Suggest appropriate visualizations for data analysis.

    Args:
        data_type: Type of data (numerical, categorical, time_series, etc.)
        analysis_goal: Goal of the analysis (trend_analysis, distribution, comparison, etc.)

    Returns:
        VisualizationSuggestion: Structured visualization suggestions with implementation guidance
    """
    suggestions_map = {
        "numerical": {
            "distribution": ["histogram", "box_plot", "violin_plot", "density_plot"],
            "comparison": ["bar_chart", "column_chart", "radar_chart"],
        },
        "categorical": {
            "distribution": ["bar_chart", "pie_chart", "donut_chart"],
            "comparison": ["grouped_bar_chart", "stacked_bar_chart"],
        },
    }

    data_suggestions = suggestions_map.get(data_type, {})
    goal_suggestions = data_suggestions.get(analysis_goal, ["bar_chart", "line_chart"])

    implementation_tips = [
        "Ensure proper labeling with clear titles and axis labels",
        "Use color schemes that are accessible and colorblind-friendly",
        "Include legends where necessary to explain encoding",
    ]

    return VisualizationSuggestion(
        data_type=data_type,
        analysis_goal=analysis_goal,
        recommended_visualizations=goal_suggestions,
        reasoning=(
            f"For {data_type} data with {analysis_goal} goal, "
            "these visualizations are most effective."
        ),
        implementation_tips=implementation_tips,
    )
