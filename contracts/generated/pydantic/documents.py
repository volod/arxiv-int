import datetime, typing, pydantic, decimal
'Normalized document identity and extracted text metadata for the archive corpus.'

class Documents(pydantic.BaseModel):
    document_id: str
    content_hash: typing.Optional[str]
    extractor_profile: typing.Optional[str]
    media_type: typing.Optional[str]
    language: typing.Optional[str]
    title: typing.Optional[str]
    byte_size: typing.Optional[int]
    text_chars: typing.Optional[int]
    generation_id: str
    contract_version: str
