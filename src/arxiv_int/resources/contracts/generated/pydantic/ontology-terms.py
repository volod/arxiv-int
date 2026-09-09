import datetime, typing, pydantic, decimal
'Controlled ontology terms with URIs, labels, and domain or range constraints.'

class Terms(pydantic.BaseModel):
    term_id: str
    uri: typing.Optional[str]
    label: typing.Optional[str]
    kind: typing.Optional[str]
    domain_uri: typing.Optional[str]
    range_uri: typing.Optional[str]
    ontology_version: typing.Optional[str]
    generation_id: str
    contract_version: str
