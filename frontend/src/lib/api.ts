import {
  DocumentItem,
  DocumentStatus,
  DocumentTypeCode,
  ExtractedField,
  AuditLogEntry,
  DocumentTypeSchema,
  SystemUser,
  ApiKeyItem,
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

export const STORAGE_KEY_TOKEN = "sanad_access_token";

export const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL && !process.env.NEXT_PUBLIC_API_URL.includes("localhost") && !process.env.NEXT_PUBLIC_API_URL.includes("127.0.0.1"))
    ? process.env.NEXT_PUBLIC_API_URL
    : typeof window !== "undefined"
      ? `${window.location.protocol}//${window.location.hostname || "127.0.0.1"}:8000`
      : (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000");

export function getAuthHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem(STORAGE_KEY_TOKEN);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY_TOKEN) : null;
  const headers = new Headers(options.headers || {});
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem(STORAGE_KEY_TOKEN);
      window.dispatchEvent(new CustomEvent("sanad:unauthorized"));
    }
  }
  return res;
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
    nationality_en: "Nationality (English)",
    nationality_ar: "Nationality (Arabic)",
    date_of_birth: "Date of Birth",
    expiry_date: "Expiry Date",
    issue_date: "Issue Date",
    sex: "Sex",
    gender: "Sex / Gender",
    trade_name: "Trade Name",
    company_name_en: "Company Name (English)",
    company_name_ar: "Company Name (Arabic)",
    license_number: "License Number",
    trn: "Tax Registration Number (TRN)",
    total_amount: "Total Amount (AED)",
    vat_amount: "VAT Amount",
    subtotal: "Subtotal",
    invoice_number: "Invoice Number",
    invoice_date: "Invoice Date",
    supplier_name: "Supplier / Vendor Name",
    vendor_name: "Vendor Name",
    customer_name: "Customer Name",
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
    nationality_en: "الجنسية (بالإنجليزية)",
    nationality_ar: "الجنسية (بالعربية)",
    date_of_birth: "تاريخ الميلاد",
    expiry_date: "تاريخ الانتهاء",
    issue_date: "تاريخ الإصدار",
    sex: "الجنس",
    gender: "الجنس",
    trade_name: "الاسم التجاري",
    company_name_en: "اسم الشركة (بالإنجليزية)",
    company_name_ar: "اسم الشركة (بالعربية)",
    license_number: "رقم الرخصة",
    trn: "رقم التسجيل الضريبي",
    total_amount: "المبلغ الإجمالي (درهم)",
    vat_amount: "مبلغ ضريبة القيمة المضافة",
    subtotal: "المبلغ الفرعي",
    invoice_number: "رقم الفاتورة",
    invoice_date: "تاريخ الفاتورة",
    supplier_name: "اسم المورد",
    vendor_name: "اسم المورد",
    customer_name: "اسم العميل",
  };
  return map[name] || name;
}

function getFieldSection(name: string): "identity" | "company" | "dates" | "financials" | "general" {
  if (["id_number", "name_ar", "name_en", "full_name_ar", "full_name_en", "nationality", "nationality_en", "nationality_ar", "sex", "gender"].includes(name)) return "identity";
  if (["date_of_birth", "expiry_date", "issue_date", "invoice_date"].includes(name)) return "dates";
  if (["trade_name", "license_number", "entity_name", "company_name_en", "company_name_ar", "supplier_name", "vendor_name", "customer_name"].includes(name)) return "company";
  if (["total_amount", "trn", "vat_amount", "subtotal", "invoice_number"].includes(name)) return "financials";
  return "general";
}

// Convert Backend Document JSON to frontend DocumentItem
export function mapBackendDocumentToItem(doc: any): DocumentItem {
  // Use document_type_code from API
  const typeCode = (doc.document_type_code || doc.document_type?.code || "emirates_id") as DocumentTypeCode;
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
  } else if (doc.document_type?.name_en) {
    typeNameEn = doc.document_type.name_en;
    typeNameAr = doc.document_type.name_ar || doc.document_type.name_en;
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

  const validationResults = (doc.validation_results || []).map((v: any) => ({
    id: v.id || String(Math.random()),
    ruleName: v.rule_name || "Rule",
    passed: Boolean(v.passed),
    severity: (v.severity as "error" | "warning") || "error",
    message: v.message || "",
  }));

  const previewUrl = `${API_BASE}/api/v1/documents/${doc.id}/file`;

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
    validationResults,
    fields,
  };
}

