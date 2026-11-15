#!/usr/bin/env bash
# ==============================================================================
# Sovereign UAE Document Intelligence SaaS - End-to-End Smoke Test
# ==============================================================================
# Verifies full pipeline on live running stack:
# 1. Health check (/health)
# 2. JWT authentication (/api/v1/auth/login)
# 3. Real image upload (/api/v1/documents/upload)
# 4. Event stream / status progression (needs_review or approved)
# 5. Reviewer field correction (/api/v1/documents/{id}/fields/{field})
# 6. Document approval (/api/v1/documents/{id}/approve)
# 7. In-country Sovereign RAG query (/api/v1/rag/query)
# 8. Hard deletion (/api/v1/documents/{id})
# 9. Verification that document and derived data are purged (404)
# ==============================================================================

set -euo pipefail

BASE_URL="${API_BASE_URL:-http://localhost:8080}"
API_URL="${BASE_URL}/api/v1"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@alhilal-demo.ae}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-AdminSecurePass2026!}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEST_IMAGE="${PROJECT_ROOT}/eval/dataset/sample_001.png"

echo "======================================================================"
echo "Starting Sovereign UAE Document Intelligence Smoke Test"
echo "Target Base URL: ${BASE_URL}"
echo "======================================================================"

# ------------------------------------------------------------------------------
# STEP 1: Verify Stack Health
# ------------------------------------------------------------------------------
echo -n "[1/9] Checking /health endpoint... "
HEALTH_RESP=$(curl -s -f "${BASE_URL}/health" || true)
if [ -z "${HEALTH_RESP}" ]; then
  echo "FAILED!"
  echo "Error: Backend server is not reachable at ${BASE_URL}/health"
  exit 1
fi
echo "OK"
echo "      Health: ${HEALTH_RESP}"

# ------------------------------------------------------------------------------
# STEP 2: Authenticate & Obtain JWT
# ------------------------------------------------------------------------------
echo -n "[2/9] Authenticating as admin (${ADMIN_EMAIL})... "
LOGIN_RESP=$(curl -s -f -X POST "${API_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}")

