import datetime, typing, pydantic, decimal
'Vector embedding references for retrieval targets under a profile.'

class Embeddings(pydantic.BaseModel):
    embedding_id: str
    target_kind: typing.Optional[str]
    target_id: typing.Optional[str]
    profile_id: typing.Optional[str]
    dimensions: typing.Optional[int]
    vector_ref: typing.Optional[str]
    model_digest: typing.Optional[str]
    generation_id: str
    contract_version: str
