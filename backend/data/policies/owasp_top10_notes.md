# OWASP Top 10 — policy notes for dual-layer RAG

Use these rules when reviewing a code change. Prefer citing a RULE id and a short quote.
Focus on what the diff introduces or removes. Do not invent rules that are not below.

## A01 Broken Access Control
Ensure users cannot act outside their intended permissions. Enforce authorization on every
sensitive endpoint, object access, and admin action — not only at login.

Look for in diffs:
- Missing authz checks on new routes or handlers
- Direct object references (IDs in URLs) without ownership checks
- Client-supplied roles, `is_admin` flags, or tenant IDs trusted without server verification
- CORS or middleware changes that widen who can call an API
- Disabled or bypassed permission decorators / guards

Require:
- Deny by default; allow only after an explicit check
- Server-side verification of resource ownership (IDOR prevention)
- Separate checks for authentication vs authorization

## A02 Cryptographic Failures
Protect data in transit and at rest. Never ship secrets in source, logs, or client bundles.

Look for in diffs:
- Hard-coded passwords, API keys, tokens, or private keys
- Passwords stored or compared in plaintext
- Weak hashing (MD5/SHA1 for passwords) instead of bcrypt/scrypt/argon2
- Custom crypto or disabled TLS verification (`verify=False`)
- Secrets committed to config files or example env files with real values

Require:
- Secrets from environment or a secret manager, not literals
- Strong password hashing with a modern KDF
- TLS for network calls; do not disable certificate verification in production paths

## A03 Injection
Never concatenate untrusted input into SQL, shell, LDAP, HTML, or template interpreters.
Use parameterized APIs and safe encoding.

Look for in diffs:
- SQL built with `+`, f-strings, or `.format()` using user input
- `os.system`, `subprocess` with `shell=True` and unsanitized input
- Dynamic eval/exec on request data
- Raw HTML/template rendering of user content without escaping
- ORM raw() calls that embed request parameters in the query string

Require:
- Parameterized queries / bound parameters (`?`, `%s` with args, or ORM filters)
- Argument lists for subprocess without `shell=True` when possible
- Context-aware output encoding for HTML/JS

## A04 Insecure Design
Threat-model high-risk flows before coding. Fail closed. Assume abuse.

Look for in diffs:
- New money, auth, upload, or admin flows without rate limits or abuse controls
- Trusting client-side only validation
- Features that expose dangerous defaults (open redirect, unrestricted file type)
- Missing step-up checks for sensitive state changes

Require:
- Explicit failure modes that deny access on error
- Rate limiting / lockout for brute-forceable actions
- Documented trust boundaries for new high-risk features

## A05 Security Misconfiguration
Ship secure defaults. Turn off debug and verbose errors in production.

Look for in diffs:
- Debug mode, stack traces, or detailed errors returned to clients
- Default credentials, sample users, or wide-open CORS (`*`) with credentials
- Unnecessary admin ports, directory listing, or leftover test endpoints
- Overly permissive security headers removed or weakened

Require:
- Production configs that disable debug and default accounts
- Least-privilege service accounts and tight CORS allowlists
- Security headers kept intact unless there is a documented reason

## A06 Vulnerable and Outdated Components
Pin dependencies and avoid known-vulnerable libraries.

Look for in diffs:
- Dependency bumps without review, or removal of pins (`>=` with no upper bound on critical libs)
- Vendored copies of old libraries
- Use of packages known for insecure defaults without hardening

Require:
- Locked/pinned versions for production apps
- Prefer maintained libraries; avoid abandoned crypto or auth packages
- After upgrades, skim changelogs for security fixes

## A07 Identification and Authentication Failures
Protect credentials and sessions. Make authentication hard to abuse.

Look for in diffs:
- Weak password rules or storing session tokens in open localStorage without care
- Session IDs in URLs
- Missing invalidation on logout / password change
- Login endpoints without throttling
- MFA bypass paths or “remember me” tokens that never expire

Require:
- Secure session cookie flags (HttpOnly, Secure, SameSite as appropriate)
- Rotate/invalidate sessions on privilege or password change
- Rate-limit authentication attempts

## A08 Software and Data Integrity Failures
Do not trust unsigned updates, CI artifacts, or client-supplied serialized objects.

Look for in diffs:
- `pickle.loads`, unsafe YAML (`yaml.load` without SafeLoader), or deserialize of user blobs
- Installing packages from unverified URLs in CI
- Auto-update hooks that skip signature checks
- Webhook handlers that skip signature verification

Require:
- SafeLoader / explicit schemas for deserialization
- Verify signatures on webhooks and update payloads
- Protect CI/CD secrets and require review on workflow changes

## A09 Security Logging and Monitoring Failures
Log security-relevant events without logging secrets. Alert on abuse.

Look for in diffs:
- Removed logging around auth, access denials, or admin actions
- Logs that print passwords, tokens, or full card numbers
- New sensitive endpoints with no audit trail

Require:
- Log auth failures, access-control failures, and privilege changes
- Redact secrets from logs
- Enough detail to investigate abuse without storing unnecessary PII

## A10 Server-Side Request Forgery (SSRF)
When the server fetches a URL from user input, allowlist destinations.

Look for in diffs:
- `requests.get(user_url)`, `httpx`, `urlopen`, or webhook callbacks with caller-controlled hosts
- PDF/image fetchers that pull remote URLs
- Cloud metadata paths (`169.254.169.254`, link-local) reachable from user input

Require:
- Allowlist schemes/hosts; block link-local, loopback, and metadata IPs
- Do not follow redirects to off-allowlist hosts
- Prefer server-side fixed endpoints over user-supplied URLs
