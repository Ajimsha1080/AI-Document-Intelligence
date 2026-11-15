"use client";

import React from "react";
import { useApp, ScreenId } from "@/context/AppContext";
import { TranslationKey } from "@/lib/translations";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  FileText,
  History,
  Users,
  CheckSquare,
  FileCode2,
  Settings,
  ShieldCheck,
  PanelLeftClose,
  PanelLeftOpen,
  LogOut,
} from "lucide-react";

export function Sidebar() {
  const {
    t,
    currentScreen,
    setCurrentScreen,
    sidebarCollapsed,
    toggleSidebar,
  } = useApp();

  const mainNavItems: {
    id: ScreenId;
    labelKey: TranslationKey;
    icon: React.ElementType;
    badge?: string;
  }[] = [
    { id: "dashboard", labelKey: "navDashboard", icon: LayoutDashboard },
    { id: "documents", labelKey: "navDocuments", icon: FileText },
    { id: "audit", labelKey: "navAudit", icon: History },
    { id: "team", labelKey: "navTeam", icon: Users },
  ];

  const secondaryNavItems: {
    id: ScreenId;
    labelKey: TranslationKey;
    icon: React.ElementType;
    badge?: string;
  }[] = [
    { id: "review", labelKey: "navReview", icon: CheckSquare, badge: "12" },
    { id: "builder", labelKey: "navBuilder", icon: FileCode2 },
    { id: "settings", labelKey: "navSettings", icon: Settings },
  ];

  return (
    <aside
      className={cn(
        "fixed inset-y-0 start-0 z-50 flex flex-col bg-card border-e border-border/80 transition-all duration-200 lg:static select-none",
        sidebarCollapsed ? "-translate-x-full lg:translate-x-0 lg:w-[72px]" : "translate-x-0 w-64"
      )}
    >
      {/* Brand Header matching reference image */}
      <div className="h-16 px-4 border-b border-border/80 flex items-center justify-between gap-2">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 shrink-0 rounded-xl bg-[#064e3b] text-white flex items-center justify-center shadow-xs">
            <ShieldCheck className="w-4 h-4 text-emerald-300" />
          </div>
          <div className={cn("min-w-0 overflow-hidden transition-all", sidebarCollapsed && "lg:hidden")}>
            <div className="font-bold text-sm text-foreground leading-tight tracking-tight">
              Document Intelligence
            </div>
            <div className="text-[10px] tracking-wider text-muted-foreground uppercase font-semibold">
              UAE SOVEREIGN
            </div>
          </div>
        </div>

        {/* Sidebar Close / Open Toggle Button */}
        <button
          onClick={toggleSidebar}
          className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/80 border border-transparent hover:border-border transition"
          title={sidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          aria-label="Toggle Sidebar"
        >
          {sidebarCollapsed ? (
            <PanelLeftOpen className="w-4 h-4 text-emerald-600" />
          ) : (
            <PanelLeftClose className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Primary Navigation List matching reference image */}
      <div className="flex-1 py-4 px-3 space-y-1.5 overflow-y-auto">
        {mainNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentScreen === item.id;

          return (
            <button
              key={item.id}
              onClick={() => setCurrentScreen(item.id)}
              className={cn(
                "w-full flex items-center gap-3 px-3.5 py-2.5 text-xs transition-all text-start group",
                isActive
                  ? "rounded-2xl border border-emerald-600/40 bg-emerald-50/40 dark:bg-emerald-950/20 text-foreground font-semibold shadow-xs"
                  : "rounded-xl text-muted-foreground hover:text-foreground hover:bg-secondary/60 font-medium"
              )}
              title={t(item.labelKey)}
            >
              <Icon
                className={cn(
                  "w-4 h-4 shrink-0 transition-colors",
                  isActive ? "text-emerald-700 dark:text-emerald-400" : "text-muted-foreground group-hover:text-foreground"
                )}
              />
              <span className={cn("flex-1 truncate", sidebarCollapsed && "lg:hidden")}>
                {t(item.labelKey)}
              </span>

              {item.badge && (
                <span
                  className={cn(
                    "px-2 py-0.5 text-[10px] font-bold rounded-full font-mono",
                    sidebarCollapsed && "lg:hidden",
                    isActive
                      ? "bg-emerald-700 text-white"
                      : "bg-secondary text-muted-foreground border border-border"
                  )}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}

        {/* Subtle Separator for Additional Sovereign Tools */}
        <div className={cn("pt-3 pb-1 px-3 text-[10px] font-semibold tracking-wider text-muted-foreground/50 uppercase", sidebarCollapsed && "lg:hidden")}>
          Workspace Tools
        </div>

        {secondaryNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentScreen === item.id;

          return (
            <button
              key={item.id}
              onClick={() => setCurrentScreen(item.id)}
              className={cn(
                "w-full flex items-center gap-3 px-3.5 py-2 text-xs transition-all text-start group",
                isActive
                  ? "rounded-2xl border border-emerald-600/40 bg-emerald-50/40 dark:bg-emerald-950/20 text-foreground font-semibold shadow-xs"
                  : "rounded-xl text-muted-foreground hover:text-foreground hover:bg-secondary/60 font-medium"
              )}
              title={t(item.labelKey)}
            >
              <Icon
                className={cn(
                  "w-4 h-4 shrink-0 transition-colors",
                  isActive ? "text-emerald-700 dark:text-emerald-400" : "text-muted-foreground group-hover:text-foreground"
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

      {/* User Profile Footer matching reference image (Ajim Sha - Administrator) */}
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

        <button
          onClick={() => setCurrentScreen("settings")}
          className={cn(
            "p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition",
            sidebarCollapsed && "lg:hidden"
          )}
          title="Sign out / Settings"
          aria-label="Account Settings"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </aside>
  );
}
