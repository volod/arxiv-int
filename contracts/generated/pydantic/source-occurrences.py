import datetime, typing, pydantic, decimal
'Silo-relative source locations and scan status for archive bytes.'

class Source_occurrences(pydantic.BaseModel):
    occurrence_id: str
    silo_id: typing.Optional[str]
    relative_path: typing.Optional[str]
    scan_id: typing.Optional[str]
    content_hash: typing.Optional[str]
    container_path: typing.Optional[str]
    member_path: typing.Optional[str]
    status: typing.Optional[str]
    generation_id: str
    contract_version: str
