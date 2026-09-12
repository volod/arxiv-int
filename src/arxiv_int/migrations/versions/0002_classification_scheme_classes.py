"""classification scheme classes

Generated from contract-derived SQLAlchemy metadata. Definitions below are frozen:
this revision never imports today's contracts to decide what it creates.

Revision ID: 0002
Revises: 0001
Contract fingerprints: see CONTRACT_FINGERPRINTS.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: None = None
depends_on: None = None

CONTRACT_FINGERPRINTS: dict[str, str] = {
    "aliases": "urn:arxiv-int:contract:aliases:1.0.0@1.0.0:a561948012ae0f628c1e138304c902213acdd7d7c4d498d8df4b8e1859251d32",
    "anomaly-findings": "urn:arxiv-int:contract:anomaly-findings:1.0.0@1.0.0:4df06b330e215f4667aa60f05b5d216a75a8271f6560094df85574acc529c0ad",
    "catalogs": "urn:arxiv-int:contract:catalogs:1.0.0@1.0.0:b22834a1446f8709cb247f26262a511174c1e5dd95f1f40507762c133260e737",
    "chunks": "urn:arxiv-int:contract:chunks:1.0.0@1.0.0:307de21efa13da3e18d6dfc8393d9ea9d7c499023dfad346163dab3f32986cd9",
    "classification-classes": "urn:arxiv-int:contract:classification-classes:1.0.0@1.0.0:f339f590b392ce6e346e197b81085c268cb874b360765aa83342abfc4d82ad61",
    "document-path-events": "urn:arxiv-int:contract:document-path-events:1.0.0@1.0.0:f1c555061b5c0a70599cbec8bf93e5c76fad15c3f0ca9a008f1db15beb9f6ab8",
    "documents": "urn:arxiv-int:contract:documents:1.0.0@1.0.0:310be9094a64330b47ab31641053480fce0d90287febb43b185f9f63b9508bb9",
    "domain-artifacts-bom": "urn:arxiv-int:contract:domain-artifacts-bom:1.0.0@1.0.0:0e834538c0a06ef2d2982cbf51dcba914130681a19c34554b53524f65f51bc9f",
    "domain-artifacts-invoice-payment": "urn:arxiv-int:contract:domain-artifacts-invoice-payment:1.0.0@1.0.0:e804bf161026cc914ff628e80d1ad2d64b34222f347a7acac6103e68c28e5a1f",
    "domain-artifacts-registry": "urn:arxiv-int:contract:domain-artifacts-registry:1.0.0@1.0.0:61f501c3551539e3dd62a9165aa6c4824296163e07274313a4015abdf0c79ded",
    "domain-artifacts-relationship-map": "urn:arxiv-int:contract:domain-artifacts-relationship-map:1.0.0@1.0.0:0e69610485706859628856a1c1b197bbed52bb2c1cf61367e9b6930ac5ebed71",
    "domain-artifacts-supply-chain": "urn:arxiv-int:contract:domain-artifacts-supply-chain:1.0.0@1.0.0:33903f91359648be4f3a9cafb82f229bfa61c74430d00988d7c7b52119a54fbc",
    "duplicate-groups": "urn:arxiv-int:contract:duplicate-groups:1.0.0@1.0.0:d4193c56fcaca0c0a8756bf932f8ce79e019e28f6fcd8c27f647522b026b3146",
    "embeddings": "urn:arxiv-int:contract:embeddings:1.0.0@1.0.0:aaab1f6568f261e4beec82c080adc97fd9fce7657079038da91ee4a89b599504",
    "evaluation-items": "urn:arxiv-int:contract:evaluation-items:1.0.0@1.0.0:4872b90c395c64cf24c72e4bba2c062dc4a3f48da1596b8096250931c6df70b0",
    "facts": "urn:arxiv-int:contract:facts:1.0.0@1.0.0:d53461b5a7070b3c34a3041e3fce345435aca25afc16866c53a8105159319969",
    "mentions": "urn:arxiv-int:contract:mentions:1.0.0@1.0.0:72bb044006f29893aa53a489944a56b21a090f9b7a85b46f3a41bf55bde4e94d",
    "normalized-documents": "urn:arxiv-int:contract:normalized-documents:1.0.0@1.0.0:d511e35c8f10bde8b949c2ae9bb71043bb6d0ce3d86f4b5979453e96544832c9",
    "objects": "urn:arxiv-int:contract:objects:1.0.0@1.0.0:aa5b00325935c7f69a3c656bdd632c933c0f7b26f65df199804b354f076df18a",
    "ontology-terms": "urn:arxiv-int:contract:ontology-terms:1.0.0@1.0.0:c9b2bf052d617fa9387f34dd1568bb46f6d89a46ce0205b73d65e35c45bc5e41",
    "source-occurrences": "urn:arxiv-int:contract:source-occurrences:1.0.0@1.0.0:2c6102d0cf82a82e0199ed780ac01ecafb561c4c7cf3f15789643945446ffd75",
    "spans": "urn:arxiv-int:contract:spans:1.0.0@1.0.0:499653b788b2a74e7afa78eb2cc3e082fd9cad7cd2a3fdd7c3bd23901902307b",
    "topics": "urn:arxiv-int:contract:topics:1.0.0@1.0.0:7f317a00986dae893ed207882df478882503d7fbde678d9cb7c76d6b681e5151",
    "transactions": "urn:arxiv-int:contract:transactions:1.0.0@1.0.0:304478e93fdd2d2145ffcb79b902ab56f7e360c7ac89aa53ea8de65074a5b870",
}
REVIEW_NOTES: tuple[str, ...] = ()
IRREVERSIBLE_REASON: str = ""


def upgrade() -> None:
    """Apply the frozen operations reviewed with this revision."""
    op.execute("CREATE SCHEMA IF NOT EXISTS corpus")
    op.create_table(
        "classification_classes",
        sa.Column("scheme_class_id", sa.Text(), nullable=False, comment=None),
        sa.Column("scheme_id", sa.Text(), nullable=False, comment=None),
        sa.Column("class_id", sa.Text(), nullable=False, comment=None),
        sa.Column("namespace", sa.Text(), nullable=False, comment=None),
        sa.Column("code", sa.Text(), nullable=True, comment=None),
        sa.Column("parent_class_id", sa.Text(), nullable=True, comment=None),
        sa.Column("ancestor_path", sa.Text(), nullable=False, comment=None),
        sa.Column("depth", sa.BigInteger(), nullable=False, comment=None),
        sa.Column("class_kind", sa.Text(), nullable=False, comment=None),
        sa.Column("caption_en", sa.Text(), nullable=True, comment=None),
        sa.Column("caption_ru", sa.Text(), nullable=True, comment=None),
        sa.Column("caption_uk", sa.Text(), nullable=True, comment=None),
        sa.Column("captions_json", sa.Text(), nullable=False, comment=None),
        sa.Column("crosswalk_json", sa.Text(), nullable=False, comment=None),
        sa.Column("path_token", sa.Text(), nullable=False, comment=None),
        sa.Column("slug", sa.Text(), nullable=True, comment=None),
        sa.Column("scheme_version", sa.Text(), nullable=False, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.PrimaryKeyConstraint("scheme_class_id", name="pk_classification_classes"),
        schema="corpus",
        comment="Frozen classes of one versioned subject-taxonomy classification scheme: taxonomy classes, operator extensions and the unclassified/unreadable outcomes, with parent closure, multilingual captions, source crosswalk, and reversible path tokens.",
    )


def downgrade() -> None:
    """Reverse the frozen operations, or refuse when data cannot be restored."""
    op.drop_table("classification_classes", schema="corpus")
