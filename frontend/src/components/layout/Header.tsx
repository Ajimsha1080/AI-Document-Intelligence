"use client";

import React from "react";
import { useApp } from "@/context/AppContext";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import { Search, Plus, Sparkles } from "lucide-react";

interface HeaderProps {
  onOpenLoginModal?: () => void;
}

export function Header({ onOpenLoginModal }: HeaderProps) {
  const {
    setCurrentScreen,
    language,
    currentUser,
    userRole,
    activeTenant,
    setIsUploadModalOpen,
    setIsCommandPaletteOpen,
  } = useApp();

  return (
    <header className="sticky top-0 z-30 w-full h-14 bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 px-4 sm:px-6 flex items-center justify-between gap-3 select-none">
      {/* Brand & Breadcrumb Hierarchy (Matching v2/Command.dc.html) */}
      <div className="flex items-center gap-2.5 min-w-0">
        <button
          type="button"
          onClick={() => setCurrentScreen("command")}
          className="flex items-center gap-2 text-zinc-900 dark:text-zinc-50 font-bold text-base tracking-tight hover:opacity-85 transition"
        >
          <span
            aria-hidden="true"
            className="w-7 h-7 rounded-lg bg-zinc-950 text-emerald-400 dark:bg-zinc-100 dark:text-emerald-700 flex items-center justify-center font-extrabold text-sm shadow-xs"
          >
            D
          </span>
          <span className="font-extrabold">DocIntel</span>
        </button>

        <span className="text-zinc-300 dark:text-zinc-700 font-normal">/</span>

        <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 truncate max-w-[140px] sm:max-w-none">
          {language === "ar" ? activeTenant.nameAr : activeTenant.nameEn}
        </span>

        {/* UAE Sovereign Region Pill */}
        <span className="hidden md:inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          UAE North
        </span>
      </div>

      {/* Center: Command Palette Trigger */}
      <div className="flex-1 max-w-md mx-auto hidden md:block">
        <button
          type="button"
          onClick={() => setIsCommandPaletteOpen(true)}
          className="w-full h-9 px-3 bg-zinc-50 dark:bg-zinc-800/60 hover:bg-zinc-100 dark:hover:bg-zinc-800 border border-zinc-200 dark:border-zinc-700/80 rounded-lg text-xs text-zinc-400 flex items-center justify-between transition"
        >
          <span className="flex items-center gap-2">
            <Search className="w-3.5 h-3.5 text-zinc-400" />
            <span>Search documents, fields, people…</span>
          </span>
          <kbd className="font-mono text-[10px] text-zinc-500 bg-white dark:bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-200 dark:border-zinc-700">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2">
        {/* Quick Upload Button */}
        {userRole !== "viewer" && (
          <button
            type="button"
            onClick={() => setIsUploadModalOpen(true)}
            className="h-8 px-3 rounded-lg bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 text-xs font-semibold hover:opacity-90 transition flex items-center gap-1.5 shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Upload</span>
          </button>
        )}

        {/* Ask AI Shortcut */}
        <button
          type="button"
          onClick={() => setCurrentScreen("ask")}
          className="h-8 px-2.5 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs font-medium text-zinc-700 dark:text-zinc-300 transition flex items-center gap-1.5"
          title="Ask Sovereign AI"
        >
          <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
          <span className="hidden lg:inline">Ask AI</span>
        </button>

        {/* Bilingual Switcher */}
        <LanguageSwitcher />

        {/* User Profile Avatar (Matching v2/Command.dc.html) */}
        <button
          type="button"
          onClick={onOpenLoginModal}
          className="flex items-center gap-2 pl-1.5 hover:opacity-85 transition text-start"
          title="Click to view profile or sign out"
        >
          <div className="w-8 h-8 rounded-full bg-emerald-50 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center font-bold text-xs">
            {(currentUser?.name || "AD").slice(0, 2).toUpperCase()}
          </div>
        </button>
      </div>
    </header>
  );
}
