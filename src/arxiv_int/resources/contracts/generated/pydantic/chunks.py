import datetime, typing, pydantic, decimal
'Chunker-partitioned text units derived from documents for retrieval and extraction.'

class Chunks(pydantic.BaseModel):
    chunk_id: str
    document_id: typing.Optional[str]
    chunker_id: typing.Optional[str]
    ordinal: typing.Optional[int]
    text: typing.Optional[str]
    start_char: typing.Optional[int]
    end_char: typing.Optional[int]
    generation_id: str
    contract_version: str
