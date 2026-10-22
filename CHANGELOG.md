# Changelog

The version scheme follows the other IFDD templates: `YY.MM.N`.

## [Unreleased]

- New example units `DEG_C` (°C) and `PERCENT_RH` (%RH) with the quantity
  kinds `Temperature` and `RelativeHumidity`, each with `skos:exactMatch` on
  QUDT; used by the time series example `climate.ops.example.ifdd.de` of the
  type template. `examples` is on the skip list: existing instances and the
  content repository take the new units by hand.

## [26.10.2] - 2026-10-14

- Documentation of the instance in `docs/en` and `docs/de` (Sphinx sources,
  MyST Markdown): index, setup, build and release, operations, security,
  troubleshooting, reference. The instance README is now an entry point with
  a quick start, the links, the honesty notes and the license; its former
  sections moved into the documentation.
- `docs/_build/` in `.gitignore` of the instance.
- Template CI: `tests/check_docs.py` checks that both languages match and
  build without warnings (`tests/docs/conf.py`, `tests/docs/requirements.txt`).

- Vocabularies: one document per namespace, `<namespace>/index.jsonld`;
  nginx answers the namespace IRI and every IRI below it with that document
  (`map` + `try_files`), `index index.jsonld`, relative redirects
  (`absolute_redirect off`). Examples: four units (V, kV, A, kA) and two quantity kinds (voltage, electric current), replacing the
  plain-text example `base/name`.
- New shared variable `ifdd_unit_url` (the examples render their IRIs from it),
  checked by the pre-hook.
- `examples` is on the skip list: existing instances and the content
  repository take the new examples by hand.

## [26.10.1]

First release as `ifdd-de/unit`, successor of `dd4-unit`.

- Variables renamed from `dd4_unit_*` to `ifdd_unit_*`, environment
  variables from `DD4_UNIT_*` to `IFDD_UNIT_*`.
- No image of its own any more: runs the upstream unprivileged nginx image
  (`ifdd_nginx_image`), configuration and content mounted read-only.
  `Dockerfile.nginx`, the image tag and `dd4_registry_url` are gone.
- Content from a separate clone (`IFDD_UNIT_CONTENT_DIR`, required in
  production); the template ships examples in `examples/json-ld` only.
- No router `tls`/`certresolver`/`entrypoints` labels, and therefore no
  `..._enable_tls`/`..._enable_letsencrypt` variables: the proxy sets TLS on
  its entry point. Router and service are named after the slug.
- Proxy network from `ifdd_proxy_network`, with `traefik.docker.network`.
- nginx: CORS on every response (`always`), preflight 204, hidden files never
  served, `server_tokens off`, gzip for JSON-LD, `Cache-Control` from
  `ifdd_unit_cache_max_age`, directory listing from `ifdd_unit_autoindex`,
  `/healthz`, port 8080, IPv4 only.
- Container: read-only root file system, `cap_drop: ALL`,
  `no-new-privileges`, health check, memory limit; no `env_file`.
- Development compose file with a port on 127.0.0.1.
- Hooks: validation of all values; the post hook only creates `.env` (the
  unused password generator of the old hook is gone).
- Static checks and a Docker smoke test in every instance; template render,
  check and smoke test over two fixtures; cruft update test.
