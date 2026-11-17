# ifdd-de/unit

cookiecutter/cruft template for the static content service `unit` of IFDD.
It serves the documents of the `unit` namespace as static files.

The generated instance runs the upstream unprivileged nginx image behind the
IFDD proxy (`ifdd-de/proxy`) and builds no image of its own. The content is
not part of the instance: it lives in a separate repository whose clone is
mounted read-only. `ifdd-de/schema`, `ifdd-de/type` and `ifdd-de/unit` share
the same structure and differ only in names and examples.

## Generate an instance

```bash
cruft create --no-input --checkout <tag> \
  --config-file cookiecutter_all.yaml \
  --skip .env --skip examples \
  --output-dir ../instances https://github.com/ifdd-de/unit
```

The skip list keeps `.env` and the examples, both instance-owned, out of
every later `cruft update`. Then set `IFDD_UNIT_CONTENT_DIR` in `.env` of
the instance (see its README).

## Variables

| Variable | Default | Meaning |
|---|---|---|
| `ifdd_unit_prj_name`, `ifdd_unit_prj_slug` | `IFDD Unit`, derived | name; the slug names the directory and the Traefik router |
| `ifdd_unit_host` | `unit` | host name routed to the service (default for `IFDD_UNIT_HOST` in `.env`) |
| `ifdd_unit_dev_port` | `8083` | port on 127.0.0.1 in development (default for `IFDD_UNIT_DEV_PORT`) |
| `ifdd_unit_autoindex` | `y` | directory listings |
| `ifdd_unit_cors_origin` | `*` | `Access-Control-Allow-Origin`: `*` or one origin |
| `ifdd_unit_cache_max_age` | `300` | `Cache-Control` max-age in seconds, `0` for `no-cache`; **a starting value, not measured** |
| `ifdd_unit_memory_limit` | `128M` | memory limit of the container; **a starting value, not measured** |
| `ifdd_nginx_image` | `nginxinc/nginx-unprivileged:1.30.6-alpine-slim` | nginx image; for a mirror, the image in the internal registry |
| `ifdd_proxy_network` | `proxy-net` | Docker network of the proxy |
| `ifdd_unit_url` | `http://unit/v1` | base URL of the units and quantity kinds; the examples render their IRIs from it (shared) |

`ifdd_nginx_image` and `ifdd_proxy_network` carry no service prefix: they are
the same for `schema`, `type` and `unit` (the network also for `proxy`).
The pre-generation hook rejects values that would render but not work.

## Vocabularies

A namespace is one directory with one document, `<namespace>/index.jsonld`,
holding all of its units and quantity kinds in `@graph`. nginx answers the namespace IRI
(`<namespace>/`) and every IRI below it (`<namespace>/<name>`) with that
document; a client finds its node by `@id`. So a property or unit IRI in
the data can be opened in a browser and shows its meaning, and a program
reads the same JSON-LD. Files that exist are served as before; an IRI of an
unknown namespace answers 404.

The examples use standard vocabularies only: `rdfs:label` and
`rdfs:comment` per language (`en`, `de`), `rdfs:range`,
`rdfs:isDefinedBy`, `sh:order` (order in the UI), `qudt:hasQuantityKind`,
`qudt:applicableUnit`, `qudt:symbol` and `skos:exactMatch` (the matching
QUDT IRI). The compact form of the examples is what ifdd-ui reads.

## Layout

| Path | Purpose |
|---|---|
| `cookiecutter.json` | variables |
| `hooks/` | validation before, `.env` after generation |
| `{{cookiecutter.ifdd_unit_prj_slug}}/` | the instance, see its README |
| `tests/check_docs.py`, `tests/docs/` | used by `template-test.yml`: the documentation of the instance, see below |
| `tests/fixtures/` | `defaults`, `custom` (slug with hyphen, fixed origin, no-cache, no listing, other network) |

`.github` and `tests` inside the instance are on the copy-without-render list:
GitHub Actions expressions and shell syntax collide with Jinja.

## Documentation of the instance (`docs/`)

Every instance carries its operating documentation as Sphinx sources in
MyST Markdown, in English (`docs/en`) and German (`docs/de`), with the same
files, labels and headings in both. The pages follow the work around the
service: `index` (purpose, content rules, architecture), `setup`,
`build-release`, `operations`, `security`, `troubleshooting`, `reference`.
cookiecutter fills in the values of the instance. The instance README is
only an entry point that links to them. The pages of `ifdd-de/schema`,
`ifdd-de/type` and `ifdd-de/unit` have the same structure; keep them in
step.

The pages have no `conf.py` of their own: they are meant to be copied into a
Sphinx project that documents all services. That project needs `myst_parser`
and `sphinxcontrib.plantuml` (PlantUML with Java and Graphviz).
Labels start with `ifdd-unit-`; references to
`ifdd-instances-static` (the instance chapter of the meta repository)
resolve only there.

Rules for editing the pages in the template:

- change both languages in the same commit;
- no Jinja syntax in examples (`{{`, `{%`, `{#`); wrap such text in
  `{% raw %}`;
- the placeholder check of the CI greps the rendered instance for the text
  `cookiecutter` followed by a dot; do not write it literally.

`tests/check_docs.py` checks a rendered instance: same files, labels and
headings per level in both languages, every label with the prefix, every
reference to an own label resolvable, and a Sphinx build of each language
with `-W` (configuration `tests/docs/conf.py`, versions
`tests/docs/requirements.txt`).

The check runs PlantUML, so it needs Java and Graphviz.
`tests/docs/get_plantuml.sh` downloads the pinned PlantUML jar into the user
cache, checks its SHA-256 and prints its path:

```bash
export IFDD_PLANTUML_JAR="$(tests/docs/get_plantuml.sh)"
```

## CI

| Workflow | Does |
|---|---|
| `template-test.yml` | renders each fixture, checks for leftover placeholders, runs the static checks, checks and builds the documentation (`tests/check_docs.py`), validates both compose files, starts the container in both modes and probes it |
| `template-update-test.yml` | generates from the latest tag, applies the current template with `cruft update`, fails on reject files, runs the static checks |

## Migrating from dd4-unit

The template, its URL and all variable names changed, so `cruft update` cannot
take an existing `dd4-unit` instance across. Generate a new instance, then:

1. Move the content into its own repository and clone it on the host.
2. Carry the host name over: `DD4_UNIT_HOST` → `IFDD_UNIT_HOST`, and set
   `IFDD_UNIT_CONTENT_DIR`.
3. Keep the slug of the old instance (`ifdd_unit_prj_slug`) if other
   configuration refers to its router name.
4. Stop the old container before starting the new one: both announce a
   router for the same host.

## AI assistance

Some parts of this repository, in particular the tests, the test data and the
documentation, were developed or improved with the help of large language
models (LLMs). All changes were reviewed and released by the maintainer.
