from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    """Request body for POST /api/v1/reports/generate"""

    owner: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="GitHub owner/login of the repository to analyze",
    )
    repository: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Repository name to analyze",
    )


class ReportGenerateResponse(BaseModel):
    """Response for a generated AI analysis report (v0: synchronous)."""

    success: bool = Field(..., description="Whether the report was generated")
    repo_full_name: str = Field(..., description="owner/repository that was analyzed")
    report_markdown: str = Field(default="", description="The full report in Markdown")
    model_used: str | None = Field(default=None, description="LLM model that produced the report")
    prompt_tokens: int = Field(default=0, description="Input tokens consumed (cost evidence)")
    completion_tokens: int = Field(default=0, description="Output tokens consumed (cost evidence)")
    duration_ms: int = Field(default=0, description="Wall-clock time of the LLM call")
    generated_at: str = Field(default="", description="ISO timestamp of generation")
    message: str | None = Field(default=None, description="Human-readable status message")