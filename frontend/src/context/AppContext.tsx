"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from "react";
import { translations, TranslationKey } from "@/lib/translations";
import {
  DocumentItem,
  DocumentTypeSchema,
  AuditLogEntry,
  SystemUser,
  ApiKeyItem,
  TableRowItem,
} from "@/types";
import { api } from "@/lib/api";

export type ScreenId =
  | "dashboard"
  | "upload"
  | "documents"
  | "review"
  | "builder"
  | "audit"
  | "settings";

export type Language = "en" | "ar";
export type Theme = "light" | "dark";

export interface TenantInfo {
  id: string;
  nameEn: string;
  nameAr: string;
  slug: string;
  tier: string;
  region: string;
  sovereigntyNotice: string;
}

export interface ToastNotification {
  id: string;
  type: "success" | "error" | "info";
  messageEn: string;
  messageAr: string;
}

interface AppContextType {
  // Navigation & Core Environment
  language: Language;
  dir: "ltr" | "rtl";
  theme: Theme;
  useArabicDigits: boolean;
  activeTenant: TenantInfo;
  currentScreen: ScreenId;
  sidebarCollapsed: boolean;
  toggleLanguage: () => void;
  toggleTheme: () => void;
  toggleArabicDigits: () => void;
  toggleSidebar: () => void;
  setCurrentScreen: (screen: ScreenId) => void;
  t: (key: TranslationKey) => string;

  // Documents & Review State
  documents: DocumentItem[];
  selectedDocumentId: string;
  selectedDocument: DocumentItem | undefined;
  activeFieldKey: string | null;
  piiMasked: boolean;
  zoomLevel: number;
  activePage: number;
  setSelectedDocumentId: (id: string) => void;
  setActiveFieldKey: (key: string | null) => void;
  setZoomLevel: React.Dispatch<React.SetStateAction<number>>;
  setActivePage: (page: number) => void;
  togglePiiMasked: () => void;
  addDocument: (doc: DocumentItem) => void;
  refreshDocuments: () => Promise<void>;
  updateDocumentField: (docId: string, fieldKey: string, newValue: string) => Promise<void>;
  updateTableRow: (docId: string, rowId: string, field: keyof TableRowItem, value: any) => void;
  approveDocument: (docId: string) => Promise<void>;
  rejectDocument: (docId: string) => Promise<void>;
  deleteDocument: (docId: string) => Promise<void>;
  bulkApproveDocuments: (docIds: string[]) => void;
  bulkDeleteDocuments: (docIds: string[]) => void;

  // Schemas State
  schemas: DocumentTypeSchema[];
  addSchema: (schema: DocumentTypeSchema) => void;
  updateSchema: (schema: DocumentTypeSchema) => void;

  // Audit State
  auditLogs: AuditLogEntry[];
  refreshAuditLogs: () => Promise<void>;
  addAuditLog: (entry: Omit<AuditLogEntry, "id" | "timestamp">) => void;

  // Users & Settings State
  users: SystemUser[];
  apiKeys: ApiKeyItem[];
  retentionDays: number;
  hardDeleteDerived: boolean;
  webhookUrl: string;
  setRetentionDays: (days: number) => void;
  setHardDeleteDerived: (val: boolean) => void;
  setWebhookUrl: (url: string) => void;
  addUser: (name: string, email: string, role: SystemUser["role"]) => void;
  updateUserRole: (id: string, role: SystemUser["role"]) => void;
  generateApiKey: (name: string, role: string) => string;
  revokeApiKey: (id: string) => void;

  // Notifications
  toasts: ToastNotification[];
  dismissToast: (id: string) => void;
  showToast: (type: "success" | "error" | "info", messageEn: string, messageAr: string) => void;
}

const defaultTenant: TenantInfo = {
  id: "00000000-0000-0000-0000-000000000001",
  nameEn: "Al Hilal Islamic Bank UAE",
  nameAr: "مصرف الهلال الإسلامي - دولة الإمارات",
  slug: "alhilal-uae",
  tier: "Enterprise Tier 1",
  region: "UAE North (Abu Dhabi Sovereign Zone)",
  sovereigntyNotice: "100% In-Country UAE Data Boundary Active",
};

const AppContext = createContext<AppContextType | undefined>(undefined);

let toastSeq = 1;

