import datetime, typing, pydantic, decimal
'Frozen classes of one versioned subject-taxonomy classification scheme: taxonomy classes, operator extensions and the unclassified/unreadable outcomes, with parent closure, multilingual captions, source crosswalk, and reversible path tokens.'

class Classification_classes(pydantic.BaseModel):
    scheme_class_id: str
    scheme_id: str
    class_id: str
    namespace: str
    code: typing.Optional[str]
    parent_class_id: typing.Optional[str]
    ancestor_path: str
    depth: int
    class_kind: str
    caption_en: typing.Optional[str]
    caption_ru: typing.Optional[str]
    caption_uk: typing.Optional[str]
    captions_json: str
    crosswalk_json: str
    path_token: str
    slug: typing.Optional[str]
    scheme_version: str
    generation_id: str
    contract_version: str
