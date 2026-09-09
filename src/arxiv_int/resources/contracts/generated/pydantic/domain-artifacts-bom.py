import datetime, typing, pydantic, decimal
'Bill-of-materials hierarchy rows with quantities, alternatives, effectivity, and completeness.'

class Bom_lines(pydantic.BaseModel):
    bom_line_id: str
    bom_id: typing.Optional[str]
    root_object_id: typing.Optional[str]
    parent_object_id: typing.Optional[str]
    child_object_id: typing.Optional[str]
    predicate_id: typing.Optional[str]
    listing_kind: typing.Optional[str]
    quantity: typing.Optional[float]
    unit: typing.Optional[str]
    alternative_group_id: typing.Optional[str]
    is_mandatory: typing.Optional[bool]
    effectivity_start: typing.Optional[datetime.datetime]
    effectivity_end: typing.Optional[datetime.datetime]
    revision_object_id: typing.Optional[str]
    completeness_status: typing.Optional[str]
    cycle_detected: typing.Optional[bool]
    evidence_fact_ids: typing.Optional[str]
    document_id: typing.Optional[str]
    anchor_kind: typing.Optional[str]
    review_state: typing.Optional[str]
    generation_id: str
    contract_version: str