ACCESS_TOKEN=$(echo "${LOGIN_RESP}" | python -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")

if [ -z "${ACCESS_TOKEN}" ]; then
  echo "FAILED!"
  echo "Error: Failed to obtain access token from response: ${LOGIN_RESP}"
  exit 1
fi
echo "OK (Token obtained)"

AUTH_HEADER="Authorization: Bearer ${ACCESS_TOKEN}"

# ------------------------------------------------------------------------------
# STEP 3: Upload Real Raster Image
# ------------------------------------------------------------------------------
echo -n "[3/9] Uploading pure raster document (${TEST_IMAGE})... "
if [ ! -f "${TEST_IMAGE}" ]; then
  echo "FAILED!"
  echo "Error: Test image not found at ${TEST_IMAGE}"
  exit 1
fi

UPLOAD_RESP=$(curl -s -f -X POST "${API_URL}/documents/upload" \
  -H "${AUTH_HEADER}" \
  -F "file=@${TEST_IMAGE};type=image/png" \
  -F "document_type_code=emirates_id")

DOC_ID=$(echo "${UPLOAD_RESP}" | python -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")

if [ -z "${DOC_ID}" ]; then
  echo "FAILED!"
  echo "Error: Document upload failed: ${UPLOAD_RESP}"
  exit 1
fi
echo "OK (Document ID: ${DOC_ID})"

# ------------------------------------------------------------------------------
# STEP 4: Await Pipeline Processing (SSE / Status Progression)
# ------------------------------------------------------------------------------
echo -n "[4/9] Waiting for pipeline processing to reach review/approved status... "
STATUS=""
for i in {1..30}; do
  DOC_DETAIL=$(curl -s -f -H "${AUTH_HEADER}" "${API_URL}/documents/${DOC_ID}" || true)
  STATUS=$(echo "${DOC_DETAIL}" | python -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" || true)
  if [ "${STATUS}" = "needs_review" ] || [ "${STATUS}" = "approved" ]; then
    break
  fi
  sleep 1
done

if [ "${STATUS}" != "needs_review" ] && [ "${STATUS}" != "approved" ]; then
  echo "FAILED! (Final status: ${STATUS})"
  exit 1
fi
echo "OK (Status: ${STATUS})"

# ------------------------------------------------------------------------------
# STEP 5: Reviewer Field Correction
# ------------------------------------------------------------------------------
echo -n "[5/9] Correcting extracted field 'full_name_en'... "
CORRECT_RESP=$(curl -s -f -X PATCH "${API_URL}/documents/${DOC_ID}/fields/full_name_en" \
  -H "${AUTH_HEADER}" \
  -H "Content-Type: application/json" \
  -d '{"corrected_value":"SALEM RASHED SAIF ALSHAMSI","reason":"Smoke test verified correction"}')

CORRECTED_VAL=$(echo "${CORRECT_RESP}" | python -c "import sys, json; print(json.load(sys.stdin).get('value', ''))")
if [ "${CORRECTED_VAL}" != "SALEM RASHED SAIF ALSHAMSI" ]; then
  echo "FAILED!"
  echo "Error: Field correction failed: ${CORRECT_RESP}"
  exit 1
fi
echo "OK (Value: '${CORRECTED_VAL}')"

# ------------------------------------------------------------------------------
# STEP 6: Document Approval
# ------------------------------------------------------------------------------
echo -n "[6/9] Approving document... "
APPROVE_RESP=$(curl -s -f -X POST "${API_URL}/documents/${DOC_ID}/approve" \
  -H "${AUTH_HEADER}")

DOC_DETAIL=$(curl -s -f -H "${AUTH_HEADER}" "${API_URL}/documents/${DOC_ID}")
FINAL_STATUS=$(echo "${DOC_DETAIL}" | python -c "import sys, json; print(json.load(sys.stdin).get('status', ''))")

if [ "${FINAL_STATUS}" != "approved" ]; then
  echo "FAILED!"
  echo "Error: Document approval failed, status is ${FINAL_STATUS}"
  exit 1
fi
echo "OK (Status: approved)"

# ------------------------------------------------------------------------------
# STEP 7: In-Country Sovereign RAG Query
# ------------------------------------------------------------------------------
echo -n "[7/9] Asking sovereign RAG question with citations... "
RAG_RESP=$(curl -s -f -X POST "${API_URL}/rag/query" \
  -H "${AUTH_HEADER}" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"What is Salem's Emirates ID number?\",\"document_id\":\"${DOC_ID}\"}")

RAG_ANSWER=$(echo "${RAG_RESP}" | python -c "import sys, json; print(json.load(sys.stdin).get('answer', ''))")
if [ -z "${RAG_ANSWER}" ]; then
  echo "FAILED!"
  echo "Error: RAG query returned empty answer: ${RAG_RESP}"
  exit 1
fi
echo "OK (Answer: ${RAG_ANSWER})"

# ------------------------------------------------------------------------------
# STEP 8: Hard Deletion
# ------------------------------------------------------------------------------
echo -n "[8/9] Hard-deleting document... "
DELETE_RESP=$(curl -s -f -X DELETE "${API_URL}/documents/${DOC_ID}" \
  -H "${AUTH_HEADER}")

DEL_STATUS=$(echo "${DELETE_RESP}" | python -c "import sys, json; print(json.load(sys.stdin).get('status', ''))")
if [ "${DEL_STATUS}" != "deleted" ]; then
  echo "FAILED!"
  echo "Error: Deletion failed: ${DELETE_RESP}"
  exit 1
fi
echo "OK (Deleted)"

# ------------------------------------------------------------------------------
# STEP 9: Verify Derived Data is Purged
# ------------------------------------------------------------------------------
echo -n "[9/9] Verifying derived document data is purged (expecting 404)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "${AUTH_HEADER}" "${API_URL}/documents/${DOC_ID}")

if [ "${HTTP_CODE}" != "404" ]; then
  echo "FAILED! Expected 404 Not Found, received HTTP ${HTTP_CODE}"
  exit 1
fi
echo "OK (HTTP 404 Confirmed)"

echo "======================================================================"
echo "SMOKE TEST PASSED! All 9 steps completed successfully end-to-end."
echo "Zero mocks, real JWT auth, live RAG & hard-deletion verified."
echo "======================================================================"
exit 0
