import datetime, typing, pydantic, decimal
'Frozen evaluation items with gold references, splits, and labels.'

class Evaluation_items(pydantic.BaseModel):
    evaluation_item_id: str
    item_kind: typing.Optional[str]
    gold_ref: typing.Optional[str]
    split: typing.Optional[str]
    query_text: typing.Optional[str]
    label: typing.Optional[str]
    dataset_id: typing.Optional[str]
    generation_id: str
    contract_version: str
