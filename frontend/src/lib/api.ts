import {
  DocumentItem,
  DocumentStatus,
  DocumentTypeCode,
  ExtractedField,
  AuditLogEntry,
  DocumentTypeSchema,
} from "@/types";

export interface PipelineStageEvent {
  event_id: string;
  document_id: string;
  tenant_id: string;
  stage: "queued" | "preprocessing" | "ocr" | "parsing" | "validating" | "needs_review" | "approved" | "failed";
  status: string;
  stage_duration_ms: number | null;
  progress_pct: number | null;
  details: Record<string, any>;
  timestamp: string;
}

const STORAGE_KEY_TOKEN = "sanad_access_token";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

function getAuthHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem(STORAGE_KEY_TOKEN);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Map backend field names to localized UI names
function formatFieldNameEn(name: string): string {
  const map: Record<string, string> = {
    id_number: "Identity Number",
    full_name_ar: "Full Name (Arabic)",
    full_name_en: "Full Name (English)",
    name_ar: "Full Name (Arabic)",
    name_en: "Full Name (English)",
    nationality: "Nationality",
    date_of_birth: "Date of Birth",
    expiry_date: "Expiry Date",
    issue_date: "Issue Date",
    sex: "Sex",
    trade_name: "Trade Name",
    license_number: "License Number",
    trn: "Tax Registration Number (TRN)",
    total_amount: "Total Amount (AED)",
    vat_amount: "VAT Amount",
    invoice_number: "Invoice Number",
    invoice_date: "Invoice Date",
    supplier_name: "Supplier Name",
  };
  return map[name] || name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatFieldNameAr(name: string): string {
  const map: Record<string, string> = {
    id_number: "رقم الهوية",
    full_name_ar: "الاسم الكامل (بالعربية)",
    full_name_en: "الاسم الكامل (بالإنجليزية)",
    name_ar: "الاسم الكامل (بالعربية)",
    name_en: "الاسم الكامل (بالإنجليزية)",
    nationality: "الجنسية",
    date_of_birth: "تاريخ الميلاد",
    expiry_date: "تاريخ الانتهاء",
    issue_date: "تاريخ الإصدار",
    sex: "الجنس",
    trade_name: "الاسم التجاري",
    license_number: "رقم الرخصة",
    trn: "رقم التسجيل الضريبي",
    total_amount: "المبلغ الإجمالي (درهم)",
    vat_amount: "مبلغ ضريبة القيمة المضافة",
    invoice_number: "رقم الفاتورة",
    invoice_date: "تاريخ الفاتورة",
    supplier_name: "اسم المورد",
  };
  return map[name] || name;
}

function getFieldSection(name: string): "identity" | "company" | "dates" | "financials" | "general" {
  if (["id_number", "name_ar", "name_en", "full_name_ar", "full_name_en", "nationality", "sex"].includes(name)) return "identity";
  if (["date_of_birth", "expiry_date", "issue_date", "invoice_date"].includes(name)) return "dates";
  if (["trade_name", "license_number", "entity_name", "supplier_name"].includes(name)) return "company";
  if (["total_amount", "trn", "vat_amount", "invoice_number"].includes(name)) return "financials";
  return "general";
}

// Convert Backend Document JSON to frontend DocumentItem
export function mapBackendDocumentToItem(doc: any): DocumentItem {
  const typeCode = (doc.document_type_code || "emirates_id") as DocumentTypeCode;
  const isEid = typeCode === "emirates_id";
  const isLicense = typeCode === "uae_trade_license";
  const isInvoice = typeCode === "commercial_invoice";

  let typeNameEn = "UAE Sovereign Document";
  let typeNameAr = "مستند سيادي إماراتي";
  if (isEid) {
    typeNameEn = "UAE Identity Card (Emirates ID)";
    typeNameAr = "بطاقة الهوية الإماراتية";
  } else if (isLicense) {
    typeNameEn = "UAE Commercial Trade License";
    typeNameAr = "رخصة تجارية إماراتية";
  } else if (isInvoice) {
    typeNameEn = "Commercial Tax Invoice";
    typeNameAr = "فاتورة ضريبية تجارية";
  }

  const fields: ExtractedField[] = (doc.extracted_fields || []).map((f: any) => {
    let bbox = undefined;
    if (f.bounding_box) {
      const bx = f.bounding_box.x <= 1.0 ? f.bounding_box.x * 100 : f.bounding_box.x;
      const by = f.bounding_box.y <= 1.0 ? f.bounding_box.y * 100 : f.bounding_box.y;
      const bw = f.bounding_box.width <= 1.0 ? f.bounding_box.width * 100 : f.bounding_box.width;
      const bh = f.bounding_box.height <= 1.0 ? f.bounding_box.height * 100 : f.bounding_box.height;
      bbox = { x: bx, y: by, width: bw, height: bh, page: f.page_number || 1 };
    }

    return {
      id: f.id,
      key: f.field_name,
      nameEn: formatFieldNameEn(f.field_name),
      nameAr: formatFieldNameAr(f.field_name),
      value: f.corrected_value !== null && f.corrected_value !== undefined ? f.corrected_value : (f.value !== undefined ? f.value : null),
      originalValue: f.raw_value !== null && f.raw_value !== undefined ? f.raw_value : (f.value !== undefined ? f.value : null),
      confidence: f.confidence,
      section: getFieldSection(f.field_name),
      page: f.page_number || 1,
      bbox,
      isCorrected: f.is_corrected,
      required: true,
    };
  });

  const validationErrors = (doc.validation_results || [])
    .filter((v: any) => !v.passed)
    .map((v: any) => ({
      id: v.id,
      fieldKey: v.rule_name,
      severity: v.severity as "error" | "warning",
      messageEn: v.message,
      messageAr: v.message,
      isResolved: false,
    }));

  const token = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY_TOKEN) : "";
  const previewUrl = token
    ? `${API_BASE}/api/v1/documents/${doc.id}/file?token=${encodeURIComponent(token)}`
    : `${API_BASE}/api/v1/documents/${doc.id}/file`;

  return {
    id: doc.id,
    referenceNumber: `DOC-${doc.id.substring(0, 8).toUpperCase()}`,
    fileName: doc.file_name,
    documentType: typeCode,
    documentTypeNameEn: typeNameEn,
    documentTypeNameAr: typeNameAr,
    status: (doc.status as DocumentStatus) || "processing",
    overallConfidence: doc.confidence_score !== null && doc.confidence_score !== undefined ? doc.confidence_score : 0.0,
    uploadedAt: doc.created_at,
    processedAt: doc.updated_at,
    fileSizeKB: Math.round((doc.file_size || 0) / 1024),
    pageCount: doc.pages?.length || 1,
    extractedLanguage: (doc.language_detected as any) || "mixed",
    previewUrl,
    validationErrors,
    fields,
  };
}

