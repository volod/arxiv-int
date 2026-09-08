import datetime, typing, pydantic, decimal
'Topic assignments linking documents to labeled topics under a scheme.'

class Topic_assignments(pydantic.BaseModel):
    topic_assignment_id: str
    topic_id: typing.Optional[str]
    label: typing.Optional[str]
    scheme_id: typing.Optional[str]
    document_id: typing.Optional[str]
    score: typing.Optional[float]
    generation_id: str
    contract_version: str
