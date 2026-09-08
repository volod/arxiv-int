import datetime, typing, pydantic, decimal
'Extracted subject-predicate-object facts with evidence anchors and confidence.'

class Facts(pydantic.BaseModel):
    fact_id: str
    subject_object_id: typing.Optional[str]
    predicate_id: typing.Optional[str]
    object_object_id: typing.Optional[str]
    literal_value: typing.Optional[str]
    literal_type: typing.Optional[str]
    status: typing.Optional[str]
    confidence: typing.Optional[float]
    document_id: typing.Optional[str]
    span_id: typing.Optional[str]
    chunk_id: typing.Optional[str]
    identity_snapshot_id: typing.Optional[str]
    extractor_id: typing.Optional[str]
    generation_id: str
    contract_version: str
