#!/usr/bin/env bash
# Refresh the bundled intermediate CA used to verify zgksiechnice.pl.
#
# The server does not send its intermediate certificate, so the integration
# bundles it. When the site renews with a different intermediate, run this
# script: it reads the "CA Issuers" URL from the live leaf certificate,
# downloads the intermediate, verifies it completes the chain, and writes it
# to cyber_folks_ca.pem.
set -euo pipefail

HOST="zgksiechnice.pl"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CA_FILE="$REPO_ROOT/custom_components/zgk_siechnice/cyber_folks_ca.pem"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo | openssl s_client -connect "$HOST:443" -servername "$HOST" 2>/dev/null \
    | openssl x509 > "$TMP/leaf.pem"

echo "Leaf:   $(openssl x509 -in "$TMP/leaf.pem" -noout -issuer)"

CA_URL="$(openssl x509 -in "$TMP/leaf.pem" -noout -ext authorityInfoAccess \
    | sed -n 's/.*CA Issuers - URI:\(.*\)/\1/p' | head -1)"
if [[ -z "$CA_URL" ]]; then
    echo "No CA Issuers URL in leaf certificate" >&2
    exit 1
fi
echo "Fetch:  $CA_URL"
curl -fsS -o "$TMP/ca.cer" "$CA_URL"

# The repository may serve DER or PEM.
openssl x509 -inform DER -in "$TMP/ca.cer" -out "$TMP/ca.pem" 2>/dev/null \
    || openssl x509 -in "$TMP/ca.cer" -out "$TMP/ca.pem"

echo "CA:     $(openssl x509 -in "$TMP/ca.pem" -noout -subject -enddate | paste -sd ' ' -)"

# Verify the same way the integration does (Python >= 3.13 default context).
python3 -I - "$HOST" "$TMP/ca.pem" <<'EOF'
import socket, ssl, sys
host, cafile = sys.argv[1], sys.argv[2]
ctx = ssl.create_default_context()
ctx.load_verify_locations(cafile=cafile)
with socket.create_connection((host, 443), timeout=15) as s:
    with ctx.wrap_socket(s, server_hostname=host):
        print("Verify: OK")
EOF

if cmp -s "$TMP/ca.pem" "$CA_FILE"; then
    echo "Bundled CA is already up to date."
else
    command cp -f "$TMP/ca.pem" "$CA_FILE"
    echo "Updated $CA_FILE"
fi
