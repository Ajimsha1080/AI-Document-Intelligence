"use client";

import React from "react";
import { useApp } from "@/context/AppContext";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import { Search, Plus, Sparkles, Menu } from "lucide-react";

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
    setIsMobileMenuOpen,
  } = useApp();

  return (
    <header className="sticky top-0 z-30 w-full h-16 bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 px-4 sm:px-8 flex items-center justify-between gap-3 select-none">
      {/* Brand & Organization Title & Mobile Hamburger */}
      <div className="flex items-center gap-2.5 min-w-0">
        <button
          type="button"
          onClick={() => setIsMobileMenuOpen(true)}
          className="md:hidden p-1.5 -ml-1 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition shrink-0"
          aria-label="Open Navigation Menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <button
          type="button"
          onClick={() => setCurrentScreen("command")}
          className="text-sm sm:text-base font-bold text-zinc-900 dark:text-zinc-50 hover:opacity-85 transition truncate max-w-[150px] xs:max-w-[200px] sm:max-w-none"
        >
          {language === "ar" ? activeTenant.nameAr : activeTenant.nameEn}
        </button>

        {/* UAE Sovereign Region Pill */}
        <span className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold text-zinc-800 dark:text-zinc-200 bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 shrink-0 whitespace-nowrap">
          <span className="w-1.5 h-1.5 rounded-full bg-zinc-950 dark:bg-zinc-100" />
          UAE North
        </span>
      </div>

      {/* Center: Command Palette Trigger (Desktop) */}
      <div className="flex-1 max-w-md lg:max-w-lg mx-auto hidden md:block min-w-0 px-2">
        <button
          type="button"
          onClick={() => setIsCommandPaletteOpen(true)}
          className="w-full h-10 px-3.5 bg-zinc-50 dark:bg-zinc-800/60 hover:bg-zinc-100 dark:hover:bg-zinc-800 border border-zinc-200 dark:border-zinc-700/80 rounded-xl text-xs sm:text-sm text-zinc-400 flex items-center justify-between gap-2 transition shadow-2xs overflow-hidden"
        >
          <span className="flex items-center gap-2.5 min-w-0 flex-1 overflow-hidden">
            <Search className="w-4 h-4 text-zinc-400 shrink-0" />
            <span className="truncate whitespace-nowrap text-start">
              {language === "ar" ? "ابحث في المستندات والحقول والأشخاص..." : "Search documents, fields, people…"}
            </span>
          </span>
          <kbd className="shrink-0 text-[11px] text-zinc-500 bg-white dark:bg-zinc-900 px-2 py-0.5 rounded-md border border-zinc-200 dark:border-zinc-700 font-semibold shadow-2xs">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2 sm:gap-2.5 shrink-0">
        {/* Mobile Search Button */}
        <button
          type="button"
          onClick={() => setIsCommandPaletteOpen(true)}
          className="md:hidden p-2 rounded-lg text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
          aria-label="Open Search Command Palette"
        >
          <Search className="w-4 h-4" />
        </button>

        {/* Quick Upload Button */}
        {userRole !== "viewer" && (
          <button
            type="button"
            onClick={() => setIsUploadModalOpen(true)}
            className="h-9 px-3.5 rounded-xl bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 text-xs sm:text-sm font-semibold hover:opacity-90 transition flex items-center gap-1.5 shadow-xs cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">Upload</span>
          </button>
        )}

        {/* Ask AI Shortcut */}
        <button
          type="button"
          onClick={() => setCurrentScreen("ask")}
          className="h-9 px-3 rounded-xl border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs sm:text-sm font-medium text-zinc-700 dark:text-zinc-300 transition flex items-center gap-1.5 cursor-pointer"
          title="Ask Sovereign AI"
        >
          <Sparkles className="w-4 h-4 text-zinc-900 dark:text-zinc-100" />
          <span className="hidden lg:inline">Ask AI</span>
        </button>

        {/* Bilingual Switcher */}
        <LanguageSwitcher />

        {/* User Profile Avatar */}
        <button
          type="button"
          onClick={onOpenLoginModal}
          className="flex items-center gap-2 pl-1.5 hover:opacity-85 transition text-start cursor-pointer"
          title="Click to view profile or sign out"
        >
          <div className="w-9 h-9 rounded-full bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 border border-zinc-200 dark:border-zinc-800 flex items-center justify-center font-bold text-xs sm:text-sm shadow-xs">
            {(currentUser?.name || "AD").slice(0, 2).toUpperCase()}
          </div>
        </button>
      </div>
    </header>
  );
}
