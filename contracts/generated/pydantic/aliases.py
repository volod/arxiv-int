import datetime, typing, pydantic, decimal
'Alternate labels and normalized aliases for knowledge-graph objects.'

class Aliases(pydantic.BaseModel):
    alias_id: str
    object_id: typing.Optional[str]
    alias_text: typing.Optional[str]
    alias_kind: typing.Optional[str]
    normalized_text: typing.Optional[str]
    generation_id: str
    contract_version: str
