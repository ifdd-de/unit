(ifdd-unit-troubleshooting)=
# Fehlersuche

Bekannte Fehlerbilder. Beginnen mit
`docker compose -f docker-compose-production.yml logs unit` und einem `curl`
der betroffenen URL.

| Symptom | Ursache | Abhilfe |
|---|---|---|
| `docker compose` bricht mit `set IFDD_UNIT_CONTENT_DIR in .env` oder `set IFDD_UNIT_HOST in .env` ab | der Eintrag fehlt in `.env` | ihn setzen ({ref}`ifdd-unit-setup`) |
| `docker compose` bricht mit `refers to undefined volume` ab | `IFDD_UNIT_CONTENT_DIR` ist relativ ohne `./` oder `../` | einen absoluten Pfad nehmen oder mit `./` beginnen |
| jede Datei antwortet 403 oder 404 | das Inhaltsverzeichnis stimmt nicht, oder seine Dateien sind für UID 101 nicht lesbar | Pfad in `.env` und Rechte prüfen (`umask 022` für den Klon) |
| ein Verzeichnis antwortet 403 | Verzeichnislisten sind aus (`ifdd_unit_autoindex`) | erwartet; eine Datei anfragen |
| eine Datei unter `.git` oder einem anderen versteckten Pfad antwortet 404 | versteckte Dateien werden nie ausgeliefert | erwartet |
| ein neuer Inhaltsstand ist nicht zu sehen | Clients nutzen noch ihre zwischengespeicherte Kopie | `{{ cookiecutter.ifdd_unit_cache_max_age }}` Sekunden warten oder ohne Cache neu laden |
| eine Änderung in `nginx/` wirkt nicht | nginx liest seine Konfiguration beim Start | den Dienst neu starten |
| der Browser meldet einen CORS-Fehler | der Ursprung der Seite ist nicht `{{ cookiecutter.ifdd_unit_cors_origin }}`, oder die CSP der Seite erlaubt diesen Host nicht | die Browser-Konsole prüfen; `ifdd_unit_cors_origin` und `connect-src` der aufrufenden Seite |
| der Dienst antwortet hinter dem Proxy 404 | der Router fehlt: Container nicht in `{{ cookiecutter.ifdd_proxy_network }}`, noch nicht healthy, oder `IFDD_UNIT_HOST` weicht vom angefragten Host ab | den Router im Dashboard des Proxys prüfen |
| eine Einheiten-IRI antwortet 404 | ihr Namensraum hat kein `index.jsonld`, oder die IRI liegt nicht unter dem Namensraumverzeichnis | die Einheiten ergänzen oder die IRI korrigieren |
| die UI zeigt keine Einheiten | der Browser kann sie nicht holen (Ursprung nicht erlaubt durch `ifdd_proxy_csp_ui` oder durch den CORS-Ursprung hier), oder der Namensraum fehlt | die Browser-Konsole prüfen; siehe {ref}`ifdd-unit-security` |
