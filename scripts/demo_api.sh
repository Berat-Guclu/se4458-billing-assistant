#!/bin/sh
# Reproduce the billing API through the gateway.
# Graded calls: BASE=https://<api-id>.execute-api.eu-central-1.amazonaws.com
# Local debug against the API container, skipping the gateway: the default below.
set -eu
BASE="${BASE:-http://localhost:18000}"

echo "1. Public query, October 2025, subscriber 5551001"
curl -sS "$BASE/api/v1/bills?subscriberNo=5551001&month=10&year=2025"
echo

echo "2. Protected detail without a token (expect 401)"
curl -sS -i "$BASE/api/v1/bills/detailed?subscriberNo=5551001&month=10&year=2025" | sed -n '1,20p'
echo

echo "3. Login"
TOKEN=$(curl -sS -X POST "$BASE/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"subscriberNo":"5551001","password":"demo123"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["accessToken"])')

echo "4. Detailed October bill"
curl -sS "$BASE/api/v1/bills/detailed?subscriberNo=5551001&month=10&year=2025&page=1&pageSize=5" \
  -H "Authorization: Bearer $TOKEN"
echo

echo "5. Calculate an empty July 2023 bill (outside the seeded history; October stays unpaid)"
curl -sS -X POST "$BASE/api/v1/bills/calculate" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"subscriberNo":"5551001","month":7,"year":2023}'
echo

echo "6. Partial payment of 20 USD on July 2023"
TXN="demo-$(date +%s)"
curl -sS -X POST "$BASE/api/v1/bills/pay" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"subscriberNo\":\"5551001\",\"month\":7,\"year\":2023,\"amount\":20,\"transactionId\":\"$TXN\"}"
echo

echo "7. Duplicate transaction (expect 409)"
curl -sS -i -X POST "$BASE/api/v1/bills/pay" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"subscriberNo\":\"5551001\",\"month\":7,\"year\":2023,\"amount\":20,\"transactionId\":\"$TXN\"}" | sed -n '1,20p'
echo
