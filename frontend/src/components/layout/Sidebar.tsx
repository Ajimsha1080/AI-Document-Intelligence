"use client";

import React from "react";
import { useApp, ScreenId } from "@/context/AppContext";
import {
  Inbox,
  CheckSquare,
  Sparkles,
  FileCode2,
  Shield,
  Users,
  Compass,
  ArrowUpRight,
  ShieldCheck,
} from "lucide-react";

export function Sidebar() {
  const {
    currentScreen,
    setCurrentScreen,
    documents,
    activeTenant,
    language,
  } = useApp();

  const totalCount = documents.length;
  const needsReviewCount = documents.filter((d) => d.status === "needs_review").length;

  const navLinks = [
    {
      id: "command" as ScreenId,
      label: "Inbox",
      labelAr: "صندوق الوارد",
      icon: Inbox,
      badge: totalCount > 0 ? totalCount : undefined,
    },
    {
      id: "review" as ScreenId,
      label: "My review queue",
      labelAr: "طابور المراجعة",
      icon: CheckSquare,
      badge: needsReviewCount > 0 ? needsReviewCount : undefined,
      badgeAmber: true,
    },
    {
      id: "ask" as ScreenId,
      label: "Ask documents",
      labelAr: "الاستعلام السيادي",
      icon: Sparkles,
    },
    {
      id: "schemas" as ScreenId,
      label: "Document types",
      labelAr: "أنواع المستندات",
      icon: FileCode2,
    },
    {
      id: "governance" as ScreenId,
      label: "Audit & access",
      labelAr: "التدقيق والحوكمة",
      icon: Shield,
    },
    {
      id: "team" as ScreenId,
      label: "Team",
      labelAr: "فريق العمل",
      icon: Users,
    },
    {
      id: "welcome" as ScreenId,
      label: "Getting started",
      labelAr: "دليل البدء",
      icon: Compass,
    },
  ];

  const isCurrent = (id: ScreenId) => {
    if (id === "command" && (currentScreen === "command" || currentScreen === "dashboard" || currentScreen === "documents")) return true;
    if (id === "schemas" && (currentScreen === "schemas" || currentScreen === "builder")) return true;
    if (id === "governance" && (currentScreen === "governance" || currentScreen === "audit" || currentScreen === "settings")) return true;
    return currentScreen === id;
  };

  return (
    <aside className="w-56 shrink-0 bg-white dark:bg-zinc-900 border-r border-zinc-200 dark:border-zinc-800 flex flex-col py-4 px-3 select-none h-full">
      {/* Navigation Links */}
      <nav aria-label="Main" className="flex-1 flex flex-col gap-1">
        <span className="px-2 pb-1 text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
          Workspace
        </span>

        {navLinks.map((item) => {
          const Icon = item.icon;
          const active = isCurrent(item.id);

          return (
            <button
              key={item.id}
              onClick={() => setCurrentScreen(item.id)}
              className={`w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-xs font-semibold transition text-start ${
                active
                  ? "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50 shadow-xs"
                  : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800/60"
              }`}
            >
              <div className="flex items-center gap-2.5 truncate">
                <Icon
                  className={`w-4 h-4 shrink-0 ${
                    active ? "text-emerald-600 dark:text-emerald-400" : "text-zinc-400"
                  }`}
                />
                <span className="truncate">{language === "ar" ? item.labelAr : item.label}</span>
              </div>

              {item.badge !== undefined && (
                <span
                  className={`text-[10px] font-bold px-1.5 py-0.2 rounded-full ${
                    item.badgeAmber
                      ? "text-amber-800 bg-amber-100 dark:bg-amber-950 dark:text-amber-300"
                      : "text-zinc-500 bg-zinc-200 dark:bg-zinc-800"
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}

        {/* Saved Views (Matching v2/Command.dc.html) */}
        <div className="pt-4 flex flex-col gap-1">
          <span className="px-2 pb-1 text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
            Saved Views
          </span>
          <button
            onClick={() => setCurrentScreen("command")}
            className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-800/60 transition text-start"
          >
            <span>Expiring IDs</span>
            <span className="text-[10px] text-zinc-400 font-semibold">12</span>
          </button>
          <button
            onClick={() => setCurrentScreen("command")}
            className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-800/60 transition text-start"
          >
            <span>Invoices &gt; AED 100k</span>
            <span className="text-[10px] text-zinc-400 font-semibold">4</span>
          </button>
        </div>

        {/* Public Landing Page Showcase */}
        <div className="pt-3">
          <button
            onClick={() => setCurrentScreen("landing")}
            className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition text-start ${
              currentScreen === "landing"
                ? "bg-emerald-50 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 font-bold"
                : "text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-800/60"
            }`}
          >
            <span className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <span>Landing Page</span>
            </span>
            <ArrowUpRight className="w-3.5 h-3.5 text-zinc-400" />
          </button>
        </div>
      </nav>

      {/* Sovereign Air-Gap Status Box at bottom (Matching v2/Landing.dc.html) */}
      <div className="p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800 text-xs flex flex-col gap-1.5">
        <div className="flex items-center gap-1.5 font-bold text-zinc-900 dark:text-zinc-100 text-[11px]">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
          <span>Sovereign Boundary</span>
        </div>
        <p className="text-[10px] text-zinc-500 leading-snug">
          100% In-Country UAE Data Boundary (Federal Decree-Law 45/2021)
        </p>
        <div className="pt-1 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-between text-[10px] text-zinc-400 font-medium">
          <span>{activeTenant.tier.split(" ")[0]}</span>
          <span className="text-emerald-600 dark:text-emerald-400 font-bold">In-Region</span>
        </div>
      </div>
    </aside>
  );
}
