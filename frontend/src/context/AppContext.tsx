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
import { DEFAULT_STANDARD_SCHEMAS } from "@/lib/defaultSchemas";

export type ScreenId =
  | "command"
  | "dashboard"
  | "upload"
  | "documents"
  | "review"
  | "builder"
  | "schemas"
  | "audit"
  | "governance"
  | "team"
  | "settings"
  | "ask"
  | "welcome"
  | "landing";

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
  isMobileMenuOpen: boolean;
  isUploadModalOpen: boolean;
  isCommandPaletteOpen: boolean;
  setIsMobileMenuOpen: (open: boolean) => void;
  setIsUploadModalOpen: (open: boolean) => void;
  setIsCommandPaletteOpen: (open: boolean) => void;
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
  approveDocument: (docId: string, force?: boolean) => Promise<void>;
  rejectDocument: (docId: string) => Promise<void>;
  deleteDocument: (docId: string) => Promise<void>;
  bulkApproveDocuments: (docIds: string[]) => void;
  bulkDeleteDocuments: (docIds: string[]) => void;

  // Schemas State
  schemas: DocumentTypeSchema[];
  refreshSchemas: () => Promise<void>;
  addSchema: (schema: DocumentTypeSchema) => Promise<void>;
  updateSchema: (schema: DocumentTypeSchema) => Promise<void>;
  deleteSchema: (id: string) => Promise<void>;

  // Audit State
  auditLogs: AuditLogEntry[];
  refreshAuditLogs: () => Promise<void>;
  addAuditLog: (entry: Omit<AuditLogEntry, "id" | "timestamp">) => void;

  // Users & Settings State
  isAuthenticated: boolean;
  setIsAuthenticated: (val: boolean) => void;
  currentUser: SystemUser | null;
  userRole: "admin" | "reviewer" | "viewer";
  logout: () => void;
  users: SystemUser[];
  refreshUsers: () => Promise<void>;
  apiKeys: ApiKeyItem[];
  refreshApiKeys: () => Promise<void>;
  retentionDays: number;
  hardDeleteDerived: boolean;
  webhookUrl: string;
  setRetentionDays: (days: number) => void;
  saveRetentionDays: (days: number) => Promise<void>;
  setHardDeleteDerived: (val: boolean) => void;
  setWebhookUrl: (url: string) => void;
  testWebhook: (targetUrl?: string) => Promise<any>;
  runRetentionSweep: () => Promise<void>;
  addUser: (name: string, email: string, role: SystemUser["role"], password?: string) => Promise<void>;
  updateUserRole: (id: string, role: SystemUser["role"]) => Promise<void>;
  deleteUser: (id: string) => Promise<void>;
  generateApiKey: (name: string, role: string) => Promise<string>;
  revokeApiKey: (id: string) => Promise<void>;

  // Notifications
  toasts: ToastNotification[];
  dismissToast: (id: string) => void;
  showToast: (type: "success" | "error" | "info", messageEn: string, messageAr: string) => void;
}

