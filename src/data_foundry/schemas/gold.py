from pydantic import BaseModel


class GoldTitle(BaseModel):
    pt: str
    en: str | None = None
    es: str | None = None
    fr: str | None = None


class GoldDescription(BaseModel):
    pt: str | None = None
    en: str | None = None
    es: str | None = None
    fr: str | None = None


class GoldLocalizedEntry(BaseModel):
    id: str
    title: GoldTitle
    description: GoldDescription
    author: str | None = None
    source: str | None = None


class GoldUniversalEntry(BaseModel):
    id: str
    cover_path: str | None = None
    cover_hash: str | None = None
    document_hash: str | None = None
    accesses: int | None = None
    size_bytes: int | None = None
    category: str | None = None
    language: str | None = None
    institution: str | None = None
    year: str | None = None
    download_url: str | None = None
