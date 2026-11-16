import datetime, typing, pydantic, decimal
'Complete, evidence-backed subject classification of physical archive files, including explicit unclassified and unreadable outcomes and the fingerprints needed to reproduce each decision.'

class File_classification(pydantic.BaseModel):
    classification_id: str
    occurrence_id: str
    document_id: typing.Optional[str]
    silo_id: str
    relative_path: str
    primary_class_id: str
    alternate_class_ids_json: str
    ancestor_path: str
    confidence: float
    calibration_profile: str
    scores_json: str
    evidence_json: str
    failure_reason: typing.Optional[str]
    extraction_fingerprint: str
    normalizer_id: str
    classifier_id: str
    configuration_sha256: str
    scheme_id: str
    review_state: str
    run_id: str
    generation_id: str
    contract_version: str
