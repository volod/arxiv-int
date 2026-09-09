import datetime, typing, pydantic, decimal
'Character-anchored spans locating evidence within documents.'

class Spans(pydantic.BaseModel):
    span_id: str
    document_id: typing.Optional[str]
    start_char: typing.Optional[int]
    end_char: typing.Optional[int]
    page: typing.Optional[int]
    kind: typing.Optional[str]
    generation_id: str
    contract_version: str
