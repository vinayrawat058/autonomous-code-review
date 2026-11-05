# OWASP Top 10 — stub notes for Policy RAG (Phase 1)

Replace/expand these with fuller rule text later. Used as seed documents for Layer 2 RAG.

## A01 Broken Access Control
Ensure users cannot act outside their intended permissions. Check authz on every endpoint.

## A02 Cryptographic Failures
Do not store secrets in code. Use strong hashing for passwords. Prefer TLS in transit.

## A03 Injection
Never concatenate untrusted input into SQL, shell, or LDAP queries. Use parameterized APIs.

## A04 Insecure Design
Threat-model high-risk flows. Fail closed. Rate-limit sensitive actions.

## A05 Security Misconfiguration
Disable default credentials, unnecessary ports, and verbose error pages in production.

## A06 Vulnerable and Outdated Components
Pin dependencies; scan for known CVEs; keep frameworks patched.

## A07 Identification and Authentication Failures
Protect session tokens; enforce MFA where needed; avoid weak password rules.

## A08 Software and Data Integrity Failures
Verify package signatures; protect CI/CD; do not deserialize untrusted data blindly.

## A09 Security Logging and Monitoring Failures
Log auth failures and privilege changes; alert on repeated abuse patterns.

## A10 Server-Side Request Forgery (SSRF)
Validate/allowlist outbound URLs; block link-local and metadata endpoints.
