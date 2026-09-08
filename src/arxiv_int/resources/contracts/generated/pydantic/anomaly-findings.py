import datetime, typing, pydantic, decimal
'Anomaly findings with severity, status, and evidence summaries for review.'

class Anomaly_findings(pydantic.BaseModel):
    finding_id: str
    finding_type: typing.Optional[str]
    severity: typing.Optional[str]
    status: typing.Optional[str]
    subject_object_id: typing.Optional[str]
    rule_id: typing.Optional[str]
    evidence_summary: typing.Optional[str]
    generation_id: str
    contract_version: str
