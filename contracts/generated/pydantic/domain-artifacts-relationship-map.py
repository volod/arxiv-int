import datetime, typing, pydantic, decimal
'Typed design/party/product relationship edges with evidence and inclusion state.'

class Relationship_edges(pydantic.BaseModel):
    edge_id: str
    subject_object_id: typing.Optional[str]
    predicate_id: typing.Optional[str]
    object_object_id: typing.Optional[str]
    relation_kind: typing.Optional[str]
    direction: typing.Optional[str]
    cardinality: typing.Optional[str]
    review_state: typing.Optional[str]
    inclusion_policy: typing.Optional[str]
    conflict_group_id: typing.Optional[str]
    evidence_fact_ids: typing.Optional[str]
    document_id: typing.Optional[str]
    span_id: typing.Optional[str]
    anchor_kind: typing.Optional[str]
    confidence: typing.Optional[float]
    generation_id: str
    contract_version: str
