#!/usr/bin/env python3
"""One fixed GET; stdout contains only static labels and bounded numeric codes."""
import json
import os
import urllib.error
import urllib.request

ACCOUNT_ID = 'a08783a0d3715df907ed5ccad38f0dcf'
URL = f'https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/pages/projects/sites-amh'
MAX_BODY = 16_384
CODE_LABELS = {
    9106: 'authentication_failed',
    9109: 'unauthorized',
    10000: 'authentication_error',
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def safe_error_codes(raw):
    """Ignore all API message text, headers, IDs, nested metadata and raw bodies."""
    if not isinstance(raw, bytes) or len(raw) > MAX_BODY:
        return []
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeError):
        return []
    if not isinstance(body, dict) or not isinstance(body.get('errors'), list):
        return []
    codes = []
    for error in body['errors'][:8]:
        code = error.get('code') if isinstance(error, dict) else None
        # bool, string tokens, token IDs, large integers and raw text cannot pass.
        if type(code) is int and 1000 <= code <= 999_999 and code not in codes:
            codes.append(code)
    return codes


def diagnose(token, opener):
    token = token.strip()
    if not token:
        return {'outcome': 'missing_secret'}, 1
    request = urllib.request.Request(
        URL,
        headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json'},
        method='GET',
    )
    try:
        with opener.open(request, timeout=25) as response:
            status = response.status
            raw = response.read(MAX_BODY + 1)
        if len(raw) > MAX_BODY:
            return {'outcome': 'response_too_large'}, 1
        payload = json.loads(raw)
        result = payload.get('result') if isinstance(payload, dict) else None
        matched = (status == 200 and payload.get('success') is True
                   and isinstance(result, dict) and result.get('name') == 'sites-amh'
                   and result.get('subdomain') == 'sites-amh.pages.dev')
        if matched:
            return {'outcome': 'pages_read_authorized', 'http_status': 200,
                    'project_identity': 'matched'}, 0
        return {'outcome': 'unexpected_response_or_identity'}, 1
    except urllib.error.HTTPError as exc:
        try:
            codes = safe_error_codes(exc.read(MAX_BODY + 1))
        except Exception:
            codes = []
        status = exc.code if type(exc.code) is int and 100 <= exc.code <= 599 else 0
        return {'outcome': 'http_rejection', 'http_status': status,
                'cloudflare_error_codes': codes,
                'categories': [CODE_LABELS.get(code, 'unclassified_code') for code in codes]}, 1
    except (urllib.error.URLError, TimeoutError):
        return {'outcome': 'network_or_timeout'}, 1
    except Exception:
        # Library exceptions may quote a malformed Authorization value. Never
        # print exception text, repr, request objects, headers, or a traceback.
        return {'outcome': 'malformed_input_or_response'}, 1


def main():
    try:
        report, status = diagnose(
            os.environ.get('CLOUDFLARE_API_TOKEN', ''),
            urllib.request.build_opener(NoRedirect),
        )
    except Exception:
        report, status = {'outcome': 'local_setup_error'}, 1
    print(json.dumps(report, sort_keys=True))
    return status


if __name__ == '__main__':
    raise SystemExit(main())
