"use client";

import React, { useState, useEffect, useRef } from "react";
import { useApp, ScreenId } from "@/context/AppContext";
import {
  Search,
  FileText,
  CheckSquare,
  Sparkles,
  FileCode2,
  History,
  Users,
  Shield,
  ArrowRight,
  X,
  UploadCloud,
  FileSpreadsheet,
  CornerDownLeft,
} from "lucide-react";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const { setCurrentScreen, documents, setSelectedDocumentId, language, setIsUploadModalOpen } = useApp();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const navCommands = [
    { id: "command", label: "Inbox & Command Center", labelAr: "صندوق الوارد ومركز العمليات", icon: FileText, screen: "command" as ScreenId, desc: "Real-time document feed and throughput metrics" },
    { id: "review", label: "Review Queue (HITL)", labelAr: "طابور المراجعة والتدقيق", icon: CheckSquare, screen: "review" as ScreenId, desc: "Human-in-the-loop field validation and visual bounding boxes" },
    { id: "ask", label: "Ask Documents (Sovereign RAG)", labelAr: "استعلام المستندات (الذكاء السيادي)", icon: Sparkles, screen: "ask" as ScreenId, desc: "Grounded conversational query across approved archives" },
    { id: "schemas", label: "Document Types & Schemas", labelAr: "أنواع المستندات والمخططات", icon: FileCode2, screen: "schemas" as ScreenId, desc: "Field extraction definitions, thresholds, and cross-checks" },
    { id: "governance", label: "Audit, Access & Retention", labelAr: "سجل التدقيق والحوكمة", icon: History, screen: "governance" as ScreenId, desc: "Immutable tamper-evident trails and sovereign retention sweepers" },
    { id: "team", label: "Team & Roles", labelAr: "فريق العمل والصلاحيات", icon: Users, screen: "team" as ScreenId, desc: "RBAC tenant members and API credential keys" },
    { id: "welcome", label: "Getting Started & Samples", labelAr: "دليل البدء والمستندات التجريبية", icon: Shield, screen: "welcome" as ScreenId, desc: "Platform onboarding and sample Emirates ID / Trade licenses" },
    { id: "landing", label: "Landing Showcase", labelAr: "صفحة العرض الرئيسية", icon: ArrowRight, screen: "landing" as ScreenId, desc: "Sovereign platform architecture overview and live metrics" },
  ];

  const filteredNav = navCommands.filter(
    (c) =>
      c.label.toLowerCase().includes(query.toLowerCase()) ||
      c.labelAr.includes(query) ||
      c.desc.toLowerCase().includes(query.toLowerCase())
  );

  const filteredDocs = documents
    .filter(
      (d) =>
        d.fileName.toLowerCase().includes(query.toLowerCase()) ||
        d.referenceNumber.toLowerCase().includes(query.toLowerCase()) ||
        d.documentType.toLowerCase().includes(query.toLowerCase()) ||
        (d.documentTypeNameEn || "").toLowerCase().includes(query.toLowerCase())
    )
    .slice(0, 5);

  // Total selectable items:
  // index 0: Quick Action (Upload)
  // index 1 .. filteredNav.length: Navigation items
  // index filteredNav.length + 1 ..: Document items
  const totalItems = 1 + filteredNav.length + filteredDocs.length;

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleSelectScreen = (screen: ScreenId) => {
    setCurrentScreen(screen);
    onClose();
  };

  const handleSelectDoc = (docId: string) => {
    setSelectedDocumentId(docId);
    setCurrentScreen("review");
    onClose();
  };

  const handleExecuteSelected = () => {
    if (selectedIndex === 0) {
      onClose();
      setIsUploadModalOpen(true);
      return;
    }

    const navIndex = selectedIndex - 1;
    if (navIndex < filteredNav.length) {
      handleSelectScreen(filteredNav[navIndex].screen);
      return;
    }

    const docIndex = navIndex - filteredNav.length;
    if (docIndex >= 0 && docIndex < filteredDocs.length) {
      handleSelectDoc(filteredDocs[docIndex].id);
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (isOpen) onClose();
      }

      if (!isOpen) return;

      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1 < totalItems ? prev + 1 : 0));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 >= 0 ? prev - 1 : totalItems - 1));
      } else if (e.key === "Enter") {
        e.preventDefault();
        handleExecuteSelected();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, selectedIndex, totalItems, filteredNav, filteredDocs]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 p-4 bg-black/60 backdrop-blur-md animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl bg-white dark:bg-zinc-900 border border-zinc-200/90 dark:border-zinc-800 rounded-2xl shadow-2xl overflow-hidden text-zinc-900 dark:text-zinc-100 flex flex-col max-h-[82vh] ring-1 ring-black/5 dark:ring-white/10"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar (Raycast / Linear style: borderless, clean focus) */}
        <div className="flex items-center gap-3.5 px-5 py-4 border-b border-zinc-200/80 dark:border-zinc-800/80 bg-zinc-50/50 dark:bg-zinc-900/50">
          <Search className="w-5 h-5 text-zinc-400 dark:text-zinc-500 shrink-0 stroke-[2.2]" />
          <input
            ref={inputRef}
            autoFocus
            type="text"
            placeholder={
              language === "ar"
                ? "ابحث عن شاشة، مستند، أو أمر سريع..."
                : "Search documents, screens, actions..."
            }
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 bg-transparent text-sm sm:text-base font-normal text-zinc-900 dark:text-zinc-50 border-0 outline-none ring-0 focus:outline-none focus:ring-0 focus:border-0 p-0 placeholder:text-zinc-400 dark:placeholder:text-zinc-500"
          />
          <div className="flex items-center gap-2 shrink-0">
            <kbd className="hidden sm:inline-flex items-center px-2 py-0.5 text-[10px] font-semibold tracking-wider text-zinc-400 dark:text-zinc-500 bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700/80 rounded-md">
              ESC
            </kbd>
            <button
              onClick={onClose}
              className="p-1 rounded-md text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition"
              aria-label="Close Command Palette"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Scrollable Results Body */}
        <div ref={listRef} className="overflow-y-auto p-2.5 divide-y divide-zinc-100 dark:divide-zinc-800/60 flex flex-col gap-1">
          {/* Section: Primary Quick Action */}
          <div className="pb-1.5">
            <button
              onClick={() => {
                onClose();
                setIsUploadModalOpen(true);
              }}
              onMouseEnter={() => setSelectedIndex(0)}
              className={`w-full flex items-center justify-between p-3 rounded-xl transition text-start group cursor-pointer ${
                selectedIndex === 0
                  ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 shadow-sm"
                  : "bg-zinc-100/70 dark:bg-zinc-800/50 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition ${
                    selectedIndex === 0
                      ? "bg-white/20 text-white dark:bg-zinc-900/10 dark:text-zinc-900"
                      : "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                  }`}
                >
                  <UploadCloud className="w-4 h-4 stroke-[2.2]" />
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="font-semibold text-xs sm:text-sm tracking-tight truncate">
                    {language === "ar" ? "تحميل مستند جديد للمعالجة" : "Upload New Document"}
                  </span>
                  <span
                    className={`text-[11px] truncate transition ${
                      selectedIndex === 0
                        ? "text-zinc-300 dark:text-zinc-600"
                        : "text-zinc-500 dark:text-zinc-400"
                    }`}
                  >
                    {language === "ar"
                      ? "معالجة فورية واستخراج البيانات بنسبة سيادية 100%"
                      : "Ingest Emirates ID, trade license, or invoice with sovereign OCR"}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <kbd
                  className={`text-[10px] px-2 py-0.5 rounded-md font-mono font-semibold border transition ${
                    selectedIndex === 0
                      ? "bg-white/20 border-white/30 text-white dark:bg-zinc-900/10 dark:border-zinc-900/20 dark:text-zinc-900"
                      : "bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-700 text-zinc-500"
                  }`}
                >
                  ⌘U
                </kbd>
                {selectedIndex === 0 && (
                  <CornerDownLeft className="w-3.5 h-3.5 opacity-80" />
                )}
              </div>
            </button>
          </div>

          {/* Section: Workspaces & Screens */}
          {filteredNav.length > 0 && (
            <div className="py-2">
              <div className="px-3 py-1.5 text-[10px] font-bold tracking-wider text-zinc-400 dark:text-zinc-500 uppercase flex items-center justify-between">
                <span>{language === "ar" ? "الشاشات ومساحات العمل" : "Workspaces & Screens"}</span>
                <span className="text-[9px] font-medium tracking-normal opacity-70">
                  {filteredNav.length} {filteredNav.length === 1 ? "screen" : "screens"}
                </span>
              </div>

              <div className="space-y-0.5 mt-0.5">
                {filteredNav.map((c, i) => {
                  const itemIndex = 1 + i;
                  const isSelected = selectedIndex === itemIndex;
                  const Icon = c.icon;

                  return (
                    <button
                      key={c.id}
                      onClick={() => handleSelectScreen(c.screen)}
                      onMouseEnter={() => setSelectedIndex(itemIndex)}
                      className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs transition text-start cursor-pointer group ${
                        isSelected
                          ? "bg-zinc-100 dark:bg-zinc-800 text-zinc-950 dark:text-zinc-50"
                          : "hover:bg-zinc-50 dark:hover:bg-zinc-800/50 text-zinc-700 dark:text-zinc-300"
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition ${
                            isSelected
                              ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 shadow-xs"
                              : "bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 group-hover:text-zinc-800 dark:group-hover:text-zinc-200"
                          }`}
                        >
                          <Icon className="w-3.5 h-3.5 stroke-[2]" />
                        </div>
                        <div className="flex flex-col min-w-0">
                          <span className="font-semibold truncate">
                            {language === "ar" ? c.labelAr : c.label}
                          </span>
                          <span className="text-[11px] text-zinc-400 dark:text-zinc-500 truncate hidden sm:inline">
                            {c.desc}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        {isSelected ? (
                          <span className="text-[10px] font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-1">
                            Jump <CornerDownLeft className="w-3 h-3" />
                          </span>
                        ) : (
                          <ArrowRight className="w-3.5 h-3.5 text-zinc-300 dark:text-zinc-600 opacity-0 group-hover:opacity-100 transition" />
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Section: Matching Documents */}
          {filteredDocs.length > 0 && (
            <div className="py-2">
              <div className="px-3 py-1.5 text-[10px] font-bold tracking-wider text-zinc-400 dark:text-zinc-500 uppercase flex items-center justify-between">
                <span>{language === "ar" ? "المستندات المتطابقة" : "Matching Documents"}</span>
                <span className="text-[9px] font-medium tracking-normal opacity-70">
                  {filteredDocs.length} {filteredDocs.length === 1 ? "document" : "documents"}
                </span>
              </div>

              <div className="space-y-0.5 mt-0.5">
                {filteredDocs.map((d, i) => {
                  const itemIndex = 1 + filteredNav.length + i;
                  const isSelected = selectedIndex === itemIndex;
                  const confPct = Math.round((d.overallConfidence || 0) * 100);

                  return (
                    <button
                      key={d.id}
                      onClick={() => handleSelectDoc(d.id)}
                      onMouseEnter={() => setSelectedIndex(itemIndex)}
                      className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs transition text-start cursor-pointer group ${
                        isSelected
                          ? "bg-zinc-100 dark:bg-zinc-800 text-zinc-950 dark:text-zinc-50"
                          : "hover:bg-zinc-50 dark:hover:bg-zinc-800/50 text-zinc-700 dark:text-zinc-300"
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition ${
                            isSelected
                              ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 shadow-xs"
                              : "bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400"
                          }`}
                        >
                          <FileSpreadsheet className="w-3.5 h-3.5 stroke-[2]" />
                        </div>
                        <div className="flex flex-col min-w-0">
                          <span className="font-semibold truncate">{d.fileName}</span>
                          <span className="text-[11px] text-zinc-400 dark:text-zinc-500 font-medium truncate">
                            {d.referenceNumber} · {d.documentTypeNameEn || d.documentType}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2.5 shrink-0">
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-tight uppercase ${
                            d.status === "approved"
                              ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                              : d.status === "needs_review"
                              ? "bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30"
                              : "bg-zinc-200/80 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
                          }`}
                        >
                          {d.status.replace("_", " ")}
                        </span>
                        <span className="font-mono text-[11px] font-bold text-zinc-500 dark:text-zinc-400 bg-white dark:bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-200 dark:border-zinc-800">
                          {confPct}%
                        </span>
                        {isSelected && (
                          <CornerDownLeft className="w-3.5 h-3.5 text-zinc-500 opacity-80" />
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {filteredNav.length === 0 && filteredDocs.length === 0 && (
            <div className="py-12 text-center text-zinc-400 flex flex-col items-center gap-2">
              <Search className="w-8 h-8 text-zinc-300 dark:text-zinc-700" />
              <span className="text-xs font-medium">
                {language === "ar" ? "لا توجد نتائج مطابقة" : "No matching actions or documents found."}
              </span>
            </div>
          )}
        </div>

        {/* High-end Command Dock Footer */}
        <div className="px-5 py-3 bg-zinc-50 dark:bg-zinc-950/80 border-t border-zinc-200/80 dark:border-zinc-800/80 flex items-center justify-between text-[11px] text-zinc-500 dark:text-zinc-400">
          <div className="flex items-center gap-4">
            <span className="inline-flex items-center gap-1.5">
              <kbd className="px-1.5 py-0.5 rounded bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 font-mono text-[9px] shadow-2xs">
                ↑
              </kbd>
              <kbd className="px-1.5 py-0.5 rounded bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 font-mono text-[9px] shadow-2xs">
                ↓
              </kbd>
              <span>navigate</span>
            </span>
            <span className="inline-flex items-center gap-1.5">
              <kbd className="px-1.5 py-0.5 rounded bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 font-mono text-[9px] shadow-2xs">
                ↵
              </kbd>
              <span>select</span>
            </span>
            <span className="hidden sm:inline-flex items-center gap-1.5">
              <kbd className="px-1.5 py-0.5 rounded bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 font-mono text-[9px] shadow-2xs">
                esc
              </kbd>
              <span>close</span>
            </span>
          </div>

          <div className="flex items-center gap-1.5 font-medium text-zinc-400 dark:text-zinc-500">
            <Shield className="w-3.5 h-3.5" />
            <span>UAE Sovereign Gateway</span>
          </div>
        </div>
      </div>
    </div>
  );
}
