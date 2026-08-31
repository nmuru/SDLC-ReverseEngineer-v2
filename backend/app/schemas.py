from pydantic import BaseModel, HttpUrl


class AnalyzeRequest(BaseModel):
    repo_url: HttpUrl
    selected_phases: list[str]
    work_id: str | None = None
    provider: str = "anthropic"
    model: str = "claude-sonnet-5"
    api_key: str


class AnalyzeResponse(BaseModel):
    repo_url: str
    business_purpose: str
    business_requirements: str
    features: str
    software_requirements: str
    technology_architecture: str
    design_pattern: str
    high_level_design: str
    low_level_design: str
    implementation_detail: str
    testing_harness: str
    future_directions: str
