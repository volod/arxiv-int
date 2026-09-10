import datetime, typing, pydantic, decimal
'Reversible duplicate and edition group memberships proposed over normalized documents.'

class Duplicate_groups(pydantic.BaseModel):
    duplicate_membership_id: str
    group_id: typing.Optional[str]
    document_id: typing.Optional[str]
    method: typing.Optional[str]
    role: typing.Optional[str]
    score: typing.Optional[float]
    suppressed: typing.Optional[bool]
    generation_id: str
    contract_version: str
