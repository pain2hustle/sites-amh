#!/usr/bin/env python3
"""Ensure only the authorized Jailyne project; fail closed and never print credentials."""
import json
import os
import urllib.error
import urllib.request

ACCOUNT_ID = 'a08783a0d3715df907ed5ccad38f0dcf'
PROJECT = 'jailyneojeda'
HOST = 'jailyneojeda.pages.dev'
BASE_URL = f'https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/pages/projects'


class SafeFailure(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_project(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('result'), dict):
        raise SafeFailure('Malformed project response; stopped.')
    project = payload['result']
    if payload.get('success') is not True:
        raise SafeFailure('Cloudflare did not confirm the project lookup.')
    if project.get('name') != PROJECT or project.get('subdomain') != HOST:
        raise SafeFailure('Exact Jailyne project/hostname mismatch; no upload allowed.')
    if project.get('production_branch') != 'main':
        raise SafeFailure('Production branch is not main; no settings changed.')


def ensure_project(call):
    # This known existing project verifies access to the intended account before
    # any create operation. It is read only; its build settings never change.
    known = call('GET', '/sites-amh')
    if not isinstance(known, dict) or not isinstance(known.get('result'), dict):
        raise SafeFailure('Malformed account verification response; stopped.')
    known_result = known['result']
    if known.get('success') is not True or known_result.get('name') != 'sites-amh' or known_result.get('subdomain') != 'sites-amh.pages.dev':
        raise SafeFailure('Expected existing account/project identity was not verified; stopped.')
    created = False
    try:
        payload = call('GET', '/' + PROJECT)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        # Explicit user authorization covers this exact named project. One
        # create attempt only; no fallback name, deletion, retry or settings edit.
        payload = call('POST', '', {'name': PROJECT, 'production_branch': 'main'})
        created = True
    validate_project(payload)
    project = payload['result']
    # First-release safety: an already-populated exact-name project may belong
    # to a prior site. Never overwrite it merely because its name matches.
    if project.get('source'):
        raise SafeFailure('Existing Git-integrated project detected; no settings changed or upload allowed.')
    if project.get('latest_deployment') or project.get('canonical_deployment'):
        raise SafeFailure('Existing deployment detected. Review its ownership/content before authorizing an update; no upload allowed.')
    domains = project.get('domains', [])
    if not isinstance(domains, list) or any(d != HOST for d in domains):
        raise SafeFailure('Unexpected custom-domain configuration; no upload allowed.')
    return created


def main():
    token = os.environ.get('CLOUDFLARE_API_TOKEN', '').strip()
    if not token:
        raise SystemExit('Missing encrypted repository secret CLOUDFLARE_API_TOKEN.')
    opener = urllib.request.build_opener(NoRedirect)
    def call(method, suffix, payload=None):
        headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/json'}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        request = urllib.request.Request(BASE_URL + suffix, data=data, headers=headers, method=method)
        with opener.open(request, timeout=25) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise SafeFailure('Unexpectedly large project response; stopped.')
        return json.loads(raw)
    try:
        created = ensure_project(call)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f'Cloudflare project verification/creation failed (HTTP {exc.code}); no alternate name or upload attempted. Response and credentials withheld.') from None
    except (urllib.error.URLError, TimeoutError):
        raise SystemExit('Cloudflare request did not complete. Creation outcome may be uncertain; inspect the exact project before retrying. No upload attempted.') from None
    except SafeFailure as exc:
        raise SystemExit(str(exc)) from None
    except (ValueError, TypeError):
        raise SystemExit('Malformed credential or API response; sensitive details withheld.') from None
    print(('Created and verified' if created else 'Verified existing') + ' jailyneojeda project, exact jailyneojeda.pages.dev hostname and main production branch.')


if __name__ == '__main__':
    main()
