from pydantic import BaseModel


class BronzeCatalogEntry(BaseModel):
    code: str
    title: str
    author: str | None = None
    source: str | None = None
    format: str | None = None
    size: str | None = None
    accesses: str | None = None
    download_url: str | None = None
    downloaded: bool = False


class BronzeMetadataEntry(BaseModel):
    code: str
    title: str | None = None
    author: str | None = None
    category: str | None = None
    language: str | None = None
    institution: str | None = None
    year: str | None = None
    accesses: str | None = None
    download_url: str | None = None


class BronzeHashEntry(BaseModel):
    sha256: str
    size_bytes: int


class BronzeHashes(BaseModel):
    total_files: int
    unique_hashes: int
    duplicates: dict
    files: dict[str, BronzeHashEntry]
