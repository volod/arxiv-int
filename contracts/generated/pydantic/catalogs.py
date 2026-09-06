import datetime, typing, pydantic, decimal
'Catalog entries summarizing objects with preferred names and document counts.'

class Catalog_entries(pydantic.BaseModel):
    catalog_entry_id: str
    catalog_kind: typing.Optional[str]
    object_id: typing.Optional[str]
    preferred_name: typing.Optional[str]
    document_count: typing.Optional[int]
    review_state: typing.Optional[str]
    generation_id: str
    contract_version: str