// Convert Backend Audit Log JSON to frontend AuditLogEntry
export function mapBackendAuditToEntry(log: any): AuditLogEntry {
  const actionMap: Record<string, AuditLogEntry["action"]> = {
    DOCUMENT_UPLOAD: "DOCUMENT_UPLOAD",
    FIELD_CORRECT: "FIELD_CORRECTED",
    DOCUMENT_APPROVE: "DOCUMENT_APPROVED",
    DOCUMENT_REJECT: "DOCUMENT_REJECTED",
    DOCUMENT_DELETE: "DOCUMENT_DELETED",
    DOCUMENT_EXPORT: "DOCUMENT_EXPORTED",
    PII_UNMASK: "PII_UNMASKED",
  };

  const action = actionMap[log.action] || "DOCUMENT_UPLOAD";
  const diff = log.details && log.details.field_name
    ? {
        field: log.details.field_name,
        oldValue: log.details.old_value || "",
        newValue: log.details.new_value || "",
      }
    : undefined;

  return {
    id: log.id,
    timestamp: log.created_at,
    actorName: log.actor_email ? log.actor_email.split("@")[0] : "System",
    actorEmail: log.actor_email || "system@pipeline.local",
    actorRole: (log.actor_role === "admin" ? "Admin" : log.actor_role === "reviewer" ? "Reviewer" : "Viewer") as any,
    action,
    documentId: log.entity_id,
    documentRef: log.entity_id ? `DOC-${log.entity_id.substring(0, 8).toUpperCase()}` : undefined,
    ipAddress: log.ip_address || "127.0.0.1",
    detailsEn: log.details?.reason || `${log.action} on ${log.entity_type} ${log.entity_id || ""}`,
    detailsAr: `${log.action} على ${log.entity_type}`,
    diff,
  };
}

