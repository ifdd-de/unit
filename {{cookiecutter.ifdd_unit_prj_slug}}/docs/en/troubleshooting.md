(ifdd-unit-troubleshooting)=
# Troubleshooting

Known failure patterns. Start with
`docker compose -f docker-compose-production.yml logs unit` and a `curl` of
the failing URL.

| Symptom | Cause | Remedy |
|---|---|---|
| `docker compose` stops with `set IFDD_UNIT_CONTENT_DIR in .env` or `set IFDD_UNIT_HOST in .env` | the entry is missing in `.env` | set it ({ref}`ifdd-unit-setup`) |
| `docker compose` stops with `refers to undefined volume` | `IFDD_UNIT_CONTENT_DIR` is relative without `./` or `../` | use an absolute path or start it with `./` |
| every file answers 403 or 404 | the content directory is wrong, or its files are not readable for UID 101 | check the path in `.env` and the permissions (`umask 022` for the clone) |
| a directory answers 403 | directory listings are off (`ifdd_unit_autoindex`) | expected; request a file |
| a file under `.git` or another hidden path answers 404 | hidden files are never served | expected |
| a new content state is not visible | clients still use their cached copy | wait `{{ cookiecutter.ifdd_unit_cache_max_age }}` seconds, or reload without cache |
| a change in `nginx/` has no effect | nginx reads its configuration at start | restart the service |
| the browser reports a CORS error | the page's origin is not `{{ cookiecutter.ifdd_unit_cors_origin }}`, or the CSP of the page does not allow this host | check the browser console; `ifdd_unit_cors_origin`, and `connect-src` of the calling page |
| the service is 404 behind the proxy | the router is missing: container not on `{{ cookiecutter.ifdd_proxy_network }}`, not healthy yet, or `IFDD_UNIT_HOST` differs from the requested host | check the router in the proxy dashboard |
| a unit IRI answers 404 | its namespace has no `index.jsonld`, or the IRI is not below the namespace directory | add the units, or fix the IRI |
| the UI shows no units | the browser cannot fetch them (origin not allowed by `ifdd_proxy_csp_ui` or by the CORS origin here), or the namespace is missing | check the browser console; see {ref}`ifdd-unit-security` |