// Convert Backend Audit Log JSON to frontend AuditLogEntry
export function mapBackendAuditToEntry(log: any): AuditLogEntry {
  const actionMap: Record<string, string> = {
    DOCUMENT_UPLOAD: "DOCUMENT_UPLOAD",
    FIELD_CORRECT: "FIELD_CORRECTED",
    FIELD_CORRECTED: "FIELD_CORRECTED",
    DOCUMENT_APPROVE: "DOCUMENT_APPROVED",
    DOCUMENT_APPROVED: "DOCUMENT_APPROVED",
    DOCUMENT_REJECT: "DOCUMENT_REJECTED",
    DOCUMENT_REJECTED: "DOCUMENT_REJECTED",
    DOCUMENT_DELETE: "DOCUMENT_DELETED",
    DOCUMENT_DELETED: "DOCUMENT_DELETED",
    DOCUMENT_EXPORT: "DOCUMENT_EXPORTED",
    DOCUMENT_EXPORTED: "DOCUMENT_EXPORTED",
    PII_UNMASK: "PII_UNMASKED",
    PII_UNMASKED: "PII_UNMASKED",
  };

  // Show unknown actions as-is
  const action = actionMap[log.action] || log.action || "UNKNOWN_ACTION";

  // Audit diff uses original_value / corrected_value
  const diff = log.details && (log.details.field_name || log.details.field)
    ? {
        field: log.details.field_name || log.details.field,
        oldValue: String(log.details.original_value ?? log.details.old_value ?? ""),
        newValue: String(log.details.corrected_value ?? log.details.new_value ?? ""),
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
    getStreamToken: () => Promise<string>;
    logout: () => void;
    getToken: () => string | null;
  };
  documents: {
    list: (params?: { status?: string; limit?: number; offset?: number }) => Promise<DocumentItem[]>;
    get: (id: string) => Promise<DocumentItem>;
    getFileBlobUrl: (id: string) => Promise<string>;
    upload: (file: File, docType?: string, onProgress?: (p: number) => void) => Promise<DocumentItem>;
    correctField: (id: string, fieldName: string, correctedValue: string, reason?: string) => Promise<ExtractedField>;
    approve: (id: string, force?: boolean) => Promise<{ status: string; webhook?: any }>;
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
    save: (schema: DocumentTypeSchema) => Promise<DocumentTypeSchema>;
    delete: (id: string) => Promise<void>;
  };
  users: {
    list: () => Promise<SystemUser[]>;
    create: (name: string, email: string, role: string, password?: string) => Promise<SystemUser>;
    updateRole: (id: string, role: string) => Promise<SystemUser>;
    delete: (id: string) => Promise<void>;
  };
  apiKeys: {
    list: () => Promise<ApiKeyItem[]>;
    create: (name: string, role?: string, expiresInDays?: number) => Promise<{ api_key: string; key: ApiKeyItem }>;
    revoke: (id: string) => Promise<void>;
  };
  tenants: {
    getMe: () => Promise<any>;
    updateSettings: (data: { retention_days?: number; pii_masking_default?: boolean; webhook_url?: string }) => Promise<any>;
    testWebhook: (url: string) => Promise<any>;
    runRetentionSweep: () => Promise<any>;
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
        body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
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
      const res = await authFetch(`${API_BASE}/api/v1/auth/me`);
      if (!res.ok) throw new Error("Failed to fetch user profile");
      return await res.json();
    },
    async getStreamToken(): Promise<string> {
      const res = await authFetch(`${API_BASE}/api/v1/auth/stream-token`, {
        method: "POST",
      });
      if (!res.ok) {
        throw new Error("Failed to obtain secure stream token");
      }
      const data = await res.json();
      return data.stream_token;
    },
    logout() {
      if (typeof window !== "undefined") {
        localStorage.removeItem(STORAGE_KEY_TOKEN);
        window.dispatchEvent(new CustomEvent("sanad:unauthorized"));
      }
    },
    getToken() {
      if (typeof window === "undefined") return null;
      return localStorage.getItem(STORAGE_KEY_TOKEN);
    },
  },

  documents: {
    async list(params) {
      const q = new URLSearchParams();
      if (params?.status) q.append("status", params.status);
      if (params?.limit) q.append("limit", params.limit.toString());
      if (params?.offset) q.append("offset", params.offset.toString());

      const res = await authFetch(`${API_BASE}/api/v1/documents/?${q.toString()}`);
      if (!res.ok) throw new Error("Failed to fetch documents");
      const data = await res.json();
      return (data.documents || []).map(mapBackendDocumentToItem);
    },

    async get(id) {
      const res = await authFetch(`${API_BASE}/api/v1/documents/${id}`);
      if (!res.ok) throw new Error(`Document ${id} not found`);
      const data = await res.json();
      return mapBackendDocumentToItem(data);
    },

    async getFileBlobUrl(id: string): Promise<string> {
      const res = await authFetch(`${API_BASE}/api/v1/documents/${id}/file`);
      if (!res.ok) throw new Error(`Failed to load preview for document ${id}`);
      const blob = await res.blob();
      return URL.createObjectURL(blob);
    },

    // Real upload progress via XMLHttpRequest; auto-detects type unless user picks one
    upload(file: File, docType?: string, onProgress?: (p: number) => void): Promise<DocumentItem> {
      return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append("file", file);
        // Only append if user explicitly chose a type (auto-detects if omitted)
        if (docType && docType !== "auto") {
          formData.append("document_type_code", docType);
        }

        const xhr = new XMLHttpRequest();
        xhr.open("POST", `${API_BASE}/api/v1/documents/upload`);

        const token = api.auth.getToken();
        if (token) {
          xhr.setRequestHeader("Authorization", `Bearer ${token}`);
        }

        if (xhr.upload && onProgress) {
          xhr.upload.onprogress = (evt) => {
            if (evt.lengthComputable) {
              const pct = Math.round((evt.loaded / evt.total) * 100);
              onProgress(pct);
            }
          };
        }

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const data = JSON.parse(xhr.responseText);
              resolve(mapBackendDocumentToItem(data));
            } catch (err) {
              reject(err);
            }
          } else if (xhr.status === 401) {
            api.auth.logout();
            reject(new Error("Unauthorized"));
          } else {
            try {
              const err = JSON.parse(xhr.responseText);
              reject(new Error(err.detail || "Document upload failed"));
            } catch {
              reject(new Error(`Upload failed with status ${xhr.status}`));
            }
          }
        };

        xhr.onerror = () => {
          const targetUrl = `${API_BASE}/api/v1/documents/upload`;
          reject(new Error(`Network error connecting to processing server at ${targetUrl}. Please ensure backend is active.`));
        };
        xhr.ontimeout = () => {
          reject(new Error("Document upload timed out. Please check server responsiveness."));
        };
        xhr.timeout = 60000; // 60s upload timeout
        xhr.send(formData);
      });
    },

    async correctField(id, fieldName, correctedValue, reason = "User correction") {
      // encodeURIComponent on field name
      const res = await authFetch(`${API_BASE}/api/v1/documents/${id}/fields/${encodeURIComponent(fieldName)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
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

    async approve(id, force = false) {
      const url = force ? `${API_BASE}/api/v1/documents/${id}/approve?force=true` : `${API_BASE}/api/v1/documents/${id}/approve`;
      const res = await authFetch(url, {
        method: "POST",
      });
      if (!res.ok) {
        let errDetail = "Failed to approve document";
        try {
          const errData = await res.json();
          if (errData.detail) {
            errDetail = typeof errData.detail === "string" ? errData.detail : (Array.isArray(errData.detail) ? errData.detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ") : JSON.stringify(errData.detail));
          }
        } catch {}
        throw new Error(errDetail);
      }
      return await res.json();
    },

    async reject(id, reason = "Rejected during human review") {
      const res = await authFetch(`${API_BASE}/api/v1/documents/${id}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rejection_reason: reason }),
      });
      if (!res.ok) throw new Error("Failed to reject document");
      return await res.json();
    },

    async delete(id) {
      const res = await authFetch(`${API_BASE}/api/v1/documents/${id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete document");
    },

    async export(id, format = "json", maskPii = true) {
      const res = await authFetch(
        `${API_BASE}/api/v1/documents/${id}/export?format=${format}&mask_pii=${maskPii}`
      );
      if (!res.ok) throw new Error("Failed to export document");
      if (format === "csv") return await res.text();
      return await res.json();
    },

    subscribeDocumentEvents(id: string, onEvent: (evt: PipelineStageEvent) => void): () => void {
      if (typeof window === "undefined") return () => {};
      let closed = false;
      let es: EventSource | null = null;

      api.auth.getStreamToken().then((streamToken) => {
        if (closed) return;
        const url = `${API_BASE}/api/v1/documents/${id}/events?token=${encodeURIComponent(streamToken)}`;
        es = new EventSource(url);
        es.onmessage = (e) => {
          try {
            const parsed = JSON.parse(e.data);
            onEvent(parsed);
          } catch {}
        };
      }).catch(() => {});

      return () => {
        closed = true;
        if (es) es.close();
      };
    },

    subscribeTenantEvents(onEvent: (evt: PipelineStageEvent) => void): () => void {
      if (typeof window === "undefined") return () => {};
      let closed = false;
      let es: EventSource | null = null;

      api.auth.getStreamToken().then((streamToken) => {
        if (closed) return;
        const url = `${API_BASE}/api/v1/documents/events?token=${encodeURIComponent(streamToken)}`;
        es = new EventSource(url);
        es.onmessage = (e) => {
          try {
            const parsed = JSON.parse(e.data);
            onEvent(parsed);
          } catch {}
        };
      }).catch(() => {});

      return () => {
        closed = true;
        if (es) es.close();
      };
    },
  },

  audit: {
    async list(params) {
      const q = new URLSearchParams();
      if (params?.action) q.append("action", params.action);
      if (params?.limit) q.append("limit", params.limit.toString());

      const res = await authFetch(`${API_BASE}/api/v1/audit/?${q.toString()}`);
      if (!res.ok) return [];
      const data = await res.json();
      return data.map(mapBackendAuditToEntry);
    },
  },

  schemas: {
    async list() {
      const res = await authFetch(`${API_BASE}/api/v1/document-types/`);
      if (!res.ok) return [];
      const data = await res.json();
      return data.map((d: any) => ({
        id: d.id,
        code: d.code,
        nameEn: d.name_en,
        nameAr: d.name_ar,
        descriptionEn: d.description || "",
        descriptionAr: d.description || "",
        fields: d.schema_definition?.fields || [],
        rules: d.schema_definition?.rules || d.schema_definition?.validation_rules || d.validation_rules || [],
        isStandard: ["emirates_id", "uae_trade_license", "commercial_invoice"].includes(d.code),
      }));
    },

    async save(schema: DocumentTypeSchema) {
      const isExistingUuid = schema.id && schema.id.length === 36 && schema.id.includes("-");
      if (isExistingUuid) {
        const res = await authFetch(`${API_BASE}/api/v1/document-types/${schema.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name_en: schema.nameEn,
            name_ar: schema.nameAr,
            description: schema.descriptionEn,
            schema_definition: {
              fields: schema.fields,
              rules: schema.rules,
            },
          }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Failed to update schema" }));
          throw new Error(err.detail || "Failed to update schema");
        }
        const d = await res.json();
        return {
          id: d.id,
          code: d.code,
          nameEn: d.name_en,
          nameAr: d.name_ar,
          descriptionEn: d.description || "",
          descriptionAr: d.description || "",
          fields: d.schema_definition?.fields || [],
          rules: d.schema_definition?.rules || d.schema_definition?.validation_rules || [],
          isStandard: ["emirates_id", "uae_trade_license", "commercial_invoice"].includes(d.code),
        };
      } else {
        const res = await authFetch(`${API_BASE}/api/v1/document-types/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            code: schema.code,
            name_en: schema.nameEn,
            name_ar: schema.nameAr,
            description: schema.descriptionEn,
            schema_definition: {
              fields: schema.fields,
              rules: schema.rules,
            },
          }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Failed to create schema" }));
          throw new Error(err.detail || "Failed to create schema");
        }
        const d = await res.json();
        return {
          id: d.id,
          code: d.code,
          nameEn: d.name_en,
          nameAr: d.name_ar,
          descriptionEn: d.description || "",
          descriptionAr: d.description || "",
          fields: d.schema_definition?.fields || [],
          rules: d.schema_definition?.rules || d.schema_definition?.validation_rules || [],
          isStandard: ["emirates_id", "uae_trade_license", "commercial_invoice"].includes(d.code),
        };
      }
    },

    async delete(id: string) {
      const res = await authFetch(`${API_BASE}/api/v1/document-types/${id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete schema");
    },
  },

  users: {
    async list(): Promise<SystemUser[]> {
      const res = await authFetch(`${API_BASE}/api/v1/users/`);
      if (!res.ok) return [];
      const data = await res.json();
      return data.map((u: any) => ({
        id: u.id,
        name: u.email.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()),
        email: u.email,
        role: u.role,
        status: u.is_active ? "active" : "deactivated",
        lastLogin: u.updated_at ? u.updated_at.split("T")[0] : "Active",
      }));
    },

    async create(name: string, email: string, role: string, password?: string): Promise<SystemUser> {
      const payload: Record<string, any> = {
        full_name: name.trim(),
        email: email.trim().toLowerCase(),
        role,
      };
      if (password) {
        payload.password = password;
      }
      const res = await authFetch(`${API_BASE}/api/v1/users/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Failed to create user" }));
        let msg = "Failed to create user";
        if (Array.isArray(err.detail)) {
          msg = err.detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ");
        } else if (typeof err.detail === "string") {
          msg = err.detail;
        } else if (err.detail) {
          msg = JSON.stringify(err.detail);
        }
        throw new Error(msg);
      }
      const u = await res.json();
      return {
        id: u.id,
        name: u.full_name || name || u.email.split("@")[0],
        email: u.email,
        role: u.role,
        status: "active",
        lastLogin: "Just now",
      };
    },

    async updateRole(id: string, role: string): Promise<SystemUser> {
      const res = await authFetch(`${API_BASE}/api/v1/users/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Failed to update role" }));
        throw new Error(err.detail || "Failed to update role");
      }
      const u = await res.json();
      return {
        id: u.id,
        name: u.email.split("@")[0],
        email: u.email,
        role: u.role,
        status: u.is_active ? "active" : "deactivated",
        lastLogin: "Active",
      };
    },

    async delete(id: string): Promise<void> {
      const res = await authFetch(`${API_BASE}/api/v1/users/${id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Failed to delete user" }));
        throw new Error(err.detail || "Failed to delete user");
      }
    },
  },

  apiKeys: {
    async list(): Promise<ApiKeyItem[]> {
      const res = await authFetch(`${API_BASE}/api/v1/users/api-keys`);
      if (!res.ok) return [];
      const data = await res.json();
      return data.map((k: any) => ({
        id: k.id,
        name: k.name,
        prefix: k.prefix,
        role: k.role,
        createdDate: k.created_at ? k.created_at.split("T")[0] : "",
        expiresInDays: k.expires_at ? Math.max(0, Math.ceil((new Date(k.expires_at).getTime() - Date.now()) / (1000 * 86400))) : 90,
        status: k.is_active ? "active" : "revoked",
      }));
    },

    async create(name: string, role = "reviewer", expiresInDays = 90): Promise<{ api_key: string; key: ApiKeyItem }> {
      const targetRole = role === "admin" ? "reviewer" : role;
      const res = await authFetch(`${API_BASE}/api/v1/users/api-keys`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, role: targetRole, expires_in_days: expiresInDays }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Failed to create API key" }));
        throw new Error(err.detail || "Failed to create API key");
      }
      const data = await res.json();
      return {
        api_key: data.api_key,
        key: {
          id: data.id,
          name: data.name,
          prefix: data.prefix,
          role: data.role,
          createdDate: new Date().toISOString().split("T")[0],
          expiresInDays,
          status: "active",
        },
      };
    },

    async revoke(id: string): Promise<void> {
      const res = await authFetch(`${API_BASE}/api/v1/users/api-keys/${id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Failed to revoke API key" }));
        throw new Error(err.detail || "Failed to revoke API key");
      }
    },
  },

  tenants: {
    async getMe(): Promise<any> {
      const res = await authFetch(`${API_BASE}/api/v1/tenants/me`);
      if (!res.ok) throw new Error("Failed to load tenant info");
      return await res.json();
    },

    async updateSettings(data: { retention_days?: number; pii_masking_default?: boolean; webhook_url?: string }): Promise<any> {
      const res = await authFetch(`${API_BASE}/api/v1/tenants/me`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Failed to update tenant settings" }));
        throw new Error(err.detail || "Failed to update tenant settings");
      }
      return await res.json();
    },

    async testWebhook(url: string): Promise<any> {
      const res = await authFetch(`${API_BASE}/api/v1/tenants/test-webhook`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Webhook test failed" }));
        throw new Error(err.detail || "Webhook test failed");
      }
      return await res.json();
    },

    async runRetentionSweep(): Promise<any> {
      const res = await authFetch(`${API_BASE}/api/v1/documents/retention/sweep`, {
        method: "POST",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Failed to run retention sweep" }));
        throw new Error(err.detail || "Failed to run retention sweep");
      }
      return await res.json();
    },
  },

  rag: {
    async query(query: string, documentId?: string, topK: number = 5): Promise<RAGResponse> {
      const res = await authFetch(`${API_BASE}/api/v1/rag/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, document_id: documentId, top_k: topK }),
      });
      if (!res.ok) throw new Error("RAG query failed");
      return await res.json();
    },
  },
};
