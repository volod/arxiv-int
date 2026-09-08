import datetime, typing, pydantic, decimal
'Financial or exchange transactions linked to parties and source documents.'

class Transactions(pydantic.BaseModel):
    transaction_id: str
    transaction_type: typing.Optional[str]
    amount: typing.Optional[float]
    currency: typing.Optional[str]
    party_subject_id: typing.Optional[str]
    party_object_id: typing.Optional[str]
    document_id: typing.Optional[str]
    event_time: typing.Optional[datetime.datetime]
    generation_id: str
    contract_version: str
