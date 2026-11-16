"use client";

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
  Users,
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

  const navSections: {
    titleEn: string;
    titleAr: string;
    items: { id: ScreenId; labelKey: TranslationKey; icon: React.ElementType; badge?: string }[];
  }[] = [
    {
      titleEn: "Overview",
      titleAr: "نظرة عامة",
      items: [
        { id: "dashboard", labelKey: "navDashboard", icon: LayoutDashboard },
        { id: "upload", labelKey: "navUpload", icon: UploadCloud },
      ],
    },
    {
      titleEn: "Intelligence & Review",
      titleAr: "المعالجة والتدقيق",
      items: [
        { id: "documents", labelKey: "navDocuments", icon: FileText },
        { id: "review", labelKey: "navReview", icon: CheckSquare, badge: "12" },
      ],
    },
    {
      titleEn: "Governance & Schemas",
      titleAr: "الحوكمة والمخططات",
      items: [
        { id: "builder", labelKey: "navBuilder", icon: FileCode2 },
        { id: "audit", labelKey: "navAudit", icon: History },
        { id: "team", labelKey: "navTeam", icon: Users },
        { id: "settings", labelKey: "navSettings", icon: Settings },
      ],
    },
  ];

  return (
    <aside
      className={cn(
        "fixed inset-y-0 start-0 z-50 flex flex-col bg-card border-e border-border/80 transition-all duration-200 lg:static select-none",
        sidebarCollapsed ? "-translate-x-full lg:translate-x-0 lg:w-[68px]" : "translate-x-0 w-64"
      )}
    >
      {/* Workspace Switcher Header */}
      <div className="h-14 px-3.5 border-b border-border/80 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 shrink-0 rounded-lg bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 flex items-center justify-center font-bold text-xs shadow-xs">
            <Layers className="w-4 h-4 text-emerald-400 dark:text-emerald-600" />
          </div>
          <div className={cn("min-w-0 overflow-hidden transition-all", sidebarCollapsed && "lg:hidden")}>
            <div className="font-semibold text-xs text-foreground truncate flex items-center gap-1.5">
              <span>{language === "ar" ? activeTenant.nameAr : activeTenant.nameEn}</span>
            </div>
            <div className="text-[10px] text-muted-foreground truncate font-mono">
              {activeTenant.tier}
            </div>
          </div>
        </div>

        {/* Sidebar Close / Open Toggle Button */}
        <button
          onClick={toggleSidebar}
          className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/80 border border-transparent hover:border-border transition"
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

      {/* Navigation Sections */}
      <div className="flex-1 py-3 px-2 space-y-4 overflow-y-auto">
        {navSections.map((sec, secIdx) => (
          <div key={secIdx} className="space-y-0.5">
            <div
              className={cn(
                "px-2.5 pb-1 text-[10px] font-semibold tracking-wider text-muted-foreground/60 uppercase",
                sidebarCollapsed && "lg:hidden"
              )}
            >
              {language === "ar" ? sec.titleAr : sec.titleEn}
            </div>

            {sec.items.map((item) => {
              const Icon = item.icon;
              const isActive = currentScreen === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => setCurrentScreen(item.id)}
                  className={cn(
                    "w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all group text-start relative",
                    isActive
                      ? "bg-secondary text-foreground font-semibold shadow-xs"
                      : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
                  )}
                  title={t(item.labelKey)}
                >
                  {/* Active Indicator Bar */}
                  {isActive && (
                    <span className="absolute start-0 top-1/2 -translate-y-1/2 w-1 h-4 bg-primary rounded-e-full" />
                  )}

                  <Icon
                    className={cn(
                      "w-4 h-4 shrink-0 transition-colors",
                      isActive
                        ? "text-primary"
                        : "text-muted-foreground group-hover:text-foreground"
                    )}
                  />
                  <span className={cn("flex-1 truncate", sidebarCollapsed && "lg:hidden")}>
                    {t(item.labelKey)}
                  </span>

                  {item.badge && (
                    <span
                      className={cn(
                        "px-1.5 py-0.2 text-[10px] font-bold rounded-md font-mono",
                        sidebarCollapsed && "lg:hidden",
                        isActive
                          ? "bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30"
                          : "bg-secondary text-muted-foreground border border-border"
                      )}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </div>

      {/* Sovereign Data Boundary Status Footer */}
      <div className={cn("p-2.5 m-2 rounded-lg bg-secondary/40 border border-border/80 text-[11px]", sidebarCollapsed && "lg:hidden")}>
        <div className="flex items-center gap-1.5 font-medium text-foreground text-xs">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-[11px] font-semibold">Zero-Egress Boundary</span>
        </div>
        <p className="text-[10px] text-muted-foreground mt-0.5 leading-snug">
          Federal Decree-Law No. 45/2021
        </p>
        <div className="mt-1.5 pt-1.5 border-t border-border/60 flex items-center justify-between text-[10px] text-muted-foreground font-mono">
          <span>{activeTenant.region.split("(")[0].trim()}</span>
          <span className="text-emerald-600 dark:text-emerald-400 font-semibold">In-Cluster</span>
        </div>
      </div>

      {/* User Profile Footer (Ajim Sha - Administrator) */}
      <div className="p-3 border-t border-border/80 flex items-center justify-between gap-2.5">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 shrink-0 rounded-full bg-slate-200 dark:bg-zinc-800 text-slate-800 dark:text-zinc-200 flex items-center justify-center font-bold text-xs select-none shadow-xs">
            AJ
          </div>
          <div className={cn("min-w-0 overflow-hidden leading-tight", sidebarCollapsed && "lg:hidden")}>
            <div className="font-semibold text-xs text-foreground truncate">
              Ajim Sha
            </div>
            <div className="text-[11px] text-muted-foreground truncate">
              Administrator
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