export interface ApiAdapter {
  auth: {
    login: (email: string, password: string) => Promise<{ access_token: string; user: any }>;
    getMe: () => Promise<any>;
    logout: () => void;
    getToken: () => string | null;
  };
  documents: {
    list: (params?: { status?: string; limit?: number; offset?: number }) => Promise<DocumentItem[]>;
    get: (id: string) => Promise<DocumentItem>;
    upload: (file: File, docType?: string, onProgress?: (p: number) => void) => Promise<DocumentItem>;
    correctField: (id: string, fieldName: string, correctedValue: string, reason?: string) => Promise<ExtractedField>;
    approve: (id: string) => Promise<{ status: string; webhook?: any }>;
    reject: (id: string, reason?: string) => Promise<{ status: string }>;
    delete: (id: string) => Promise<void>;
    export: (id: string, format: "json" | "csv", maskPii: boolean) => Promise<any>;
    subscribeDocumentEvents: (id: string, onEvent: (evt: PipelineStageEvent) => void) => () => void;
    subscribeTenantEvents: (onEvent: (evt: PipelineStageEvent) => void) => () => void;
  };
  audit: {
    list: (params?: { action?: string; limit?: number }) => Promise<AuditLogEntry[]>;
  };
  schemas: {
    list: () => Promise<DocumentTypeSchema[]>;
  };
  rag: {
    query: (query: string, documentId?: string, topK?: number) => Promise<RAGResponse>;
  };
}

export interface RAGCitationItem {
  chunk_id: string;
  document_id?: string;
  page: number;
  bounding_box?: { x: number; y: number; width: number; height: number; page?: number };
  snippet: string;
}

export interface RAGResponse {
  query: string;
  answer: string;
  answer_ar: string;
  mode: string;
  confidence: number;
  citations: RAGCitationItem[];
  prompt_guard_flagged: boolean;
}

