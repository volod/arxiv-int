"""Deterministic multilingual caption-overlap classifier with bounded feature preparation."""

import math
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from arxiv_int.classification.model import Candidate, Classification, ClassifierPolicy, PhysicalFile
from arxiv_int.classification.text_features import feature_counts, words
from arxiv_int.classification.vocabulary.model import Scheme
from arxiv_int.classification.vocabulary.outcomes import EXCEPTIONAL_OUTCOMES

_MAX_EVIDENCE = 8


@dataclass(frozen=True, slots=True)
class CaptionVariant:
    """One language-specific self caption with lower-weight ancestor context."""

    features: Mapping[str, float]
    self_features: frozenset[str]
    norm: float


@dataclass(frozen=True, slots=True)
class Prototype:
    """One leaf-class weighted feature profile."""

    class_id: str
    features: Mapping[str, float]
    variants: tuple[CaptionVariant, ...]


class CaptionClassifier:
    """Score bounded file features against multilingual taxonomy leaf captions."""

    def __init__(self, scheme: Scheme, policy: ClassifierPolicy) -> None:
        self.scheme = scheme
        self.policy = policy
        raw = self._raw_profiles()
        document_frequency = Counter(feature for profile in raw.values() for feature in profile)
        total = len(raw)
        self.idf = {
            feature: math.log((total + 1.0) / (count + 1.0)) + 1.0
            for feature, count in document_frequency.items()
        }
        self.prototypes = tuple(
            Prototype(
                class_id,
                features,
                self._caption_variants(class_id),
            )
            for class_id, features in sorted(raw.items())
        )

    def _caption_variants(self, class_id: str) -> tuple[CaptionVariant, ...]:
        """Keep translations separate and add same-language ancestor context."""
        item = self.scheme.classes[class_id]
        variants: list[CaptionVariant] = []
        for language, caption in item.captions:
            self_features = feature_counts(words(caption))
            weighted = self._variant_features(class_id, language, caption)
            norm = sum(
                count * self.policy.weights.self_caption * self.idf[feature]
                for feature, count in self_features.items()
            )
            variants.append(CaptionVariant(weighted, frozenset(self_features), norm))
        return tuple(variants)

    def _variant_features(self, class_id: str, language: str, caption: str) -> dict[str, float]:
        weighted: dict[str, float] = defaultdict(float)
        for feature, count in feature_counts(words(caption)).items():
            weighted[feature] += count * self.policy.weights.self_caption
        for ancestor_id in self.scheme.path(class_id)[:-1]:
            captions = dict(self.scheme.classes[ancestor_id].captions)
            for feature, count in feature_counts(words(captions[language])).items():
                weighted[feature] += count * self.policy.weights.ancestor_caption
        return dict(weighted)

    def _raw_profiles(self) -> dict[str, dict[str, float]]:
        profiles: dict[str, dict[str, float]] = {}
        classes = (
            class_id for class_id in self.scheme.classes if class_id not in EXCEPTIONAL_OUTCOMES
        )
        for class_id in classes:
            profile: dict[str, float] = defaultdict(float)
            item = self.scheme.classes[class_id]
            for language, caption in item.captions:
                for feature, weight in self._variant_features(class_id, language, caption).items():
                    profile[feature] += weight
            profiles[class_id] = profile
        return profiles

    def classify(self, item: PhysicalFile) -> Classification:
        """Return one ordinary or explicit exceptional classification."""
        if item.status != "ready":
            return self._exception("unreadable", f"inventory-{item.reason or 'unreadable'}", item)
        if not item.documents:
            reason = item.extraction_failures[0] if item.extraction_failures else "no-usable-text"
            return self._exception("unreadable", reason, item)
        weighted, positions = self._file_features(item)
        candidates = tuple(self._score(profile, weighted) for profile in self.prototypes)
        ranked = tuple(
            sorted(
                candidates,
                key=lambda value: (
                    -value.score,
                    -self.scheme.depth(value.class_id),
                    value.class_id,
                ),
            )
        )
        best = ranked[0]
        competitor = next(
            (
                candidate
                for candidate in ranked[1:]
                if not self._same_branch(best.class_id, candidate.class_id)
            ),
            None,
        )
        margin = best.score - (competitor.score if competitor is not None else 0.0)
        if (
            best.score < self.policy.primary_threshold
            or margin < self.policy.margin_threshold
            or len(best.matched_terms) < self.policy.minimum_matched_features
        ):
            return Classification(
                "unclassified",
                (),
                ("unclassified",),
                1.0 - best.score,
                ranked[: self.policy.max_alternates + 1],
                self._evidence(best, positions),
                "below-threshold-or-margin",
                tuple(sorted({document.document_id for document in item.documents})),
            )
        alternates = tuple(
            candidate.class_id
            for candidate in ranked[1:]
            if candidate.score >= self.policy.alternate_threshold
            and not self._same_branch(best.class_id, candidate.class_id)
        )[: self.policy.max_alternates]
        return Classification(
            best.class_id,
            alternates,
            self.scheme.path(best.class_id),
            best.score,
            ranked[: self.policy.max_alternates + 1],
            self._evidence(best, positions),
            None,
            tuple(sorted({document.document_id for document in item.documents})),
        )

    def _file_features(
        self, item: PhysicalFile
    ) -> tuple[Mapping[str, float], dict[str, tuple[str, int, int]]]:
        weighted: dict[str, float] = defaultdict(float)
        positions: dict[str, tuple[str, int, int]] = {}
        sources = [("path", item.relative_path, self.policy.weights.path)]
        sources.extend(
            ("title", document.title, self.policy.weights.title) for document in item.documents
        )
        sources.extend(
            (
                document.document_id,
                document.text[: self.policy.max_text_chars],
                self.policy.weights.text,
            )
            for document in item.documents
        )
        for source, text, weight in sources:
            tokens = words(text)
            for feature, count in feature_counts(tokens).items():
                weighted[feature] += count * weight
            folded = text.casefold()
            for token in tokens:
                start = folded.find(token)
                if start >= 0:
                    positions.setdefault(token, (source, start, start + len(token)))
        return weighted, positions

    def _score(self, prototype: Prototype, document: Mapping[str, float]) -> Candidate:
        score = max(self._variant_score(variant, document) for variant in prototype.variants)
        matched = sorted(
            feature[2:]
            for feature in prototype.features
            if feature.startswith("w:") and document.get(feature, 0.0) > 0.0
        )
        return Candidate(
            prototype.class_id,
            min(1.0, score),
            tuple(matched),
        )

    def _variant_score(self, variant: CaptionVariant, document: Mapping[str, float]) -> float:
        if not any(
            feature.startswith("w:") and document.get(feature, 0.0) > 0.0
            for feature in variant.self_features
        ):
            return 0.0
        return sum(
            min(document.get(feature, 0.0), weight) * self.idf[feature]
            for feature, weight in variant.features.items()
        ) / max(variant.norm, 1.0)

    def _same_branch(self, left: str, right: str) -> bool:
        return left in self.scheme.path(right) or right in self.scheme.path(left)

    def _evidence(
        self, candidate: Candidate, positions: dict[str, tuple[str, int, int]]
    ) -> tuple[dict[str, object], ...]:
        evidence = []
        for term in candidate.matched_terms[:_MAX_EVIDENCE]:
            source, start, end = positions[term]
            evidence.append({"source": source, "start": start, "end": end, "term": term})
        return tuple(evidence)

    def _exception(self, outcome: str, reason: str, item: PhysicalFile) -> Classification:
        return Classification(outcome, (), (outcome,), 1.0, (), (), reason, ())
