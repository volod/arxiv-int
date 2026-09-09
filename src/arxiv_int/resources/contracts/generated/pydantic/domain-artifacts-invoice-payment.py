import datetime, typing, pydantic, decimal
'Invoice lines, payments, credit notes, ledger postings, and allocation match states.'

class Invoice_payment_rows(pydantic.BaseModel):
    row_id: str
    row_kind: typing.Optional[str]
    invoice_object_id: typing.Optional[str]
    payment_object_id: typing.Optional[str]
    line_number: typing.Optional[int]
    amount: typing.Optional[float]
    allocated_amount: typing.Optional[float]
    currency: typing.Optional[str]
    due_date: typing.Optional[datetime.datetime]
    payment_date: typing.Optional[datetime.datetime]
    match_state: typing.Optional[str]
    allocation_group_id: typing.Optional[str]
    debit_credit: typing.Optional[str]
    evidence_fact_ids: typing.Optional[str]
    document_id: typing.Optional[str]
    review_state: typing.Optional[str]
    confidence: typing.Optional[float]
    generation_id: str
    contract_version: str
