"""Static checks of this instance.

They read the files as they are in this repository and assert what the
template promises. Docker is not needed; if an nginx binary is installed, the
configuration is also loaded by nginx itself. tests/smoke.sh covers the
running container.
"""

import json
import os
import re
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SERVICE = "unit"
PREFIX = "IFDD_UNIT_"
COMPOSE_FILES = ["docker-compose-production.yml", "docker-compose-development.yml"]
NGINX_CONF = ROOT / "nginx" / "default.conf"
EXAMPLES = ROOT / "examples" / "json-ld"


def load(path):
    return yaml.safe_load(Path(path).read_text())


def service(compose_file):
    return load(ROOT / compose_file)["services"][SERVICE]


def labels(compose_file):
    return service(compose_file)["labels"]


def nginx_conf():
    return NGINX_CONF.read_text()


def location_block(prefix):
    """The body of the first location block whose header starts with prefix."""
    text = nginx_conf()
    start = text.index(prefix)
    depth, begin = 0, text.index("{", start)
    for index in range(begin, len(text)):
        depth += {"{": 1, "}": -1}.get(text[index], 0)
        if depth == 0:
            return text[begin:index]
    raise AssertionError(f"unbalanced braces after {prefix!r}")


# --- compose -----------------------------------------------------------------

@pytest.mark.parametrize("compose_file", COMPOSE_FILES)
def test_compose_file_parses(compose_file):
    assert service(compose_file)["image"]


@pytest.mark.parametrize("compose_file", COMPOSE_FILES)
def test_nothing_from_dotenv_reaches_the_container(compose_file):
    # .env only feeds the ${...} interpolation; nginx needs none of it.
    assert "env_file" not in service(compose_file)
    assert "environment" not in service(compose_file)


@pytest.mark.parametrize("compose_file", COMPOSE_FILES)
def test_no_router_tls_or_entrypoint_labels(compose_file):
    # A router tls section replaces the TLS configuration of the proxy entry
    # point, Let's Encrypt resolver included; routers without entrypoints
    # attach to the default entry point. See the README of ifdd-de/proxy.
    for label in labels(compose_file):
        assert ".tls" not in label and ".entrypoints" not in label, label


@pytest.mark.parametrize("compose_file", COMPOSE_FILES)
def test_router_and_service_share_one_name(compose_file):
    routers = {m.group(1) for label in labels(compose_file) if (m := re.match(r"traefik\.http\.routers\.([^.]+)\.", label))}
    services = {m.group(1) for label in labels(compose_file) if (m := re.match(r"traefik\.http\.services\.([^.]+)\.", label))}
    assert len(routers) == 1 and routers == services


@pytest.mark.parametrize("compose_file", COMPOSE_FILES)
def test_host_rule_requires_the_host_variable(compose_file):
    rules = [label for label in labels(compose_file) if ".rule=" in label]
    assert rules and all(f"${{{PREFIX}HOST:?" in rule for rule in rules)


@pytest.mark.parametrize("compose_file", COMPOSE_FILES)
def test_load_balancer_port_matches_nginx(compose_file):
    listen = re.search(r"^\s*listen\s+(\d+);", nginx_conf(), re.M).group(1)
    ports = [label.split("=", 1)[1] for label in labels(compose_file) if "loadbalancer.server.port=" in label]
    assert ports == [listen]


@pytest.mark.parametrize("compose_file", COMPOSE_FILES)
def test_docker_network_label_matches_the_external_network(compose_file):
    network = load(ROOT / compose_file)["networks"]["ext-proxy-net"]
    assert network["external"] is True
    assert f"traefik.docker.network={network['name']}" in labels(compose_file)


