import React from "react";
import { useApp } from "@/context/AppContext";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import {
  Menu,
  Moon,
  Sun,
  ShieldCheck,
  Search,
  Bell,
  Building2,
  UserCheck,
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
    activeTenant,
    language,
    showToast,
  } = useApp();

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/75">
      <div className="flex h-16 items-center px-4 sm:px-6 gap-3">
        {/* Sidebar Toggle */}
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary focus:ring-1 focus:ring-primary lg:hidden"
          aria-label="Toggle navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Sovereign Region Badge */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600"></span>
          </span>
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-700 dark:text-emerald-400" />
          <span>{t("sovereignBadge")}</span>
        </div>

        {/* Quick Search */}
        <div className="flex-1 max-w-md ms-2 me-auto">
          <div className="relative">
            <Search className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder={t("searchPlaceholder")}
              className="w-full ps-9 pe-4 py-1.5 text-sm bg-secondary/50 border border-border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:bg-card transition-all"
            />
            <kbd className="hidden sm:inline-block absolute end-2.5 top-1/2 -translate-y-1/2 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground bg-muted border border-border rounded">
              ⌘K
            </kbd>
          </div>
        </div>

        {/* Right Section Controls */}
        <div className="flex items-center gap-2.5">
          {/* Sovereign AI Assistant Trigger */}
          <button
            onClick={() => window.dispatchEvent(new CustomEvent("open-sovereign-chatbot"))}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-emerald-600/50 bg-emerald-950/40 hover:bg-emerald-900/50 text-emerald-300 text-xs font-bold transition shadow-xs"
            title="Open Sovereign RAG Assistant"
          >
            <Sparkles className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            <span className="hidden sm:inline">
              {language === "ar" ? "المساعد السيادي" : "AI Assistant"}
            </span>
          </button>

          {/* Active Tenant / Bank */}
          <div className="hidden xl:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border bg-secondary/30 text-xs">
            <Building2 className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="font-semibold text-foreground">
              {language === "ar" ? activeTenant.nameAr : activeTenant.nameEn}
            </span>
          </div>

          {/* Bilingual Switcher */}
          <LanguageSwitcher />

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary border border-border focus:ring-1 focus:ring-primary transition-all"
            title={theme === "light" ? t("toggleThemeDark") : t("toggleThemeLight")}
          >
            {theme === "light" ? (
              <Moon className="w-4 h-4 text-slate-700" />
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
            className="relative p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary border border-border focus:ring-1 focus:ring-primary"
            title={t("notifications")}
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 end-1.5 w-2 h-2 rounded-full bg-primary ring-2 ring-card" />
          </button>

          {/* User Profile */}
          <button
            onClick={onOpenLoginModal}
            className="flex items-center gap-2.5 ps-2 border-s border-border hover:opacity-80 transition text-start"
            title="Click to switch user or view Sovereign SSO gateway"
          >
            <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary font-bold text-xs">
              AM
            </div>
            <div className="hidden lg:block text-start">
              <div className="text-xs font-bold text-foreground leading-tight flex items-center gap-1">
                <span>Ahmed Al Mansoori</span>
                <UserCheck className="w-3 h-3 text-emerald-600" />
              </div>
              <div className="text-[10px] text-muted-foreground font-medium">
                {t("roleAdmin")}
              </div>
            </div>
          </button>
        </div>
      </div>
    </header>
  );
}
