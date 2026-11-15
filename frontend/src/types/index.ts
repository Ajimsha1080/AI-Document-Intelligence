export type DocumentStatus = "processing" | "needs_review" | "approved" | "failed";
export type DocumentTypeCode = "emirates_id" | "uae_trade_license" | "commercial_invoice";
export type FieldDataType = "string" | "number" | "date" | "regex" | "currency";

export interface BoundingBox {
  x: number;      // normalized 0..1 or percentage
  y: number;      // normalized 0..1 or percentage
  width: number;  // normalized 0..1 or percentage
  height: number; // normalized 0..1 or percentage
  page: number;
}

export interface ExtractedField {
  id: string;
  key: string;
  nameEn: string;
  nameAr: string;
  value: string | null;
  originalValue: string | null;
  confidence: number; // 0..1
  section: "identity" | "company" | "dates" | "financials" | "general";
  page: number;
  bbox?: BoundingBox;
  isCorrected?: boolean;
  required?: boolean;
  validationError?: string;
}

export interface TableRowItem {
  id: string;
  itemDescription: string;
  quantity: number;
  unitPriceAED: number;
  vatRate: number; // e.g. 0.05
  lineTotalAED: number;
}

export interface ValidationErrorItem {
  id: string;
  fieldKey?: string;
  severity: "error" | "warning";
  messageEn: string;
  messageAr: string;
  isResolved?: boolean;
}

export interface DocumentItem {
  id: string;
  referenceNumber: string;
  fileName: string;
  documentType: DocumentTypeCode;
  documentTypeNameEn: string;
  documentTypeNameAr: string;
  status: DocumentStatus;
  overallConfidence: number;
  uploadedAt: string;
  processedAt: string;
  reviewedBy?: string;
  fileSizeKB: number;
  pageCount: number;
  fields: ExtractedField[];
  tableData?: TableRowItem[];
  validationErrors: ValidationErrorItem[];
  previewUrl: string; // SVG or simulated document
  extractedLanguage: "ara" | "eng" | "mixed";
}

export interface SchemaFieldDefinition {
  id: string;
  key: string;
  nameEn: string;
  nameAr: string;
  dataType: FieldDataType;
  required: boolean;
  confidenceThreshold: number;
  validationRegex?: string;
  section: string;
}

export interface ValidationRuleDefinition {
  id: string;
  nameEn: string;
  nameAr: string;
  ruleType: "not_expired" | "format_match" | "totals_match" | "required_field";
  targetField: string;
  severity: "error" | "warning";
  enabled: boolean;
}

export interface DocumentTypeSchema {
  id: string;
  code: DocumentTypeCode;
  nameEn: string;
  nameAr: string;
  descriptionEn: string;
  descriptionAr: string;
  fields: SchemaFieldDefinition[];
  rules: ValidationRuleDefinition[];
  isStandard: boolean;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  actorName: string;
  actorEmail: string;
  actorRole: "Admin" | "Reviewer" | "Viewer" | "API Client";
  action:
    | "DOCUMENT_UPLOAD"
    | "FIELD_CORRECTED"
    | "DOCUMENT_APPROVED"
    | "DOCUMENT_REJECTED"
    | "DOCUMENT_EXPORTED"
    | "DOCUMENT_DELETED"
    | "PII_UNMASKED"
    | "SCHEMA_MODIFIED"
    | "API_KEY_GENERATED";
  documentId?: string;
  documentRef?: string;
  ipAddress: string;
  detailsEn: string;
  detailsAr: string;
  diff?: {
    field: string;
    oldValue: string;
    newValue: string;
  };
}

export interface SystemUser {
  id: string;
  name: string;
  email: string;
  role: "admin" | "reviewer" | "viewer" | "api_client";
  status: "active" | "invited" | "deactivated";
  lastLogin: string;
}

export interface ApiKeyItem {
  id: string;
  name: string;
  prefix: string;
  role: string;
  createdDate: string;
  expiresInDays: number;
  status: "active" | "revoked";
}