@pytest.mark.parametrize("compose_file", COMPOSE_FILES)
def test_container_is_hardened(compose_file):
    svc = service(compose_file)
    assert svc["read_only"] is True
    assert "/tmp" in svc["tmpfs"]
    assert svc["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in svc["security_opt"]


@pytest.mark.parametrize("compose_file", COMPOSE_FILES)
def test_health_check_uses_the_health_endpoint(compose_file):
    assert "http://127.0.0.1:8080/healthz" in service(compose_file)["healthcheck"]["test"]
    assert "location = /healthz" in nginx_conf()


@pytest.mark.parametrize("compose_file", COMPOSE_FILES)
def test_configuration_is_mounted_read_only_and_exists(compose_file):
    volumes = service(compose_file)["volumes"]
    for source, target in (("./nginx/default.conf", "/etc/nginx/conf.d/default.conf"), ("./nginx/mime.types", "/etc/nginx/mime.types")):
        assert f"{source}:{target}:ro" in volumes
        assert (ROOT / source).is_file()


def content_volume(compose_file):
    volumes = [v for v in service(compose_file)["volumes"] if v.endswith(":/usr/share/nginx/html:ro")]
    assert len(volumes) == 1, "exactly one read-only content mount expected"
    return volumes[0]


def test_production_refuses_to_start_without_a_content_directory():
    assert content_volume("docker-compose-production.yml").startswith(f"${{{PREFIX}CONTENT_DIR:?")


def test_development_falls_back_to_the_examples():
    assert content_volume("docker-compose-development.yml").startswith(f"${{{PREFIX}CONTENT_DIR:-./examples/json-ld}}")
    assert EXAMPLES.is_dir()


def test_development_port_is_bound_to_loopback_only():
    assert all(port.startswith("127.0.0.1:") for port in service("docker-compose-development.yml")["ports"])


def test_production_publishes_no_port():
    assert "ports" not in service("docker-compose-production.yml")


# --- nginx ---------------------------------------------------------------------

def test_hidden_files_are_never_served():
    assert re.search(r"location ~ /\\\.\s*\{\s*return 404;\s*\}", nginx_conf())


def test_cors_headers_are_sent_on_every_response():
    block = location_block("location / ")
    for header in ("Access-Control-Allow-Origin", "Access-Control-Allow-Methods", "Access-Control-Allow-Headers"):
        assert re.search(rf'add_header {header} "[^"]+" always;', block), header


def test_preflight_is_answered_without_content():
    assert re.search(r"if \(\$request_method = OPTIONS\)\s*\{\s*return 204;\s*\}", location_block("location / "))


def test_server_version_is_not_disclosed():
    assert re.search(r"^\s*server_tokens off;", nginx_conf(), re.M)


def test_json_ld_has_its_media_type():
    assert re.search(r"application/ld\+json\s+jsonld;", (ROOT / "nginx" / "mime.types").read_text())


@pytest.mark.skipif(shutil.which("nginx") is None, reason="no nginx binary installed")
def test_nginx_accepts_the_configuration(tmp_path):
    # Mirrors the http block of the unprivileged image closely enough for a
    # syntax and semantics check (includes, directives, contexts).
    main = tmp_path / "nginx.conf"
    main.write_text(
        f"pid {tmp_path}/nginx.pid;\n"
        f"error_log {tmp_path}/error.log;\n"
        "events {}\n"
        "http {\n"
        f"    include {ROOT}/nginx/mime.types;\n"
        "    default_type application/octet-stream;\n"
        f"    access_log {tmp_path}/access.log;\n"
        f"    client_body_temp_path {tmp_path}/client_temp;\n"
        f"    proxy_temp_path {tmp_path}/proxy_temp;\n"
        f"    fastcgi_temp_path {tmp_path}/fastcgi_temp;\n"
        f"    uwsgi_temp_path {tmp_path}/uwsgi_temp;\n"
        f"    scgi_temp_path {tmp_path}/scgi_temp;\n"
        "    sendfile on;\n"
        f"    include {NGINX_CONF};\n"
        "}\n"
    )
    result = subprocess.run(["nginx", "-t", "-q", "-p", str(tmp_path), "-c", str(main)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


# --- files -------------------------------------------------------------------

def test_dotenv_holds_only_variables_of_this_service():
    for line in (ROOT / "dotenv.dist").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            assert line.startswith(PREFIX), line


def test_env_file_is_git_ignored():
    assert ".env" in (ROOT / ".gitignore").read_text().splitlines()


@pytest.mark.parametrize(
    "path",
    sorted(p.relative_to(ROOT).as_posix() for p in EXAMPLES.rglob("*.jsonld")) or [None],
)
def test_json_ld_examples_parse(path):
    if path is None:
        pytest.skip("no .jsonld examples")
    document = json.loads((ROOT / path).read_text())
    assert "@context" in document



# --- vocabularies ----------------------------------------------------------------

def vocabularies():
    return sorted(EXAMPLES.rglob("index.jsonld"))


def test_term_iris_fall_back_to_the_vocabulary_of_their_namespace():
    conf = nginx_conf()
    assert re.search(r"map \$uri \$vocabulary \{\s*~\^\(\?<namespace>\.\*/\)\[\^/\]\+\$\s+\$\{namespace\}index\.jsonld;", conf)
    assert re.search(r"^\s*index index\.jsonld;", conf, re.M)
    assert "try_files $uri $uri/ $vocabulary =404;" in location_block("location / ")


@pytest.mark.parametrize("path", [p.relative_to(ROOT).as_posix() for p in vocabularies()] or [None])
def test_vocabulary_examples(path):
    """One document per namespace: the namespace node first, every @id below it."""
    if path is None:
        pytest.skip("no vocabulary examples")
    document = json.loads((ROOT / path).read_text())
    graph = document["@graph"]
    namespace = graph[0]["@id"]
    assert namespace.endswith(f"/{Path(path).parent.name}/") and graph[0]["@type"] == "owl:Ontology"
    for node in graph:
        assert node["@id"].startswith(namespace), node["@id"]
        assert {"en", "de"} <= set(node.get("label", {})), node["@id"]


@pytest.mark.skipif(shutil.which("nginx") is None, reason="no nginx binary installed")
def test_nginx_serves_vocabularies(tmp_path):
    """A real nginx: namespace and term IRIs answer with the vocabulary as JSON-LD."""
    examples = vocabularies()
    if not examples:
        pytest.skip("no vocabulary examples")
    content = tmp_path / "html"
    shutil.copytree(EXAMPLES, content)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    conf = nginx_conf().replace("listen 8080;", f"listen 127.0.0.1:{port};")
    conf = conf.replace("root /usr/share/nginx/html;", f"root {content};")
    (tmp_path / "default.conf").write_text(conf)
    main = tmp_path / "nginx.conf"
    main.write_text(
        # Started as root, nginx runs its workers as nobody, who cannot read the
        # temporary directory; the test keeps them as root then.
        ("user root;\n" if os.geteuid() == 0 else "")
        + f"pid {tmp_path}/nginx.pid;\nerror_log {tmp_path}/error.log;\nevents {{}}\n"
        f"http {{\n    include {ROOT}/nginx/mime.types;\n    default_type application/octet-stream;\n"
        f"    access_log off;\n    client_body_temp_path {tmp_path}/c;\n    proxy_temp_path {tmp_path}/p;\n"
        f"    fastcgi_temp_path {tmp_path}/f;\n    uwsgi_temp_path {tmp_path}/u;\n    scgi_temp_path {tmp_path}/s;\n"
        f"    include {tmp_path}/default.conf;\n}}\n"
    )
    started = subprocess.run(["nginx", "-p", str(tmp_path), "-c", str(main)], capture_output=True, text=True)
    assert started.returncode == 0, started.stderr
    try:
        time.sleep(0.2)
        namespace = examples[0].parent.relative_to(EXAMPLES).as_posix()
        base = f"http://127.0.0.1:{port}/{namespace}/"
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for url in (base, base + "some_term"):
            with opener.open(url, timeout=5) as answer:
                assert answer.status == 200
                assert answer.headers["Content-Type"].startswith("application/ld+json")
                assert answer.headers["Access-Control-Allow-Origin"]
                assert json.loads(answer.read())["@graph"][0]["@id"].endswith(f"/{namespace}/")
        try:
            opener.open(f"http://127.0.0.1:{port}/no/such/namespace/term", timeout=5)
            raise AssertionError("an unknown namespace must answer 404")
        except urllib.error.HTTPError as error:
            assert error.code == 404
    finally:
        subprocess.run(["kill", (tmp_path / "nginx.pid").read_text().strip()], check=False)
