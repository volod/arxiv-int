import datetime, typing, pydantic, decimal
'Portable path events that record initial, renamed, copied, and imported locations for canonical documents.'

class Document_path_event(pydantic.BaseModel):
    event_id: str
    document_id: str
    occurrence_id: typing.Optional[str]
    silo_id: str
    kind: str
    relative_path: str
    previous_relative_path: typing.Optional[str]
    content_hash: str
    ledger_id: typing.Optional[str]
    event_time: datetime.datetime
    generation_id: str
    contract_version: str
