(ifdd-unit-index)=
# {{ cookiecutter.ifdd_unit_prj_name }} (unit)

The static content service `unit` of an IFDD node: it serves the units and
quantity kinds that the vocabularies and the documents refer to. It runs the upstream nginx image as an unprivileged user behind the
proxy and builds no image of its own: the configuration and the content are
mounted read-only. This chapter describes the instance
`{{ cookiecutter.ifdd_unit_prj_slug }}`, generated from the template
`ifdd-de/unit`, from the point of view of the people who set it up, run and
secure it.

| | |
|---|---|
| Host | `{{ cookiecutter.ifdd_unit_host }}` (default of `IFDD_UNIT_HOST` in `.env`; routed by the proxy) |
| Base URL | `{{ cookiecutter.ifdd_unit_url }}` (`ifdd_unit_url`, shared) |
| Image | `{{ cookiecutter.ifdd_nginx_image }}` (shared by schema, type and unit) |
| Content | the directory `IFDD_UNIT_CONTENT_DIR` in `.env`, usually a clone of a separate content repository |
| Network | `{{ cookiecutter.ifdd_proxy_network }}` |
| Development | `http://127.0.0.1:{{ cookiecutter.ifdd_unit_dev_port }}/` |

## What the instance contains

The nginx configuration (`nginx/default.conf`, `nginx/mime.types`), two
compose files, `.env`, and example content in `examples/json-ld/`. The real
content is not part of the instance: it lives in its own repository, whose
clone is mounted read-only. `ifdd-de/schema`, `ifdd-de/type` and
`ifdd-de/unit` share this structure.

## Units and quantity kinds

A namespace is one directory with one document, `<namespace>/index.jsonld`,
holding all of its units and quantity kinds in `@graph`. nginx answers the
namespace IRI (`<namespace>/`) and every IRI below it (`<namespace>/<name>`)
with that document; a client finds its node by `@id`. So a unit IRI in the
data can be opened in a browser and shows its meaning, and a program reads
the same JSON-LD. Files that exist are served as they are; an IRI of an
unknown namespace answers 404. Keep the IRIs in the documents equal to the
URLs they are served at (below `{{ cookiecutter.ifdd_unit_url }}`).

The examples use standard vocabularies only: `rdfs:label` and
`rdfs:comment` per language (`en`, `de`), `rdfs:isDefinedBy`,
`qudt:hasQuantityKind`, `qudt:applicableUnit`, `qudt:symbol` and
`skos:exactMatch` (the matching QUDT IRI).

## Architecture

```{mermaid}
flowchart LR
  Clients[browsers, services] -->|HTTPS| Proxy[proxy: Traefik]
  Proxy -->|"{{ cookiecutter.ifdd_unit_host }}, port 8080"| Nginx[unit: nginx]
  Nginx -->|read-only| Content[(content clone)]
  Repo[content repository] -->|git pull| Content
```

| Who | Uses this service for |
|---|---|
| ui | units and their symbols (in the browser, cross-origin) |
| type | its vocabularies refer to units and quantity kinds here |
| ct | the fake data of its profiles names units of this service |
| people and programs | a unit IRI from the data, opened directly |

## Chapters

```{toctree}
:maxdepth: 2

setup
build-release
operations
security
troubleshooting
reference
```

The values of the variables of this instance and how they relate to the
other services are listed in the chapter on the service instances
({ref}`ifdd-instances-static`).