export function AppProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>("en");
  const [theme, setTheme] = useState<Theme>("light");
  const [useArabicDigits, setUseArabicDigits] = useState<boolean>(false);
  const [currentScreen, setCurrentScreen] = useState<ScreenId>("dashboard");
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [activeTenant] = useState<TenantInfo>(defaultTenant);

  // Core Data Collections from live backend
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>("");
  const [activeFieldKey, setActiveFieldKey] = useState<string | null>("date_of_birth");
  const [piiMasked, setPiiMasked] = useState<boolean>(true);
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [activePage, setActivePage] = useState<number>(1);

  // Config Collections
  const [schemas, setSchemas] = useState<DocumentTypeSchema[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [users, setUsers] = useState<SystemUser[]>([]);
  const [apiKeys, setApiKeys] = useState<ApiKeyItem[]>([]);
  const [retentionDays, setRetentionDays] = useState<number>(365);
  const [hardDeleteDerived, setHardDeleteDerived] = useState<boolean>(true);
  const [webhookUrl, setWebhookUrl] = useState<string>(
    "https://api.alhilal-bank.ae/webhooks/doc-intelligence-approved"
  );
  const [toasts, setToasts] = useState<ToastNotification[]>([]);

  // Sync document dir and lang attributes
  useEffect(() => {
    const dir = language === "ar" ? "rtl" : "ltr";
    document.documentElement.dir = dir;
    document.documentElement.lang = language;
  }, [language]);

  // Sync theme class
  useEffect(() => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [theme]);

  const toggleLanguage = () => {
    setLanguage((prev) => (prev === "en" ? "ar" : "en"));
  };

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  const toggleArabicDigits = () => {
    setUseArabicDigits((prev) => !prev);
  };

  const toggleSidebar = () => {
    setSidebarCollapsed((prev) => !prev);
  };

  const showToast = (type: "success" | "error" | "info", messageEn: string, messageAr: string) => {
    const newToast: ToastNotification = {
      id: `toast-${Date.now()}-${toastSeq++}`,
      type,
      messageEn,
      messageAr,
    };
    setToasts((prev) => [newToast, ...prev.slice(0, 4)]);
  };

  const dismissToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const addAuditLog = (entry: Omit<AuditLogEntry, "id" | "timestamp">) => {
    const newEntry: AuditLogEntry = {
      ...entry,
      id: `aud-${Date.now()}`,
      timestamp: new Date().toISOString(),
    };
    setAuditLogs((prev) => [newEntry, ...prev]);
  };

  const refreshDocuments = useCallback(async () => {
    try {
      if (!api.auth.getToken()) {
        try {
          await api.auth.login("admin@alhilal-demo.ae", "AdminSecurePass2026!");
        } catch {
          return;
        }
      }
      const docs = await api.documents.list();
      setDocuments(docs || []);
      if (docs && docs.length > 0) {
        setSelectedDocumentId((prev) => {
          if (docs.some((d) => d.id === prev)) return prev;
          return docs[0].id;
        });
      }
    } catch {
      // Live server offline or network failure
    }
  }, []);

  const refreshAuditLogs = useCallback(async () => {
    try {
      const logs = await api.audit.list();
      setAuditLogs(logs || []);
    } catch {
      // Ignore
    }
  }, []);

  const refreshSchemas = useCallback(async () => {
    try {
      const liveSchemas = await api.schemas.list();
      setSchemas(liveSchemas || []);
    } catch {
      // Ignore
    }
  }, []);

  // Fetch initial live data and subscribe to real-time events on mount
  useEffect(() => {
    refreshDocuments();
    refreshAuditLogs();
    refreshSchemas();

    const unsubscribe = api.documents.subscribeTenantEvents(() => {
      refreshDocuments();
      refreshAuditLogs();
    });

    return () => {
      unsubscribe();
    };
  }, [refreshDocuments, refreshAuditLogs, refreshSchemas]);

  const togglePiiMasked = () => {
    setPiiMasked((prev) => !prev);
    addAuditLog({
      actorName: "Ahmed Al Mansoori",
      actorEmail: "admin@adcb.ae",
      actorRole: "Admin",
      action: "PII_UNMASKED",
      documentId: selectedDocumentId,
      documentRef: selectedDocument?.referenceNumber,
      ipAddress: "192.168.10.45",
      detailsEn: piiMasked ? "Admin unmasked PII view" : "Admin masked PII view",
      detailsAr: piiMasked ? "قام المشرف بإظهار البيانات الحساسة" : "قام المشرف بحجب البيانات الحساسة",
    });
  };

  const addDocument = (doc: DocumentItem) => {
    setDocuments((prev) => [doc, ...prev.filter((d) => d.id !== doc.id)]);
    setSelectedDocumentId(doc.id);
    addAuditLog({
      actorName: "Ahmed Al Mansoori",
      actorEmail: "admin@adcb.ae",
      actorRole: "Admin",
      action: "DOCUMENT_UPLOAD",
      documentId: doc.id,
      documentRef: doc.referenceNumber,
      ipAddress: "192.168.10.45",
      detailsEn: `Uploaded document '${doc.fileName}' (${doc.documentTypeNameEn})`,
      detailsAr: `تم رفع المستند '${doc.fileName}' (${doc.documentTypeNameAr})`,
    });
  };

  const updateDocumentField = async (docId: string, fieldKey: string, newValue: string) => {
    setDocuments((prev) =>
      prev.map((doc) => {
        if (doc.id !== docId) return doc;
        const updatedFields = doc.fields.map((f) => {
          if (f.key !== fieldKey) return f;
          return {
            ...f,
            value: newValue,
            isCorrected: newValue !== f.originalValue,
            confidence: 1.0,
          };
        });
        const updatedErrors = doc.validationErrors.filter((e) => e.fieldKey !== fieldKey);
        return {
          ...doc,
          fields: updatedFields,
          validationErrors: updatedErrors,
        };
      })
    );

    try {
      await api.documents.correctField(docId, fieldKey, newValue);
    } catch (err: any) {
      showToast("error", `Failed to save correction to server: ${err.message}`, "فشل حفظ التعديل على الخادم");
    }

    addAuditLog({
      actorName: "Ahmed Al Mansoori",
      actorEmail: "admin@adcb.ae",
      actorRole: "Admin",
      action: "FIELD_CORRECTED",
      documentId: docId,
      documentRef: selectedDocument?.referenceNumber,
      ipAddress: "192.168.10.45",
      detailsEn: `Corrected field '${fieldKey}' to '${newValue}'`,
      detailsAr: `تم تعديل وتصحيح الحقل '${fieldKey}' إلى '${newValue}'`,
      diff: {
        field: fieldKey,
        oldValue: selectedDocument?.fields.find((f) => f.key === fieldKey)?.value || "",
        newValue,
      },
    });

    showToast("info", `Field '${fieldKey}' updated and saved!`, `تم تحديث وحفظ الحقل '${fieldKey}'!`);
  };

  const updateTableRow = (docId: string, rowId: string, field: keyof TableRowItem, value: any) => {
    setDocuments((prev) =>
      prev.map((doc) => {
        if (doc.id !== docId || !doc.tableData) return doc;
        const updatedTable = doc.tableData.map((row) => {
          if (row.id !== rowId) return row;
          const updated = { ...row, [field]: value };
          if (field === "quantity" || field === "unitPriceAED") {
            const raw = updated.quantity * updated.unitPriceAED;
            updated.lineTotalAED = raw + raw * updated.vatRate;
          }
          return updated;
        });

        const sumLineTotals = updatedTable.reduce((acc, r) => acc + r.lineTotalAED, 0);
        const updatedFields = doc.fields.map((f) => {
          if (f.key === "total_amount") {
            return {
              ...f,
              value: sumLineTotals.toFixed(2),
              isCorrected: true,
              confidence: 1.0,
            };
          }
          return f;
        });

        return {
          ...doc,
          tableData: updatedTable,
          fields: updatedFields,
          status: "needs_review",
        };
      })
    );

    showToast("success", "Table row updated and total rebalanced!", "تم تحديث بند الجدول وإعادة موازنة المجموع!");
  };

  const approveDocument = async (docId: string) => {
    setDocuments((prev) =>
      prev.map((doc) => {
        if (doc.id !== docId) return doc;
        return {
          ...doc,
          status: "approved",
          reviewedBy: "Ahmed Al Mansoori",
          validationErrors: [],
        };
      })
    );

    try {
      await api.documents.approve(docId);
    } catch (err: any) {
      showToast("error", `Failed to approve document: ${err.message}`, "فشل اعتماد المستند");
    }

    addAuditLog({
      actorName: "Ahmed Al Mansoori",
      actorEmail: "admin@adcb.ae",
      actorRole: "Admin",
      action: "DOCUMENT_APPROVED",
      documentId: docId,
      documentRef: selectedDocument?.referenceNumber,
      ipAddress: "192.168.10.45",
      detailsEn: `Approved document ${selectedDocument?.referenceNumber}. Webhook dispatched.`,
      detailsAr: `تم اعتماد المستند ${selectedDocument?.referenceNumber}. تم إطلاق الويب هوك.`,
    });

    showToast(
      "success",
      `Document ${selectedDocument?.referenceNumber} approved successfully!`,
      `تم اعتماد المستند ${selectedDocument?.referenceNumber} بنجاح!`
    );
  };

  const rejectDocument = async (docId: string) => {
    setDocuments((prev) =>
      prev.map((doc) => {
        if (doc.id !== docId) return doc;
        return {
          ...doc,
          status: "failed",
          reviewedBy: "Ahmed Al Mansoori",
        };
      })
    );

    try {
      await api.documents.reject(docId, "Rejected during human review");
    } catch (err: any) {
      showToast("error", `Failed to reject document: ${err.message}`, "فشل رفض المستند");
    }

    addAuditLog({
      actorName: "Ahmed Al Mansoori",
      actorEmail: "admin@adcb.ae",
      actorRole: "Admin",
      action: "DOCUMENT_REJECTED",
      documentId: docId,
      documentRef: selectedDocument?.referenceNumber,
      ipAddress: "192.168.10.45",
      detailsEn: `Rejected document ${selectedDocument?.referenceNumber} due to compliance check failure.`,
      detailsAr: `تم رفض المستند ${selectedDocument?.referenceNumber} لعدم اجتياز الفحص الرقابي.`,
    });

    showToast(
      "error",
      `Document ${selectedDocument?.referenceNumber} marked as rejected.`,
      `تم رفض المستند ${selectedDocument?.referenceNumber}.`
    );
  };

  const deleteDocument = async (docId: string) => {
    const docToDelete = documents.find((d) => d.id === docId);
    setDocuments((prev) => prev.filter((doc) => doc.id !== docId));

    try {
      await api.documents.delete(docId);
    } catch (err: any) {
      showToast("error", `Failed to delete document: ${err.message}`, "فشل حذف المستند");
    }

    addAuditLog({
      actorName: "Ahmed Al Mansoori",
      actorEmail: "admin@adcb.ae",
      actorRole: "Admin",
      action: "DOCUMENT_DELETED",
      documentId: docId,
      documentRef: docToDelete?.referenceNumber,
      ipAddress: "192.168.10.45",
      detailsEn: `Hard deleted document and purged all derived embeddings & OCR text per UAE retention policy.`,
      detailsAr: `تم الحذف النهائي للمستند وتطهير كافة البيانات والنصوص المستخرجة طبقاً لسياسة الاحتفاظ.`,
    });

    showToast("info", "Document permanently deleted.", "تم حذف المستند نهائياً.");
  };

  const bulkApproveDocuments = (docIds: string[]) => {
    setDocuments((prev) =>
      prev.map((doc) => (docIds.includes(doc.id) ? { ...doc, status: "approved" } : doc))
    );
    docIds.forEach((id) => approveDocument(id));
    showToast(
      "success",
      `Bulk approved ${docIds.length} documents!`,
      `تم اعتماد ${docIds.length} مستندات بنجاح!`
    );
  };

  const bulkDeleteDocuments = (docIds: string[]) => {
    setDocuments((prev) => prev.filter((doc) => !docIds.includes(doc.id)));
    docIds.forEach((id) => deleteDocument(id));
    showToast(
      "info",
      `Hard deleted ${docIds.length} documents.`,
      `تم الحذف النهائي لعدد ${docIds.length} مستندات.`
    );
  };

  const addSchema = (schema: DocumentTypeSchema) => {
    setSchemas((prev) => [...prev, schema]);
    addAuditLog({
      actorName: "Ahmed Al Mansoori",
      actorEmail: "admin@adcb.ae",
      actorRole: "Admin",
      action: "SCHEMA_MODIFIED",
      detailsEn: `Created custom schema '${schema.nameEn}' (${schema.code})`,
      detailsAr: `تم إنشاء قالب مخصص '${schema.nameAr}' (${schema.code})`,
      ipAddress: "192.168.10.45",
    });
    showToast("success", `Schema '${schema.nameEn}' created!`, `تم إنشاء القالب '${schema.nameAr}'!`);
  };

  const updateSchema = (schema: DocumentTypeSchema) => {
    setSchemas((prev) => prev.map((s) => (s.id === schema.id ? schema : s)));
    addAuditLog({
      actorName: "Ahmed Al Mansoori",
      actorEmail: "admin@adcb.ae",
      actorRole: "Admin",
      action: "SCHEMA_MODIFIED",
      detailsEn: `Updated schema definition '${schema.nameEn}'`,
      detailsAr: `تم تحديث بنية القالب '${schema.nameAr}'`,
      ipAddress: "192.168.10.45",
    });
    showToast("info", `Schema '${schema.nameEn}' updated.`, `تم تحديث القالب '${schema.nameAr}'.`);
  };

  const addUser = (name: string, email: string, role: SystemUser["role"]) => {
    const newUser: SystemUser = {
      id: `usr-${Date.now()}`,
      name,
      email,
      role,
      status: "active",
      lastLogin: new Date().toISOString(),
    };
    setUsers((prev) => [...prev, newUser]);
    showToast("success", `User ${name} added successfully!`, `تمت إضافة المستخدم ${name} بنجاح!`);
  };

  const updateUserRole = (id: string, role: SystemUser["role"]) => {
    setUsers((prev) => prev.map((u) => (u.id === id ? { ...u, role } : u)));
    showToast("info", "User permissions updated.", "تم تحديث صلاحيات المستخدم.");
  };

  const generateApiKey = (name: string, role: string) => {
    const prefix = `sn_${name.toLowerCase().replace(/\s+/g, "_").slice(0, 4)}`;
    const secret = `sec_${Date.now()}_prod`;
    const newKey: ApiKeyItem = {
      id: `key-${Date.now()}`,
      name,
      prefix,
      role,
      createdDate: new Date().toISOString().split("T")[0],
      expiresInDays: 90,
      status: "active",
    };
    setApiKeys((prev) => [newKey, ...prev]);
    showToast("success", `API key '${name}' created!`, `تم إصدار المفتاح البرمجي '${name}'!`);
    return `${prefix}_${secret}`;
  };

  const revokeApiKey = (id: string) => {
    setApiKeys((prev) => prev.map((k) => (k.id === id ? { ...k, status: "revoked" } : k)));
    showToast("info", "API key revoked.", "تم إلغاء تفعيل المفتاح البرمجي.");
  };

  const selectedDocument = documents.find((d) => d.id === selectedDocumentId) || documents[0];

  const t = (key: TranslationKey): string => {
    const translationObj = translations[key];
    if (!translationObj) return key;
    return translationObj[language] || translationObj.en || key;
  };

  return (
    <AppContext.Provider
      value={{
        language,
        dir: language === "ar" ? "rtl" : "ltr",
        theme,
        useArabicDigits,
        activeTenant,
        currentScreen,
        sidebarCollapsed,
        toggleLanguage,
        toggleTheme,
        toggleArabicDigits,
        toggleSidebar,
        setCurrentScreen,
        t,

        documents,
        selectedDocumentId,
        selectedDocument,
        activeFieldKey,
        piiMasked,
        zoomLevel,
        activePage,
        setSelectedDocumentId,
        setActiveFieldKey,
        setZoomLevel,
        setActivePage,
        togglePiiMasked,
        addDocument,
        refreshDocuments,
        updateDocumentField,
        updateTableRow,
        approveDocument,
        rejectDocument,
        deleteDocument,
        bulkApproveDocuments,
        bulkDeleteDocuments,

        schemas,
        addSchema,
        updateSchema,

        auditLogs,
        refreshAuditLogs,
        addAuditLog,

        users,
        apiKeys,
        retentionDays,
        hardDeleteDerived,
        webhookUrl,
        setRetentionDays,
        setHardDeleteDerived,
        setWebhookUrl,
        addUser,
        updateUserRole,
        generateApiKey,
        revokeApiKey,

        toasts,
        dismissToast,
        showToast,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
}