const defaultTenant: TenantInfo = {
  id: "00000000-0000-0000-0000-000000000001",
  nameEn: "Organization Workspace",
  nameAr: "مساحة عمل المؤسسة",
  slug: "tenant",
  tier: "Enterprise Tier 1",
  region: "UAE Sovereign Zone",
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
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);
  const [activeTenant, setActiveTenant] = useState<TenantInfo>(defaultTenant);

  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [currentUser, setCurrentUser] = useState<SystemUser | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>("");
  const [activeFieldKey, setActiveFieldKey] = useState<string | null>("date_of_birth");
  const [piiMasked, setPiiMasked] = useState<boolean>(true);
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [activePage, setActivePage] = useState<number>(1);

  // Config Collections
  const [schemas, setSchemas] = useState<DocumentTypeSchema[]>(DEFAULT_STANDARD_SCHEMAS);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [users, setUsers] = useState<SystemUser[]>([]);
  const [apiKeys, setApiKeys] = useState<ApiKeyItem[]>([]);
  const [retentionDays, setRetentionDays] = useState<number>(365);
  const [hardDeleteDerived, setHardDeleteDerived] = useState<boolean>(true);
  const [webhookUrl, setWebhookUrl] = useState<string>("");
  const [toasts, setToasts] = useState<ToastNotification[]>([]);

  const userRole: "admin" | "reviewer" | "viewer" = (currentUser?.role as any) || "viewer";

  const showToast = useCallback((type: "success" | "error" | "info", messageEn: string, messageAr: string) => {
    const newToast: ToastNotification = {
      id: `toast-${Date.now()}-${toastSeq++}`,
      type,
      messageEn,
      messageAr,
    };
    setToasts((prev) => [newToast, ...prev.slice(0, 4)]);
  }, []);

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
      if (!api.auth.getToken()) return;
      const docs = await api.documents.list();
      setDocuments(docs || []);
      if (docs && docs.length > 0) {
        setSelectedDocumentId((prev) => {
          if (docs.some((d) => d.id === prev)) return prev;
          return docs[0].id;
        });
      }
    } catch {}
  }, []);

  const refreshAuditLogs = useCallback(async () => {
    try {
      if (!api.auth.getToken()) return;
      const logs = await api.audit.list();
      setAuditLogs(logs || []);
    } catch {}
  }, []);

  const refreshSchemas = useCallback(async () => {
    try {
      if (!api.auth.getToken()) return;
      const liveSchemas = await api.schemas.list();
      if (liveSchemas && liveSchemas.length > 0) {
        setSchemas(liveSchemas);
      }
    } catch {}
  }, []);

  const refreshUsers = useCallback(async () => {
    try {
      if (!api.auth.getToken()) return;
      const liveUsers = await api.users.list();
      setUsers(liveUsers || []);
    } catch {}
  }, []);

  const refreshApiKeys = useCallback(async () => {
    try {
      if (!api.auth.getToken()) return;
      const liveKeys = await api.apiKeys.list();
      setApiKeys(liveKeys || []);
    } catch {}
  }, []);

  const refreshTenantSettings = useCallback(async () => {
    try {
      if (!api.auth.getToken()) return;
      const tenant = await api.tenants.getMe();
      if (tenant) {
        if (tenant.name) {
          setActiveTenant((prev) => ({
            ...prev,
            id: tenant.id || prev.id,
            nameEn: tenant.name,
            nameAr: tenant.name_ar || tenant.name,
          }));
        }
        if (tenant.webhook_url !== undefined && tenant.webhook_url !== null) {
          setWebhookUrl(tenant.webhook_url);
        }
        if (tenant.retention_days) {
          setRetentionDays(tenant.retention_days);
        }
        if (tenant.pii_masking_default !== undefined) {
          setPiiMasked(tenant.pii_masking_default);
        }
      }
    } catch {}
  }, []);

  const loadUserProfile = useCallback(async () => {
    try {
      if (!api.auth.getToken()) return;
      const me = await api.auth.getMe();
      if (me) {
        setCurrentUser({
          id: me.id,
          name: me.name || me.email?.split("@")[0] || "User",
          email: me.email,
          role: me.role || "viewer",
          status: "active",
          lastLogin: "Active now",
        });
      }
    } catch {}
  }, []);

  // Check authentication status on mount & listen for 401 unauthorized
  useEffect(() => {
    const token = api.auth.getToken();
    if (token) {
      setIsAuthenticated(true);
      loadUserProfile();
      refreshDocuments();
      refreshAuditLogs();
      refreshSchemas();
      refreshUsers();
      refreshApiKeys();
      refreshTenantSettings();
    } else {
      const autoPref = typeof window !== "undefined" ? localStorage.getItem("sanad_auto_login") : null;
      if (autoPref !== "false") {
        api.auth.login("admin@alhilal-demo.ae", "AdminSecurePass2026!").then(() => {
          setIsAuthenticated(true);
          loadUserProfile();
          refreshDocuments();
          refreshAuditLogs();
          refreshSchemas();
          refreshUsers();
          refreshApiKeys();
          refreshTenantSettings();
        }).catch(() => {
          setIsAuthenticated(false);
        });
      } else {
        setIsAuthenticated(false);
      }
    }

    const handleUnauthorized = () => {
      setIsAuthenticated(false);
      setCurrentUser(null);
      setDocuments([]);
      setAuditLogs([]);
      setUsers([]);
      setApiKeys([]);
    };
    window.addEventListener("sanad:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("sanad:unauthorized", handleUnauthorized);
  }, [loadUserProfile, refreshDocuments, refreshAuditLogs, refreshSchemas, refreshUsers, refreshApiKeys, refreshTenantSettings]);

  const logout = useCallback(() => {
    api.auth.logout();
    setIsAuthenticated(false);
    setCurrentUser(null);
    setDocuments([]);
    setAuditLogs([]);
    setUsers([]);
    setApiKeys([]);
  }, []);

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

  // Subscribe to real-time events on mount
  useEffect(() => {
    if (!isAuthenticated) return;
    const unsubscribe = api.documents.subscribeTenantEvents(() => {
      refreshDocuments();
      refreshAuditLogs();
    });

    return () => {
      unsubscribe();
    };
  }, [isAuthenticated, refreshDocuments, refreshAuditLogs]);

  const togglePiiMasked = async () => {
    const nextVal = !piiMasked;
    setPiiMasked(nextVal);
    try {
      await api.tenants.updateSettings({ pii_masking_default: nextVal });
      refreshAuditLogs();
    } catch {}
  };

  const addDocument = (doc: DocumentItem) => {
    setDocuments((prev) => [doc, ...prev.filter((d) => d.id !== doc.id)]);
    setSelectedDocumentId(doc.id);
    refreshAuditLogs();
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
      await refreshDocuments();
      await refreshAuditLogs();
      showToast("info", `Field '${fieldKey}' updated and saved!`, `تم تحديث وحفظ الحقل '${fieldKey}'!`);
    } catch (err: any) {
      showToast("error", `Failed to save correction: ${err.message}`, "فشل حفظ التعديل على الخادم");
    }
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

  const approveDocument = async (docId: string, force = false) => {
    try {
      await api.documents.approve(docId, force);
      await refreshDocuments();
      await refreshAuditLogs();
      showToast(
        "success",
        `Document approved successfully!`,
        `تم اعتماد المستند بنجاح!`
      );
    } catch (err: any) {
      showToast("error", `Failed to approve document: ${err.message}`, "فشل اعتماد المستند");
      throw err;
    }
  };

  const rejectDocument = async (docId: string) => {
    try {
      await api.documents.reject(docId, "Rejected during human review");
      await refreshDocuments();
      await refreshAuditLogs();
      showToast(
        "error",
        `Document marked as rejected.`,
        `تم رفض المستند.`
      );
    } catch (err: any) {
      showToast("error", `Failed to reject document: ${err.message}`, "فشل رفض المستند");
    }
  };

  const deleteDocument = async (docId: string) => {
    try {
      await api.documents.delete(docId);
      setDocuments((prev) => prev.filter((doc) => doc.id !== docId));
      await refreshAuditLogs();
      showToast("info", "Document permanently deleted.", "تم حذف المستند نهائياً.");
    } catch (err: any) {
      showToast("error", `Failed to delete document: ${err.message}`, "فشل حذف المستند");
    }
  };

  const bulkApproveDocuments = (docIds: string[]) => {
    docIds.forEach((id) => approveDocument(id));
  };

  const bulkDeleteDocuments = (docIds: string[]) => {
    docIds.forEach((id) => deleteDocument(id));
  };

  const addSchema = async (schema: DocumentTypeSchema) => {
    try {
      const saved = await api.schemas.save(schema);
      await refreshSchemas();
      await refreshAuditLogs();
      showToast("success", `Schema '${saved.nameEn}' created!`, `تم إنشاء القالب '${saved.nameAr}'!`);
    } catch (err: any) {
      showToast("error", `Failed to save schema: ${err.message}`, "فشل حفظ القالب");
    }
  };

  const updateSchema = async (schema: DocumentTypeSchema) => {
    try {
      const saved = await api.schemas.save(schema);
      await refreshSchemas();
      await refreshAuditLogs();
      showToast("info", `Schema '${saved.nameEn}' updated.`, `تم تحديث القالب '${saved.nameAr}'.`);
    } catch (err: any) {
      showToast("error", `Failed to update schema: ${err.message}`, "فشل تحديث القالب");
    }
  };

  const deleteSchema = async (id: string) => {
    try {
      await api.schemas.delete(id);
      await refreshSchemas();
      await refreshAuditLogs();
      showToast("info", "Schema deleted.", "تم حذف القالب.");
    } catch (err: any) {
      showToast("error", `Failed to delete schema: ${err.message}`, "فشل حذف القالب");
    }
  };

  const addUser = async (name: string, email: string, role: SystemUser["role"], password?: string) => {
    try {
      const created = await api.users.create(name, email, role, password);
      await refreshUsers();
      await refreshAuditLogs();
      showToast("success", `User ${created.email} added!`, `تمت إضافة المستخدم ${created.email} بنجاح!`);
    } catch (err: any) {
      showToast("error", `Failed to add user: ${err.message}`, "فشل إضافة المستخدم");
      throw err;
    }
  };

  const updateUserRole = async (id: string, role: SystemUser["role"]) => {
    try {
      await api.users.updateRole(id, role);
      await refreshUsers();
      await refreshAuditLogs();
      showToast("info", "User permissions updated.", "تم تحديث صلاحيات المستخدم.");
    } catch (err: any) {
      showToast("error", `Failed to update user role: ${err.message}`, "فشل تحديث صلاحيات المستخدم");
    }
  };

  const deleteUser = async (id: string) => {
    try {
      await api.users.delete(id);
      await refreshUsers();
      await refreshAuditLogs();
      showToast("info", "User deleted.", "تم حذف المستخدم.");
    } catch (err: any) {
      showToast("error", `Failed to delete user: ${err.message}`, "فشل حذف المستخدم");
    }
  };

  const generateApiKey = async (name: string, role: string): Promise<string> => {
    try {
      const res = await api.apiKeys.create(name, role);
      await refreshApiKeys();
      await refreshAuditLogs();
      showToast("success", `API key '${name}' created!`, `تم إصدار المفتاح البرمجي '${name}'!`);
      return res.api_key;
    } catch (err: any) {
      showToast("error", `Failed to generate API key: ${err.message}`, "فشل إصدار المفتاح البرمجي");
      return "";
    }
  };

  const revokeApiKey = async (id: string) => {
    try {
      await api.apiKeys.revoke(id);
      await refreshApiKeys();
      await refreshAuditLogs();
      showToast("info", "API key revoked.", "تم إلغاء تفعيل المفتاح البرمجي.");
    } catch (err: any) {
      showToast("error", `Failed to revoke key: ${err.message}`, "فشل إلغاء المفتاح");
    }
  };

  const saveRetentionDays = async (days: number) => {
    setRetentionDays(days);
    try {
      await api.tenants.updateSettings({ retention_days: days });
      await refreshAuditLogs();
      showToast("success", `Retention set to ${days} days`, `تم تعيين مدة الاحتفاظ إلى ${days} يوماً`);
    } catch (err: any) {
      showToast("error", `Failed to update retention: ${err.message}`, "فشل تحديث سياسة الاحتفاظ");
    }
  };

  const runRetentionSweep = async () => {
    try {
      const res = await api.tenants.runRetentionSweep();
      await refreshDocuments();
      await refreshAuditLogs();
      const count = res.total_purged !== undefined ? res.total_purged : (res.purged_count || 0);
      showToast(
        "success",
        `Retention sweep executed: ${count} expired documents purged.`,
        `تم تنفيذ مسح الاحتفاظ: تم حذف ${count} مستندات منتهية الصلاحية.`
      );
    } catch (err: any) {
      showToast("error", `Retention sweep failed: ${err.message}`, "فشل تنفيذ مسح الاحتفاظ");
    }
  };

  const testWebhook = async (targetUrl?: string) => {
    try {
      const urlToTest = targetUrl || webhookUrl;
      const res = await api.tenants.testWebhook(urlToTest);
      showToast(
        res.dispatched ? "success" : "info",
        `Webhook evaluated: dispatched=${res.dispatched} (${res.reason})`,
        `تم تقييم الويب هوك: تم الإرسال=${res.dispatched}`
      );
      return res;
    } catch (err: any) {
      showToast("error", `Webhook test error: ${err.message}`, "خطأ أثناء اختبار الويب هوك");
    }
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
        isMobileMenuOpen,
        isUploadModalOpen,
        isCommandPaletteOpen,
        setIsMobileMenuOpen,
        setIsUploadModalOpen,
        setIsCommandPaletteOpen,
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
        refreshSchemas,
        addSchema,
        updateSchema,
        deleteSchema,

        auditLogs,
        refreshAuditLogs,
        addAuditLog,

        isAuthenticated,
        setIsAuthenticated,
        currentUser,
        userRole,
        logout,
        users,
        refreshUsers,
        apiKeys,
        refreshApiKeys,
        retentionDays,
        hardDeleteDerived,
        webhookUrl,
        setRetentionDays,
        saveRetentionDays,
        setHardDeleteDerived,
        setWebhookUrl,
        testWebhook,
        runRetentionSweep,
        addUser,
        updateUserRole,
        deleteUser,
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
