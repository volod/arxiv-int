"""SQL fixtures for disposable PostgreSQL extension probes."""

SQL_PROBES = """
SELECT current_setting('server_version_num')::int >= 170000 AS pg17;
SHOW shared_preload_libraries;
SELECT name || '=' || default_version || '/' || COALESCE(installed_version, '-')
FROM pg_available_extensions
WHERE name IN ('age','pg_search','vector')
ORDER BY name;
SELECT extname || '=' || extversion
FROM pg_extension
WHERE extname IN ('age','pg_search','vector')
ORDER BY extname;
"""

BM25_VECTOR_SQL = """
CREATE TABLE probe_docs (id serial PRIMARY KEY, body text);
INSERT INTO probe_docs (body) VALUES ('russian search probe'), ('other text');
CREATE INDEX probe_docs_bm25 ON probe_docs USING bm25 (id, body) WITH (key_field='id');
SELECT id FROM probe_docs WHERE body @@@ 'russian';
CREATE TABLE probe_embeds (id serial PRIMARY KEY, embedding vector(3));
INSERT INTO probe_embeds (embedding)
VALUES ('[1,0,0]'::vector), ('[0,1,0]'::vector);
SELECT id FROM probe_embeds ORDER BY embedding <-> '[1,0,0]'::vector LIMIT 1;
"""

CYPHER_SQL = """
LOAD 'age';
SET search_path = ag_catalog, "$user", public;
SELECT * FROM create_graph('probe_graph');
SELECT * FROM cypher('probe_graph', $$
  CREATE (a:Doc {id: 1, title: 'alpha'})-[:CITES {n: 1}]->(b:Doc {id: 2, title: 'beta'})
  RETURN a, b
$$) AS (a agtype, b agtype);
SELECT * FROM cypher('probe_graph', $$
  MATCH (a:Doc)-[r:CITES]->(b:Doc)
  WHERE a.title = 'alpha'
  RETURN a.title, r.n, b.title
$$) AS (a_title agtype, n agtype, b_title agtype);
SELECT * FROM drop_graph('probe_graph', true);
"""

TXN_SQL = """
BEGIN;
CREATE TEMP TABLE probe_txn (id int PRIMARY KEY);
INSERT INTO probe_txn VALUES (1);
SAVEPOINT s1;
INSERT INTO probe_txn VALUES (2);
ROLLBACK TO SAVEPOINT s1;
INSERT INTO probe_txn VALUES (3);
COMMIT;
SELECT count(*) FROM probe_txn;
"""
