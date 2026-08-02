# Security Policy

## Supported versions

Security fixes are applied to the latest minor release.

## Reporting

Please report vulnerabilities through GitHub private vulnerability reporting rather than a public issue. Do not include real private documents, credentials, or exploit data in an issue.

## Current boundaries

- The API is designed for local development and does not provide authentication.
- Do not expose port 8000 directly to the public internet.
- Uploads are limited to 20 MB and 200 pages, validated by PDF magic bytes, rejected when encrypted, and required to contain an extractable text layer.
- Uploaded corpora are held in process memory and disappear on restart.
- Remote model downloads and web fallback require explicit configuration.
