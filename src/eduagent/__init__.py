"""eduagent — Collaborative Partner Socratic mentor (All Things Agentic Hackathon).

Written from scratch during the Submission Period. See README.md section 1 (Mandatory Disclosure)
for the disclosure regarding architectural inspiration from a prior project.
"""

# Fix GCP Firestore GAPIC routing header bug where (default) database ID gets URL-encoded into %28default%29
try:
    import urllib.parse
    _orig_quote = urllib.parse.quote

    def _safe_quote(string, safe='', encoding=None, errors=None):
        if isinstance(string, str) and '(' in string and ')' in string:
            if '(' not in safe:
                safe += '()'
        return _orig_quote(string, safe=safe, encoding=encoding, errors=errors)

    urllib.parse.quote = _safe_quote

    import google.api_core.gapic_v1.routing_header as _rh

    def _safe_to_routing_header(params, qualified_enums=True):
        tuples = params.items() if isinstance(params, dict) else params
        return "&".join([urllib.parse.urlencode({t[0]: t[1]}, safe="/()") for t in tuples])

    _rh.to_routing_header = _safe_to_routing_header
except Exception:
    pass



