"use client";

import React from "react";
import { useApp } from "@/context/AppContext";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import {
  Menu,
  Moon,
  Sun,
  Search,
  Bell,
  Sparkles,
} from "lucide-react";

interface HeaderProps {
  onOpenLoginModal?: () => void;
}

export function Header({ onOpenLoginModal }: HeaderProps) {
  const {
    t,
    theme,
    toggleTheme,
    toggleSidebar,
    currentScreen,
    language,
    showToast,
  } = useApp();

  const screenTitles: Record<string, { en: string; ar: string }> = {
    dashboard: { en: "Dashboard", ar: "لوحة التحكم" },
    upload: { en: "Upload Ingestion", ar: "تحميل المستندات" },
    documents: { en: "Document Management", ar: "مركز إدارة المستندات" },
    review: { en: "Review Queue", ar: "طابور المراجعة" },
    builder: { en: "Schema Engine", ar: "منشئ المخططات" },
    audit: { en: "Audit Trail", ar: "سجل التدقيق" },
    settings: { en: "Sovereignty & Settings", ar: "الإعدادات والسيادة" },
  };

  const activeTitle = screenTitles[currentScreen] || { en: "Platform", ar: "المنصة" };

  return (
    <header className="sticky top-0 z-40 w-full h-14 border-b border-border/80 bg-background/80 backdrop-blur-md">
      <div className="flex h-full items-center px-4 sm:px-6 justify-between gap-3">
        {/* Left Section: Toggle & Breadcrumbs */}
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={toggleSidebar}
            className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/80 border border-transparent hover:border-border transition"
            aria-label="Toggle navigation"
            title={language === "ar" ? "فتح/إغلاق القائمة الجانبية" : "Open/Close Sidebar"}
          >
            <Menu className="w-4 h-4" />
          </button>

          {/* Breadcrumb Hierarchy */}
          <div className="hidden sm:flex items-center gap-1.5 text-xs">
            <span className="font-semibold text-foreground/80">Sanad DocIntel</span>
            <span className="text-muted-foreground/60">/</span>
            <span className="font-semibold text-foreground">
              {language === "ar" ? activeTitle.ar : activeTitle.en}
            </span>
          </div>
        </div>

        {/* Center: Minimalist Search */}
        <div className="flex-1 max-w-sm mx-auto hidden md:block">
          <div className="relative">
            <Search className="absolute start-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <input
              type="text"
              placeholder={language === "ar" ? "بحث سريع في المستندات..." : "Search documents, schemas, audits..."}
              className="w-full ps-8 pe-12 py-1.5 text-xs bg-secondary/50 hover:bg-secondary/80 focus:bg-background border border-border/70 rounded-lg text-foreground placeholder:text-muted-foreground/70 focus:outline-none focus:ring-1 focus:ring-primary transition-all font-medium"
            />
            <kbd className="absolute end-2 top-1/2 -translate-y-1/2 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground bg-secondary border border-border rounded">
              ⌘K
            </kbd>
          </div>
        </div>

        {/* Right Section Controls */}
        <div className="flex items-center gap-2">
          {/* Sovereign AI Assistant Trigger Button */}
          <button
            onClick={() => window.dispatchEvent(new CustomEvent("open-sovereign-chatbot"))}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-border/80 bg-secondary/60 hover:bg-secondary text-foreground text-xs font-semibold shadow-xs transition active:scale-[0.98]"
            title="Open Sovereign RAG Assistant (⌘J)"
          >
            <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
            <span className="hidden sm:inline">
              {language === "ar" ? "المساعد السيادي" : "AI Assistant"}
            </span>
            <kbd className="hidden lg:inline-block px-1 py-0.2 text-[9px] font-mono text-muted-foreground bg-background rounded border border-border">
              ⌘J
            </kbd>
          </button>

          {/* Sovereign Region Badge */}
          <div className="hidden xl:flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span>Zero Egress</span>
          </div>

          <div className="h-4 w-px bg-border/80 hidden sm:block mx-1" />

          {/* Bilingual Switcher */}
          <LanguageSwitcher />

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/80 border border-transparent hover:border-border transition"
            title={theme === "light" ? t("toggleThemeDark") : t("toggleThemeLight")}
          >
            {theme === "light" ? (
              <Moon className="w-4 h-4 text-zinc-700" />
            ) : (
              <Sun className="w-4 h-4 text-amber-400" />
            )}
          </button>

          {/* Notifications */}
          <button
            onClick={() =>
              showToast(
                "info",
                "Compliance Notification: 12 high-priority KYC documents awaiting approval.",
                "إشعار رقابي: ١٢ مستند هوية ذو أولوية عالية بانتظار الاعتماد."
              )
            }
            className="relative p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/80 border border-transparent hover:border-border transition"
            title={t("notifications")}
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1 end-1 w-1.5 h-1.5 rounded-full bg-primary" />
          </button>

          {/* User Profile Avatar */}
          <button
            onClick={onOpenLoginModal}
            className="flex items-center gap-2 ps-1.5 border-s border-border/80 hover:opacity-85 transition text-start"
            title="Click to switch user or view Sovereign SSO gateway"
          >
            <div className="w-7 h-7 rounded-full bg-slate-200 dark:bg-zinc-800 text-slate-800 dark:text-zinc-200 flex items-center justify-center font-bold text-xs select-none shadow-xs">
              AJ
            </div>
            <div className="hidden lg:block text-start leading-tight">
              <div className="text-xs font-semibold text-foreground">
                Ajim Sha
              </div>
              <div className="text-[10px] text-muted-foreground">
                Administrator
              </div>
            </div>
          </button>
        </div>
      </div>
    </header>
  );
}