// -------------------------------------------------------------
// LIVE ADAPTER (Connects to real FastAPI Sovereign Backend)
// -------------------------------------------------------------
export const api: ApiAdapter = {
  auth: {
    async login(email, password) {
      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Login failed" }));
        throw new Error(err.detail || "Authentication failed");
      }
      const data = await res.json();
      if (typeof window !== "undefined") {
        localStorage.setItem(STORAGE_KEY_TOKEN, data.access_token);
      }
      return { access_token: data.access_token, user: data };
    },
    async getMe() {
      const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
        headers: { ...getAuthHeader() },
      });
      if (!res.ok) throw new Error("Failed to fetch user profile");
      return await res.json();
    },
    logout() {
      if (typeof window !== "undefined") {
        localStorage.removeItem(STORAGE_KEY_TOKEN);
      }
    },
    getToken() {
      if (typeof window === "undefined") return null;
      return localStorage.getItem(STORAGE_KEY_TOKEN);
    },
  },

  documents: {
    async list(params) {
      if (!api.auth.getToken()) {
        try {
          await api.auth.login("admin@alhilal-demo.ae", "AdminSecurePass2026!");
        } catch {}
      }
      const q = new URLSearchParams();
      if (params?.status) q.append("status", params.status);
      if (params?.limit) q.append("limit", params.limit.toString());
      if (params?.offset) q.append("offset", params.offset.toString());

      const res = await fetch(`${API_BASE}/api/v1/documents/?${q.toString()}`, {
        headers: { ...getAuthHeader() },
      });
      if (!res.ok) throw new Error("Failed to fetch documents");
      const data = await res.json();
      return (data.documents || []).map(mapBackendDocumentToItem);
    },

    async get(id) {
      if (!api.auth.getToken()) {
        try {
          await api.auth.login("admin@alhilal-demo.ae", "AdminSecurePass2026!");
        } catch {}
      }
      const res = await fetch(`${API_BASE}/api/v1/documents/${id}`, {
        headers: { ...getAuthHeader() },
      });
      if (!res.ok) throw new Error(`Document ${id} not found`);
      const data = await res.json();
      return mapBackendDocumentToItem(data);
    },

    async upload(file, docType = "emirates_id", onProgress) {
      if (!api.auth.getToken()) {
        try {
          await api.auth.login("admin@alhilal-demo.ae", "AdminSecurePass2026!");
        } catch {}
      }
      const formData = new FormData();
      formData.append("file", file);
      if (docType && docType !== "auto") {
        formData.append("document_type_code", docType);
      }

      if (onProgress) onProgress(20);

      const res = await fetch(`${API_BASE}/api/v1/documents/upload`, {
        method: "POST",
        headers: { ...getAuthHeader() },
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail || "Document upload failed");
      }

      if (onProgress) onProgress(100);
      const data = await res.json();
      return mapBackendDocumentToItem(data);
    },

    async correctField(id, fieldName, correctedValue, reason = "User correction") {
      const res = await fetch(`${API_BASE}/api/v1/documents/${id}/fields/${fieldName}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader(),
        },
        body: JSON.stringify({ corrected_value: correctedValue, reason }),
      });
      if (!res.ok) throw new Error("Failed to correct field");
      const f = await res.json();
      return {
        id: f.id,
        key: f.field_name,
        nameEn: formatFieldNameEn(f.field_name),
        nameAr: formatFieldNameAr(f.field_name),
        value: f.corrected_value,
        originalValue: f.raw_value || f.value,
        confidence: f.confidence,
        section: getFieldSection(f.field_name),
        page: f.page_number,
        isCorrected: f.is_corrected,
      };
    },

    async approve(id) {
      const res = await fetch(`${API_BASE}/api/v1/documents/${id}/approve`, {
        method: "POST",
        headers: { ...getAuthHeader() },
      });
      if (!res.ok) throw new Error("Failed to approve document");
      return await res.json();
    },

    async reject(id, reason = "Rejected during human review") {
      const res = await fetch(`${API_BASE}/api/v1/documents/${id}/reject`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader(),
        },
        body: JSON.stringify({ rejection_reason: reason }),
      });
      if (!res.ok) throw new Error("Failed to reject document");
      return await res.json();
    },

    async delete(id) {
      const res = await fetch(`${API_BASE}/api/v1/documents/${id}`, {
        method: "DELETE",
        headers: { ...getAuthHeader() },
      });
      if (!res.ok) throw new Error("Failed to delete document");
    },

    async export(id, format = "json", maskPii = true) {
      const res = await fetch(
        `${API_BASE}/api/v1/documents/${id}/export?format=${format}&mask_pii=${maskPii}`,
        { headers: { ...getAuthHeader() } }
      );
      if (!res.ok) throw new Error("Failed to export document");
      if (format === "csv") return await res.text();
      return await res.json();
    },

    subscribeDocumentEvents(id: string, onEvent: (evt: PipelineStageEvent) => void): () => void {
      if (typeof window === "undefined") return () => {};
      const token = localStorage.getItem(STORAGE_KEY_TOKEN);
      const url = `${API_BASE}/api/v1/documents/${id}/events${token ? `?token=${encodeURIComponent(token)}` : ""}`;
      const es = new EventSource(url);
      es.onmessage = (e) => {
        try {
          const parsed = JSON.parse(e.data);
          onEvent(parsed);
        } catch {}
      };
      return () => es.close();
    },

    subscribeTenantEvents(onEvent: (evt: PipelineStageEvent) => void): () => void {
      if (typeof window === "undefined") return () => {};
      const token = localStorage.getItem(STORAGE_KEY_TOKEN);
      const url = `${API_BASE}/api/v1/events${token ? `?token=${encodeURIComponent(token)}` : ""}`;
      const es = new EventSource(url);
      es.onmessage = (e) => {
        try {
          const parsed = JSON.parse(e.data);
          onEvent(parsed);
        } catch {}
      };
      return () => es.close();
    },
  },

  audit: {
    async list(params) {
      const q = new URLSearchParams();
      if (params?.action) q.append("action", params.action);
      if (params?.limit) q.append("limit", params.limit.toString());

      const res = await fetch(`${API_BASE}/api/v1/audit/?${q.toString()}`, {
        headers: { ...getAuthHeader() },
      });
      if (!res.ok) return [];
      const data = await res.json();
      return data.map(mapBackendAuditToEntry);
    },
  },

  schemas: {
    async list() {
      const res = await fetch(`${API_BASE}/api/v1/document-types/`, {
        headers: { ...getAuthHeader() },
      });
      if (!res.ok) return [];
      const data = await res.json();
      return data.map((d: any) => ({
        id: d.id,
        code: d.code,
        nameEn: d.name_en,
        nameAr: d.name_ar,
        fields: d.schema_definition?.fields || [],
        rules: d.schema_definition?.validation_rules || [],
      }));
    },
  },

  rag: {
    async query(query: string, documentId?: string, topK: number = 5): Promise<RAGResponse> {
      if (!api.auth.getToken()) {
        try {
          await api.auth.login("admin@alhilal-demo.ae", "AdminSecurePass2026!");
        } catch {}
      }
      const res = await fetch(`${API_BASE}/api/v1/rag/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader(),
        },
        body: JSON.stringify({ query, document_id: documentId, top_k: topK }),
      });
      if (!res.ok) throw new Error("RAG query failed");
      return await res.json();
    },
  },
};
