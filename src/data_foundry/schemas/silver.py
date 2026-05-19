from pydantic import BaseModel


class SilverLlmMetadata(BaseModel):
    model: str
    base_url: str
    run_id: str
    generated_at: str
    vision_used: bool | None = None  # only present in descriptions


class SilverDescription(BaseModel):
    title: str
    description: str | None = None
    error: str | None = None
    llm_metadata: SilverLlmMetadata | None = None


class SilverTranslation(BaseModel):
    original: str
    en: str | None = None
    es: str | None = None
    fr: str | None = None
    llm_metadata: SilverLlmMetadata | None = None


class SilverCover(BaseModel):
    path: str | None = None
    hash: str | None = None
