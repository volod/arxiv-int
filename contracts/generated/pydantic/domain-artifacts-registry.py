import datetime, typing, pydantic, decimal
'Run artifact registry for domain investigation family outputs and creation statuses.'

class Domain_artifact_registry(pydantic.BaseModel):
    artifact_id: str
    artifact_type: typing.Optional[str]
    schema_version: typing.Optional[str]
    generator_fingerprint: typing.Optional[str]
    policy_fingerprint: typing.Optional[str]
    input_fact_snapshot_id: typing.Optional[str]
    identity_snapshot_id: typing.Optional[str]
    review_inclusion_rules: typing.Optional[str]
    uri_or_path: typing.Optional[str]
    media_type: typing.Optional[str]
    byte_count: typing.Optional[int]
    row_count: typing.Optional[int]
    checksum: typing.Optional[str]
    evidence_coverage: typing.Optional[float]
    creation_status: typing.Optional[str]
    failure_reason: typing.Optional[str]
    run_id: typing.Optional[str]
    generation_id: str
    contract_version: str
