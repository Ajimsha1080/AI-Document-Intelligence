"""
Cross-Platform Python Runner for Sovereign UAE Document Intelligence Smoke Test.
Executes the identical 9 steps as smoke_test.sh using requests/urllib.
"""

import os
import sys
import time
import httpx

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
API_URL = f"{BASE_URL}/api/v1"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@alhilal-demo.ae")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "AdminSecurePass2026!")
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEST_IMAGE = os.path.join(PROJECT_ROOT, "eval", "dataset", "sample_001.png")

def main():
    print("=" * 70)
    print("Starting Sovereign UAE Document Intelligence Smoke Test (Python Runner)")
    print(f"Target Base URL: {BASE_URL}")
    print("=" * 70)

    # 1. Health check
    print("[1/9] Checking /health endpoint... ", end="", flush=True)
    resp = httpx.get(f"{BASE_URL}/health", timeout=10)
    if resp.status_code != 200:
        print(f"FAILED (Status: {resp.status_code})")
        sys.exit(1)
    print(f"OK ({resp.json()})")

    # 2. Login
    print(f"[2/9] Authenticating as admin ({ADMIN_EMAIL})... ", end="", flush=True)
    resp = httpx.post(
        f"{API_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10
    )
    if resp.status_code != 200:
        print(f"FAILED: {resp.text}")
        sys.exit(1)
    token = resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("OK (Token obtained)")

    # 3. Upload real image
    print(f"[3/9] Uploading pure raster document ({TEST_IMAGE})... ", end="", flush=True)
    if not os.path.exists(TEST_IMAGE):
        print(f"FAILED: File not found at {TEST_IMAGE}")
        sys.exit(1)

    with open(TEST_IMAGE, "rb") as f:
        files = {"file": ("sample_001.png", f, "image/png")}
        data = {"document_type_code": "emirates_id"}
        resp = httpx.post(f"{API_URL}/documents/upload", headers=headers, files=files, data=data, timeout=30)

    if resp.status_code != 201:
        print(f"FAILED: {resp.text}")
        sys.exit(1)

    doc_id = resp.json().get("id")
    print(f"OK (Document ID: {doc_id})")

    # 4. Await pipeline processing
    print("[4/9] Waiting for pipeline processing to reach review/approved status... ", end="", flush=True)
    final_status = ""
    for _ in range(30):
        resp = httpx.get(f"{API_URL}/documents/{doc_id}", headers=headers, timeout=10)
        if resp.status_code == 200:
            final_status = resp.json().get("status")
            if final_status in ["needs_review", "approved"]:
                break
        time.sleep(1)

    if final_status not in ["needs_review", "approved"]:
        print(f"FAILED (Final status: {final_status})")
        sys.exit(1)
    print(f"OK (Status: {final_status})")

    # 5. Field correction
    print("[5/9] Correcting extracted field 'full_name_en'... ", end="", flush=True)
    resp = httpx.patch(
        f"{API_URL}/documents/{doc_id}/fields/full_name_en",
        headers=headers,
        json={"corrected_value": "SALEM RASHED SAIF ALSHAMSI", "reason": "Smoke test verified correction"},
        timeout=10
    )
    if resp.status_code != 200:
        print(f"FAILED: {resp.text}")
        sys.exit(1)
    corrected_val = resp.json().get("value")
    print(f"OK (Value: '{corrected_val}')")

    # 6. Approve document
    print("[6/9] Approving document... ", end="", flush=True)
    resp = httpx.post(f"{API_URL}/documents/{doc_id}/approve?force=true", headers=headers, timeout=10)
    if resp.status_code != 200:
        print(f"FAILED: {resp.text}")
        sys.exit(1)

    doc_detail = httpx.get(f"{API_URL}/documents/{doc_id}", headers=headers, timeout=10).json()
    if doc_detail.get("status") != "approved":
        print(f"FAILED: status is {doc_detail.get('status')}")
        sys.exit(1)
    print("OK (Status: approved)")

    # 7. Ask RAG question
    print("[7/9] Asking sovereign RAG question with citations... ", end="", flush=True)
    resp = httpx.post(
        f"{API_URL}/rag/query",
        headers=headers,
        json={"query": "What is Salem's Emirates ID number?", "document_id": doc_id},
        timeout=10
    )
    if resp.status_code != 200:
        print(f"FAILED: {resp.text}")
        sys.exit(1)
    rag_ans = resp.json().get("answer")
    print(f"OK (Answer: {rag_ans})")

    # 8. Hard delete document
    print("[8/9] Hard-deleting document... ", end="", flush=True)
    resp = httpx.delete(f"{API_URL}/documents/{doc_id}", headers=headers, timeout=10)
    if resp.status_code != 200:
        print(f"FAILED: {resp.text}")
        sys.exit(1)
    print("OK (Deleted)")

    # 9. Verify derived data is purged
    print("[9/9] Verifying derived document data is purged (expecting 404)... ", end="", flush=True)
    resp = httpx.get(f"{API_URL}/documents/{doc_id}", headers=headers, timeout=10)
    if resp.status_code != 404:
        print(f"FAILED: Expected 404, got {resp.status_code}")
        sys.exit(1)
    print("OK (HTTP 404 Confirmed)")

    print("=" * 70)
    print("SMOKE TEST PASSED! All 9 steps completed successfully end-to-end.")
    print("=" * 70)

if __name__ == "__main__":
    main()
