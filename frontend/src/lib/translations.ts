export type TranslationKey = keyof typeof translations;

export const translations = {
  // Brand & Header
  appName: {
    en: "Sanad DocIntel",
    ar: "سند لذكاء المستندات",
  },
  appTagline: {
    en: "UAE Sovereign Document Intelligence",
    ar: "منصة ذكاء المستندات السيادية لدولة الإمارات",
  },
  searchPlaceholder: {
    en: "Search documents, Emirates IDs, license numbers... (Cmd+K)",
    ar: "البحث في المستندات، الهوية الإماراتية، الرخص... (Cmd+K)",
  },
  sovereignBadge: {
    en: "UAE Sovereign Cloud • Zero Egress",
    ar: "سحابة سيادية إماراتية • معالجة داخل الدولة",
  },
  tenantLabel: {
    en: "Active Bank / Entity",
    ar: "المصرف / الجهة النشطة",
  },
  notifications: {
    en: "Notifications",
    ar: "الإشعارات",
  },
  userProfile: {
    en: "User Profile",
    ar: "الملف التعريفي",
  },
  roleAdmin: {
    en: "Compliance Admin",
    ar: "مدير الامتثال والرقابة",
  },

  // Navigation Items
  navDashboard: {
    en: "Dashboard",
    ar: "لوحة التحكم",
  },
  navUpload: {
    en: "Upload Documents",
    ar: "تحميل المستندات",
  },
  navDocuments: {
    en: "Document Management Center",
    ar: "مركز إدارة المستندات",
  },
  navReview: {
    en: "Review Queue",
    ar: "طابور المراجعة والتدقيق",
  },
  navBuilder: {
    en: "Schema Builder",
    ar: "منشئ المخططات",
  },
  navAudit: {
    en: "Immutable Audit Log",
    ar: "سجل التدقيق والامتثال",
  },
  navTeam: {
    en: "Team",
    ar: "فريق العمل",
  },
  navSettings: {
    en: "Settings & Sovereignty",
    ar: "الإعدادات والسيادة الرقمية",
  },

  // Status Badges
  statusProcessing: {
    en: "Processing",
    ar: "قيد المعالجة",
  },
  statusNeedsReview: {
    en: "Needs Review",
    ar: "يتطلب مراجعة",
  },
  statusApproved: {
    en: "Approved",
    ar: "معتمد ومطابق",
  },
  statusFailed: {
    en: "Validation Error",
    ar: "خطأ في التحقق",
  },

  // Confidence Badges
  confidenceHigh: {
    en: "High Confidence",
    ar: "ثقة عالية",
  },
  confidenceMedium: {
    en: "Medium Confidence",
    ar: "ثقة متوسطة",
  },
  confidenceLow: {
    en: "Low Confidence",
    ar: "ثقة منخفضة",
  },

  // Actions
  actionApprove: {
    en: "Approve Document",
    ar: "اعتماد المستند",
  },
  actionReject: {
    en: "Reject Document",
    ar: "رفض المستند",
  },
  actionSendBack: {
    en: "Send Back for Rescan",
    ar: "إعادة لطلب إعادة المسح",
  },
  actionExport: {
    en: "Export Data",
    ar: "تصدير البيانات",
  },
  actionDelete: {
    en: "Hard Delete",
    ar: "حذف نهائي",
  },
  actionJumpToSource: {
    en: "Jump to Source Location",
    ar: "الانتقال إلى موضع الاستخراج",
  },

  // Keyboard Shortcuts
  shortcutHint: {
    en: "Shortcuts: [J] Next field • [K] Prev field • [Enter] Approve • [M] Mask PII",
    ar: "اختصارات: [J] الحقل التالي • [K] الحقل السابق • [Enter] اعتماد • [M] حجب البيانات",
  },

  // Language & Numerals
  toggleLanguage: {
    en: "العربية",
    ar: "English",
  },
  toggleDigits: {
    en: "Arabic-Indic Digits (٠-٩)",
    ar: "الأرقام المشرقية (٠-٩)",
  },
  toggleThemeLight: {
    en: "Light Mode",
    ar: "الوضع النهاري",
  },
  toggleThemeDark: {
    en: "Dark Mode",
    ar: "الوضع الليلي",
  },

  // Sidebar Footer
  sovereigntyNoticeTitle: {
    en: "Data Sovereignty Compliance",
    ar: "امتثال السيادة الرقمية",
  },
  sovereigntyNoticeText: {
    en: "All processing strictly within UAE borders (Azure UAE North / In-Cluster). Fully compliant with Federal Decree-Law No. 45/2021.",
    ar: "جميع عمليات المعالجة والتخزين تجري بالكامل داخل دولة الإمارات طبقا للمرسوم بقانون اتحادي رقم 45 لسنة 2021 بشأن حماية البيانات الشخصية.",
  },
} as const;
