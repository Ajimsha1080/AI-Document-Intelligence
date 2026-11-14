# Emirates ID Extraction Pipeline Evaluation Report

**Evaluation Date:** 2026-11-14 14:09:24Z  
**Evaluation Mode:** Sovereign Air-Gapped Local Pipeline  
**Model Provider Backend:** `Local OCR Engine (Tesseract/Layout)`  
**Dataset Size:** 50 labeled synthetic documents (100% synthetic, zero real personal data)  
**Compliance Standard:** UAE PDPL Federal Decree-Law No. 45/2021 (Zero Cross-Border Data Transfer)

---

## 1. Executive Summary & KPIs

| Metric | Measured Value | Target Baseline | Compliance Status |
| :--- | :--- | :--- | :--- |
| **Total Evaluated Documents** | `50` | 50 | PASSED |
| **Document Exact-Match Rate** | `100.0%` | ≥ 90.0% | PASSED |
| **Average Field Confidence** | `94.0%` | ≥ 85.0% | PASSED |
| **Average Latency / Document** | `20.1 ms` | < 1,500 ms | PASSED |
| **p95 Latency** | `19.4 ms` | < 2,500 ms | PASSED |
| **Outbound Network Calls** | `0 (100% Air-Gapped)` | 0 | PASSED |

---

## 2. Per-Field Extraction Accuracy

Each field is checked against ground truth with Arabic-Indic digit normalization and checksum validation:

| Field Identifier | Semantic Description | Accuracy Rate | Matched / Total |
| :--- | :--- | :--- | :--- |
| `id_number` | 15-Digit Emirates ID with Luhn Checksum | **100.0%** | 50 / 50 |
| `name_ar` | Full Name in Arabic Script | **100.0%** | 50 / 50 |
| `name_en` | Full Name in English / Transliteration | **100.0%** | 50 / 50 |
| `nationality` | Country of Citizenship | **100.0%** | 50 / 50 |
| `date_of_birth` | Date of Birth (DD/MM/YYYY) | **100.0%** | 50 / 50 |
| `expiry_date` | Card Expiration Date | **100.0%** | 50 / 50 |
| `sex` | Sex Indicator (M / F) | **100.0%** | 50 / 50 |

---

## 3. Latency Distribution

Processing pipeline includes orientation correction, deskew, contrast normalization, resolution scaling, and token parsing:

- **Mean Processing Time:** `20.11 ms`
- **Fastest (p0):** `10.21 ms`
- **95th Percentile (p95):** `19.44 ms`
- **Slowest (p100):** `357.95 ms`

---

## 4. Edge Cases and Resilience Tested

The evaluation dataset exercised the following document degradation scenarios:
1. **Rotation & Skew:** Angle shifts (-2° to +2°) normalized by PIL rotation preprocessor.
2. **Resolution Variations:** High-density ID crops scaled via Lanczos filter.
3. **Subtle Blur & Grain:** Filtered using edge enhancement and adaptive contrast.
4. **Digit Normalization:** Arabic-Indic digits (٠-٩) mapped to ISO digits (0-9).
5. **Checksum Defense:** Invalid check digits flagged immediately by the validation engine with zero invented values.

---

## 5. Sovereign Architecture Guarantee

- **Zero Network Egress:** No external APIs (Google Cloud Vision, AWS Textract, Azure Document Intelligence, OpenAI) were contacted.
- **In-Country Residency:** Execution occurred completely within the local execution environment in accordance with UAE Federal Decree-Law No. 45/2021.
