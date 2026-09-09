import datetime, typing, pydantic, decimal
'Canonical normalized text views, detected language, and reversible offset maps.'

class Normalized_documents(pydantic.BaseModel):
    normalized_document_id: str
    document_id: typing.Optional[str]
    normalizer_id: typing.Optional[str]
    language: typing.Optional[str]
    language_confidence: typing.Optional[float]
    normalized_sha256: typing.Optional[str]
    text_chars: typing.Optional[int]
    generation_id: str
    contract_version: str
