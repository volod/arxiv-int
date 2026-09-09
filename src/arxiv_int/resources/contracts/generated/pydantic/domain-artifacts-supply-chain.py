import datetime, typing, pydantic, decimal
'Supply-chain stage edges separating quote, order, invoice, ship, receive, and pay claims.'

class Supply_chain_edges(pydantic.BaseModel):
    edge_id: str
    path_id: typing.Optional[str]
    stage: typing.Optional[str]
    from_object_id: typing.Optional[str]
    to_object_id: typing.Optional[str]
    role_predicate_id: typing.Optional[str]
    product_object_id: typing.Optional[str]
    transaction_id: typing.Optional[str]
    direction: typing.Optional[str]
    event_time: typing.Optional[datetime.datetime]
    status: typing.Optional[str]
    evidence_fact_ids: typing.Optional[str]
    document_id: typing.Optional[str]
    review_state: typing.Optional[str]
    confidence: typing.Optional[float]
    generation_id: str
    contract_version: str
