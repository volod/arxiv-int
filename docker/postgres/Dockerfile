# syntax=docker/dockerfile:1.7

# Project-owned ParadeDB Community + Apache AGE image for one PostgreSQL major.
# Build with: make postgres-image

ARG PARADEDB_IMAGE=paradedb/paradedb:0.25.6-pg17
ARG PARADEDB_DIGEST=sha256:044b8cc5b40159714e88e3f546fc74de11cf215c030190cc82c6627015d728ea

FROM ${PARADEDB_IMAGE}@${PARADEDB_DIGEST} AS age-builder
ARG AGE_GIT_SHA=e1467f12e0b1d15dd35d3ab93f057a7112d425b8
ARG POSTGRES_MAJOR=17
USER root
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    flex \
    bison \
    libreadline-dev \
    zlib1g-dev \
    "postgresql-server-dev-${POSTGRES_MAJOR}" \
  && rm -rf /var/lib/apt/lists/*
WORKDIR /tmp/age
RUN curl -fsSL "https://github.com/apache/age/archive/${AGE_GIT_SHA}.tar.gz" \
    | tar -xz --strip-components=1 \
  && make PG_CONFIG="/usr/lib/postgresql/${POSTGRES_MAJOR}/bin/pg_config" install \
  && install -d /opt/age-install/lib /opt/age-install/extension /opt/age-install/notice \
  && cp "/usr/lib/postgresql/${POSTGRES_MAJOR}/lib/age.so" /opt/age-install/lib/ \
  && cp "/usr/share/postgresql/${POSTGRES_MAJOR}/extension"/age* /opt/age-install/extension/ \
  && cp /tmp/age/NOTICE /opt/age-install/notice/AGE-NOTICE \
  && cp /tmp/age/LICENSE /opt/age-install/notice/AGE-LICENSE

FROM ${PARADEDB_IMAGE}@${PARADEDB_DIGEST}
ARG PARADEDB_IMAGE
ARG PARADEDB_DIGEST
ARG POSTGRES_MAJOR=17
ARG POSTGRES_VERSION=17.11
ARG PG_SEARCH_VERSION=0.25.6
ARG VECTOR_VERSION=0.8.4
ARG AGE_GIT_SHA=e1467f12e0b1d15dd35d3ab93f057a7112d425b8
ARG AGE_VERSION=1.7.0
ARG IMAGE_TAG=17-0.25.6-age1.7.0

USER root
COPY --from=age-builder /opt/age-install/lib/age.so \
  /usr/lib/postgresql/${POSTGRES_MAJOR}/lib/age.so
COPY --from=age-builder /opt/age-install/extension/ \
  /usr/share/postgresql/${POSTGRES_MAJOR}/extension/
COPY --from=age-builder /opt/age-install/notice/ /usr/share/arxiv-int/licenses/
COPY docker/postgres/scripts/merge_preload.sh /usr/local/lib/arxiv-int/merge_preload.sh
COPY docker/postgres/initdb/20_arxiv_int_extensions.sh \
  /docker-entrypoint-initdb.d/20_arxiv_int_extensions.sh
COPY docker/postgres/NOTICE /usr/share/arxiv-int/NOTICE
COPY docker/postgres/pins.env /usr/share/arxiv-int/pins.env

RUN chmod 0755 /usr/local/lib/arxiv-int/merge_preload.sh \
    /docker-entrypoint-initdb.d/20_arxiv_int_extensions.sh \
  && /usr/local/lib/arxiv-int/merge_preload.sh \
    "/usr/share/postgresql/${POSTGRES_MAJOR}/postgresql.conf.sample" age \
  && printf '%s\n' \
    '{' \
    "  \"paradedb_image\": \"${PARADEDB_IMAGE}@${PARADEDB_DIGEST}\"," \
    "  \"postgres_major\": \"${POSTGRES_MAJOR}\"," \
    "  \"postgres_version\": \"${POSTGRES_VERSION}\"," \
    "  \"pg_search_version\": \"${PG_SEARCH_VERSION}\"," \
    "  \"vector_version\": \"${VECTOR_VERSION}\"," \
    "  \"age_git_sha\": \"${AGE_GIT_SHA}\"," \
    "  \"age_version\": \"${AGE_VERSION}\"," \
    "  \"image_tag\": \"${IMAGE_TAG}\"" \
    '}' > /usr/share/arxiv-int/extension-pins.json \
  && chown -R postgres:postgres /usr/share/arxiv-int \
  && chmod 0644 /usr/share/arxiv-int/NOTICE \
    /usr/share/arxiv-int/pins.env \
    /usr/share/arxiv-int/extension-pins.json \
    /usr/share/arxiv-int/licenses/*

LABEL org.opencontainers.image.title="arxiv-int postgres" \
  org.opencontainers.image.description="Pinned ParadeDB Community plus Apache AGE" \
  org.arxiv-int.postgres.major="${POSTGRES_MAJOR}" \
  org.arxiv-int.paradedb.digest="${PARADEDB_DIGEST}" \
  org.arxiv-int.age.git_sha="${AGE_GIT_SHA}" \
  org.arxiv-int.age.version="${AGE_VERSION}" \
  org.arxiv-int.image.tag="${IMAGE_TAG}"

# Keep the base image user (root entrypoint) so Compose may set RUNTIME_UID.
