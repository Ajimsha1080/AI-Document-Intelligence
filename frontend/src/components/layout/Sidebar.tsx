import React from "react";
import { useApp, ScreenId } from "@/context/AppContext";
import { TranslationKey } from "@/lib/translations";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  UploadCloud,
  FileText,
  CheckSquare,
  FileCode2,
  History,
  Settings,
  Shield,
  Layers,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";

export function Sidebar() {
  const {
    t,
    currentScreen,
    setCurrentScreen,
    sidebarCollapsed,
    toggleSidebar,
    language,
    activeTenant,
  } = useApp();

  const navItems: { id: ScreenId; labelKey: TranslationKey; icon: React.ElementType; badge?: string }[] = [
    {
      id: "dashboard",
      labelKey: "navDashboard",
      icon: LayoutDashboard,
    },
    {
      id: "upload",
      labelKey: "navUpload",
      icon: UploadCloud,
    },
    {
      id: "documents",
      labelKey: "navDocuments",
      icon: FileText,
    },
    {
      id: "review",
      labelKey: "navReview",
      icon: CheckSquare,
      badge: "12",
    },
    {
      id: "builder",
      labelKey: "navBuilder",
      icon: FileCode2,
    },
    {
      id: "audit",
      labelKey: "navAudit",
      icon: History,
    },
    {
      id: "settings",
      labelKey: "navSettings",
      icon: Settings,
    },
  ];

  return (
    <aside
      className={cn(
        "fixed inset-y-0 start-0 z-50 flex flex-col w-64 bg-card border-e border-border transition-all duration-200 lg:static",
        sidebarCollapsed ? "-translate-x-full lg:translate-x-0 lg:w-20" : "translate-x-0"
      )}
    >
      {/* Brand Header */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-border">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 shrink-0 rounded-xl bg-gradient-to-br from-emerald-800 to-emerald-950 flex items-center justify-center text-white shadow-md shadow-emerald-900/20">
            <Layers className="w-5 h-5 text-gold-light" />
          </div>
          <div className={cn("overflow-hidden transition-all", sidebarCollapsed && "lg:hidden")}>
            <div className="font-extrabold text-sm tracking-tight text-foreground flex items-center gap-1.5">
              <span>{t("appName")}</span>
              <span className="px-1.5 py-0.2 text-[9px] font-bold rounded bg-primary/10 text-primary border border-primary/20">
                UAE
              </span>
            </div>
            <div className="text-[10px] text-muted-foreground truncate font-medium">
              {t("appTagline")}
            </div>
          </div>
        </div>

        {/* Sidebar Close / Open Toggle Button */}
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary border border-border/60 transition"
          title={
            sidebarCollapsed
              ? language === "ar"
                ? "توسيع القائمة"
                : "Expand Sidebar"
              : language === "ar"
              ? "طي القائمة"
              : "Collapse Sidebar"
          }
          aria-label="Toggle Sidebar"
        >
          {sidebarCollapsed ? (
            <PanelLeftOpen className="w-4 h-4 text-primary" />
          ) : (
            <PanelLeftClose className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Navigation List */}
      <div className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        <div className={cn("px-3 pb-2 text-[11px] font-bold tracking-wider text-muted-foreground/70 uppercase", sidebarCollapsed && "lg:hidden")}>
          {language === "ar" ? "قائمة المنصة" : "Platform Navigation"}
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentScreen === item.id;

          return (
            <button
              key={item.id}
              onClick={() => setCurrentScreen(item.id)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold transition-all group text-start",
                isActive
                  ? "bg-primary text-primary-foreground shadow-sm shadow-emerald-900/20"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/70"
              )}
              title={t(item.labelKey)}
            >
              <Icon
                className={cn(
                  "w-4 h-4 shrink-0 transition-colors",
                  isActive
                    ? "text-primary-foreground"
                    : "text-muted-foreground group-hover:text-foreground"
                )}
              />
              <span className={cn("flex-1 truncate", sidebarCollapsed && "lg:hidden")}>
                {t(item.labelKey)}
              </span>

              {item.badge && (
                <span
                  className={cn(
                    "px-2 py-0.5 text-[10px] font-bold rounded-full",
                    sidebarCollapsed && "lg:hidden",
                    isActive
                      ? "bg-primary-foreground/20 text-primary-foreground"
                      : "bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-300 dark:border-amber-800"
                  )}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Sovereign Data Boundary Notice Footer */}
      <div className={cn("p-3 m-3 rounded-xl bg-secondary/50 border border-border text-[11px]", sidebarCollapsed && "lg:hidden")}>
        <div className="flex items-center gap-1.5 font-bold text-foreground mb-1">
          <Shield className="w-3.5 h-3.5 text-primary" />
          <span>{t("sovereigntyNoticeTitle")}</span>
        </div>
        <p className="text-[10px] text-muted-foreground leading-relaxed line-clamp-3">
          {t("sovereigntyNoticeText")}
        </p>
        <div className="mt-2 pt-2 border-t border-border/60 flex items-center justify-between text-[10px] font-mono text-muted-foreground">
          <span>{activeTenant.tier}</span>
          <span className="text-emerald-700 dark:text-emerald-400 font-bold">● Active</span>
        </div>
      </div>
    </aside>
  );
}
