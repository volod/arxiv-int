import datetime, typing, pydantic, decimal
'Surface-form mentions linking documents, spans, and chunks to object anchors.'

class Mentions(pydantic.BaseModel):
    mention_id: str
    document_id: typing.Optional[str]
    span_id: typing.Optional[str]
    chunk_id: typing.Optional[str]
    surface_form: typing.Optional[str]
    object_anchor_id: typing.Optional[str]
    generation_id: str
    contract_version: str
