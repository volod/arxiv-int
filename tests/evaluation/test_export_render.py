from arxiv_int.evaluation.export_catalog import CatalogEntity, CatalogField
from arxiv_int.evaluation.export_render import (
    account_substitute,
    address_substitutes,
    email_substitute,
    entity_label,
    iban_valid,
    inn10_check_digit,
    luhn_valid,
    phone_substitute,
)


def test_entity_labels_keep_same_name_entities_distinct() -> None:
    left = CatalogEntity("person:alpha", "person", ("Alice Example",), ())
    right = CatalogEntity("person:beta", "person", ("Alice Example",), ())

    assert entity_label(left).startswith("person_")
    assert entity_label(right).startswith("person_")
    assert entity_label(left) != entity_label(right)
    assert entity_label(left) == entity_label(left)


def test_email_phone_and_address_keep_required_shape() -> None:
    email = email_substitute("alice.example@acme.example")
    assert email.startswith("contact_")
    assert email.endswith("@example.invalid")
    phone = phone_substitute(
        CatalogField("phone", "+7 (495) 123-45-67", "", "+7", "", "", "", "", "")
    )
    assert phone.startswith("+7")
    assert len([char for char in phone if char.isdigit()]) == 11
    assert "(" in phone and "-" in phone
    address = address_substitutes(
        CatalogField(
            "address",
            "Example Street 12, Exampleville, 125009",
            "",
            "",
            "Example Street",
            "12",
            "Exampleville",
            "125009",
            "",
        )
    )
    assert address["Example Street"].startswith("Street_")
    assert address["Exampleville"].startswith("City_")
    assert address["12"].isdigit()
    assert len(address["125009"]) == 6


def test_account_substitutes_recompute_check_digits() -> None:
    luhn = account_substitute(
        CatalogField("account", "4532015112830366", "luhn", "", "", "", "", "", "")
    )
    assert luhn_valid(luhn)
    assert luhn != "4532015112830366"
    iban = account_substitute(
        CatalogField("account", "DE89370400440532013000", "iban", "", "", "", "", "", "")
    )
    assert iban.startswith("DE")
    assert iban_valid(iban)
    inn = account_substitute(CatalogField("account", "0123456789", "inn10", "", "", "", "", "", ""))
    assert inn10_check_digit(inn[:-1]) == inn[-1]
    assert len(inn) == 10
