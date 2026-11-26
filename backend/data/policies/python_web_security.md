# Python / web app secure-coding notes

Companion rules for Python services (Flask/FastAPI/Django-style). Use with OWASP Top 10.
Cite these when the diff is Python-specific.

## PY01 SQL and ORM safety
Never build SQL with string concatenation or f-strings from request data.
Use bound parameters (`cursor.execute(sql, (value,))`), SQLAlchemy `text()` with binds,
or ORM filters. Prefer `?` / named params over interpolating into the query string.

## PY02 Command execution
Avoid `os.system` and `subprocess` with `shell=True` when arguments come from users.
Pass an argument list (`subprocess.run(["cmd", arg], check=True)`) and validate inputs.
Do not call `eval` / `exec` on request bodies.

## PY03 Secrets and settings
Load secrets from environment variables or a secret store. Do not hard-code API keys,
passwords, or tokens in `.py` files. Keep `.env` out of git; never log secret values.

## PY04 Deserialization
Do not `pickle.loads` untrusted bytes. For YAML use `safe_load`. Prefer JSON with
schema validation (Pydantic) for API payloads.

## PY05 SSRF and outbound HTTP
When fetching remote URLs, allowlist hosts. Do not pass raw user URLs to `requests`,
`httpx`, or `urllib` without checks. Disable or carefully control redirects.

## PY06 Path traversal
When reading/writing files from user-supplied names, resolve paths under a fixed base
directory and reject `..` escapes. Do not concatenate user paths onto system roots.

## PY07 Authn/Authz in frameworks
Apply auth dependencies/middleware on every sensitive route. Do not trust
`request.json["user_id"]` for authorization — load the principal from the session/token
and check permissions server-side.

## PY08 XSS and templates
Escape untrusted content in HTML templates. Avoid `Markup(...)` / `|safe` on user input.
For JSON APIs, set correct content types so browsers do not sniff HTML.
