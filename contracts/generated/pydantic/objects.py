import datetime, typing, pydantic, decimal
'Canonical knowledge-graph objects with lifecycle and review state.'

class Objects(pydantic.BaseModel):
    object_id: str
    object_type: typing.Optional[str]
    preferred_label: typing.Optional[str]
    lifecycle_state: typing.Optional[str]
    review_state: typing.Optional[str]
    cluster_id: typing.Optional[str]
    generation_id: str
    contract_version: str
