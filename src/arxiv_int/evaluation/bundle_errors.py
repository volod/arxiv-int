"""Typed failures for evaluation run-bundle publish and verify."""


class BundleError(Exception):
    """A run bundle cannot be published or verified."""


class BundleExistsError(BundleError, FileExistsError):
    """A bundle already occupies the destination name."""


class BundleManifestError(BundleError):
    """Manifest identity or schema is missing or malformed."""


class BundleLayoutError(BundleError):
    """A bundle entry escaped, used a symlink, or is not a regular file."""


class BundleIntegrityError(BundleError):
    """Checksum, size, or file set does not match the manifest."""
