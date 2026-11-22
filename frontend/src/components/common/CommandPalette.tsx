"use client";

import React, { useState, useEffect } from "react";
import { useApp, ScreenId } from "@/context/AppContext";
import { Search, FileText, CheckSquare, Sparkles, FileCode2, History, Users, Shield, ArrowRight, X } from "lucide-react";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const { setCurrentScreen, documents, setSelectedDocumentId, language, setIsUploadModalOpen } = useApp();
  const [query, setQuery] = useState("");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (isOpen) onClose();
        else {
          // Open handled by caller or state
        }
      }
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const navCommands = [
    { id: "command", label: "Inbox & Command Center", labelAr: "صندوق الوارد ومركز العمليات", icon: FileText, screen: "command" as ScreenId },
    { id: "review", label: "Review Queue", labelAr: "طابور المراجعة والتدقيق", icon: CheckSquare, screen: "review" as ScreenId },
    { id: "ask", label: "Ask Documents (Sovereign RAG)", labelAr: "استعلام المستندات (الذكاء السيادي)", icon: Sparkles, screen: "ask" as ScreenId },
    { id: "schemas", label: "Document Types & Schemas", labelAr: "أنواع المستندات والمخططات", icon: FileCode2, screen: "schemas" as ScreenId },
    { id: "governance", label: "Audit, Access & Retention", labelAr: "سجل التدقيق والحوكمة", icon: History, screen: "governance" as ScreenId },
    { id: "team", label: "Team & Roles", labelAr: "فريق العمل والصلاحيات", icon: Users, screen: "team" as ScreenId },
    { id: "welcome", label: "Getting Started & Samples", labelAr: "دليل البدء والمستندات التجريبية", icon: Shield, screen: "welcome" as ScreenId },
    { id: "landing", label: "Landing Page Showcase", labelAr: "صفحة العرض الرئيسية", icon: ArrowRight, screen: "landing" as ScreenId },
  ];

  const filteredNav = navCommands.filter(
    (c) =>
      c.label.toLowerCase().includes(query.toLowerCase()) ||
      c.labelAr.includes(query)
  );

  const filteredDocs = documents
    .filter(
      (d) =>
        d.fileName.toLowerCase().includes(query.toLowerCase()) ||
        d.referenceNumber.toLowerCase().includes(query.toLowerCase()) ||
        d.documentType.toLowerCase().includes(query.toLowerCase())
    )
    .slice(0, 5);

  const handleSelectScreen = (screen: ScreenId) => {
    setCurrentScreen(screen);
    onClose();
  };

  const handleSelectDoc = (docId: string) => {
    setSelectedDocumentId(docId);
    setCurrentScreen("review");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-150">
      <div
        className="w-full max-w-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-2xl overflow-hidden text-zinc-900 dark:text-zinc-100 flex flex-col max-h-[80vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
          <Search className="w-5 h-5 text-zinc-400 shrink-0" />
          <input
            autoFocus
            type="text"
            placeholder={language === "ar" ? "ابحث عن شاشة، مستند، أو أمر سريع... (Esc للإغلاق)" : "Search documents, screens, actions... (Esc to close)"}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 bg-transparent text-sm font-medium outline-hidden placeholder:text-zinc-400"
          />
          <button
            onClick={onClose}
            className="p-1 rounded-md text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="overflow-y-auto p-2 divide-y divide-zinc-100 dark:divide-zinc-800/60">
          {/* Quick Actions */}
          <div className="py-1">
            <button
              onClick={() => {
                onClose();
                setIsUploadModalOpen(true);
              }}
              className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold text-emerald-800 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 hover:bg-emerald-100 dark:hover:bg-emerald-900/40 transition text-start"
            >
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                {language === "ar" ? "+ تحميل مستند جديد الآن" : "+ Upload New Document Now"}
              </span>
              <kbd className="font-mono text-[10px] bg-white dark:bg-zinc-900 px-1.5 py-0.5 rounded border border-emerald-200 dark:border-emerald-800">U</kbd>
            </button>
          </div>

          {/* Navigation Screens */}
          {filteredNav.length > 0 && (
            <div className="py-1.5">
              <div className="px-3 py-1 text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
                {language === "ar" ? "الشاشات ومهام العمل" : "Workspaces & Screens"}
              </div>
              {filteredNav.map((c) => {
                const Icon = c.icon;
                return (
                  <button
                    key={c.id}
                    onClick={() => handleSelectScreen(c.screen)}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium hover:bg-zinc-100 dark:hover:bg-zinc-800/80 transition text-start group"
                  >
                    <Icon className="w-4 h-4 text-zinc-400 group-hover:text-emerald-600 dark:group-hover:text-emerald-400" />
                    <span className="flex-1">{language === "ar" ? c.labelAr : c.label}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-zinc-300 dark:text-zinc-600 opacity-0 group-hover:opacity-100 transition" />
                  </button>
                );
              })}
            </div>
          )}

          {/* Matching Documents */}
          {filteredDocs.length > 0 && (
            <div className="py-1.5">
              <div className="px-3 py-1 text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
                {language === "ar" ? "المستندات المتطابقة" : "Matching Documents"}
              </div>
              {filteredDocs.map((d) => (
                <button
                  key={d.id}
                  onClick={() => handleSelectDoc(d.id)}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs hover:bg-zinc-100 dark:hover:bg-zinc-800/80 transition text-start group"
                >
                  <div className="flex flex-col min-w-0">
                    <span className="font-semibold truncate">{d.fileName}</span>
                    <span className="text-[11px] text-zinc-500 font-mono">
                      {d.referenceNumber} · {d.documentTypeNameEn}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        d.status === "approved"
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                          : d.status === "needs_review"
                          ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                          : "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
                      }`}
                    >
                      {d.status.replace("_", " ")}
                    </span>
                    <span className="font-mono text-zinc-400 text-[11px]">
                      {Math.round(d.overallConfidence * 100)}%
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 bg-zinc-50 dark:bg-zinc-950/60 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-between text-[11px] text-zinc-500">
          <span>Navigate with <strong>↑</strong> <strong>↓</strong> and <strong>↵</strong></span>
          <span className="font-mono">DocIntel UAE Sovereign</span>
        </div>
      </div>
    </div>
  );
}
