"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useApp } from "@/context/AppContext";
import { ShieldCheck, Lock, Mail, Loader2, ArrowRight, Zap, Sparkles } from "lucide-react";
import { api } from "@/lib/api";

const STORAGE_AUTO_LOGIN = "sanad_auto_login";

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function LoginModal({ isOpen, onClose }: LoginModalProps) {
  const {
    language,
    toggleLanguage,
    showToast,
    refreshDocuments,
    refreshAuditLogs,
    isAuthenticated,
    setIsAuthenticated,
  } = useApp();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingMsg, setLoadingMsg] = useState("");
  const [autoLogin, setAutoLogin] = useState(true);

  // Initialize auto-login preference
  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem(STORAGE_AUTO_LOGIN);
      if (stored !== null) {
        setAutoLogin(stored === "true");
      } else {
        // Default to enabled for easy access
        localStorage.setItem(STORAGE_AUTO_LOGIN, "true");
        setAutoLogin(true);
      }
    }
  }, []);

  const executeLogin = useCallback(
    async (loginEmail: string, loginPass: string, isAutomatic = false) => {
      setLoading(true);
      setLoadingMsg(
        isAutomatic
          ? language === "ar"
            ? "تسجيل دخول تلقائي..."
            : "Auto-logging in..."
          : language === "ar"
          ? "جارٍ التحقق من الهوية..."
          : "Authenticating..."
      );

      try {
        const res = await api.auth.login(loginEmail.trim().toLowerCase(), loginPass);
        setIsAuthenticated(true);
        showToast(
          "success",
          `Authenticated as ${res.user.full_name || loginEmail} (${res.user.role})`,
          "تم تسجيل الدخول بنجاح"
        );
        await refreshDocuments();
        await refreshAuditLogs();
        onClose();
      } catch (err: any) {
        showToast(
          "error",
          err.message || "Invalid credentials. Please verify your email and password.",
          "فشل التحقق من الهوية، يرجى التأكد من البيانات المدخلة"
        );
      } finally {
        setLoading(false);
        setLoadingMsg("");
      }
    },
    [language, refreshAuditLogs, refreshDocuments, onClose, setIsAuthenticated, showToast]
  );

  // Trigger automatic login on mount if preference or query param is set
  useEffect(() => {
    if (!isOpen || isAuthenticated) return;

    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const urlAutoLogin = params.get("autologin") === "true";
      const prefAutoLogin = localStorage.getItem(STORAGE_AUTO_LOGIN) === "true";

      if (urlAutoLogin || prefAutoLogin) {
        // Small delay for clean DOM hydration
        const timer = setTimeout(() => {
          executeLogin("admin@alhilal-demo.ae", "AdminSecurePass2026!", true);
        }, 350);
        return () => clearTimeout(timer);
      }
    }
  }, [isOpen, isAuthenticated, executeLogin]);

  const handleToggleAutoLogin = (enabled: boolean) => {
    setAutoLogin(enabled);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_AUTO_LOGIN, String(enabled));
    }
  };

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeLogin(email, password, false);
  };

  const handleFillDemo = () => {
    setEmail("admin@alhilal-demo.ae");
    setPassword("AdminSecurePass2026!");
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 select-none">
      <div
        className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl max-w-md w-full p-6 sm:p-8 shadow-2xl flex flex-col gap-5 relative text-zinc-900 dark:text-zinc-100 transition-all"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button - Only visible if already authenticated */}
        {isAuthenticated && (
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 font-bold p-1 rounded-md"
          >
            ✕
          </button>
        )}

        {/* Header Branding */}
        <div className="flex flex-col items-center text-center gap-2">
          <div className="w-12 h-12 rounded-xl bg-zinc-950 text-emerald-400 dark:bg-zinc-100 dark:text-emerald-700 flex items-center justify-center font-extrabold text-2xl shadow-md">
            D
          </div>
          <h2 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            {language === "ar" ? "تسجيل الدخول المؤسسي • دوك إنتل" : "Sign in to DocIntel"}
          </h2>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            <span>UAE Sovereign Identity Gateway · UAE North</span>
          </div>
        </div>

        {/* ⚡ 1-Click Instant Auto-Login Button */}
        <div className="flex flex-col gap-2 pt-1">
          <button
            type="button"
            disabled={loading}
            onClick={() => executeLogin("admin@alhilal-demo.ae", "AdminSecurePass2026!", false)}
            className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white font-bold text-xs transition shadow-sm flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
          >
            {loading && loadingMsg ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-white" />
                <span>{loadingMsg}</span>
              </>
            ) : (
              <>
                <Zap className="w-4 h-4 text-amber-300 fill-amber-300 shrink-0" />
                <span>
                  {language === "ar"
                    ? "تسجيل دخول فوري كمسؤول تجريبي (بنقرة واحدة)"
                    : "1-Click Instant Auto-Login (Demo Admin)"}
                </span>
                <ArrowRight className="w-3.5 h-3.5 opacity-80" />
              </>
            )}
          </button>
          <p className="text-[11px] text-zinc-500 dark:text-zinc-400 text-center flex items-center justify-center gap-1">
            <Sparkles className="w-3 h-3 text-emerald-500 shrink-0" />
            <span>
              {language === "ar"
                ? "دخول فوري بحساب مسؤول بنك الهلال مع صلاحيات كاملة"
                : "Instant access with pre-configured Al Hilal Admin credentials"}
            </span>
          </p>
        </div>

        {/* Divider */}
        <div className="relative flex items-center justify-center my-0.5">
          <div className="border-t border-zinc-200 dark:border-zinc-800 w-full" />
          <span className="bg-white dark:bg-zinc-900 px-3 text-[11px] font-medium text-zinc-400 shrink-0">
            {language === "ar" ? "أو تسجيل الدخول اليدوي" : "or sign in manually"}
          </span>
          <div className="border-t border-zinc-200 dark:border-zinc-800 w-full" />
        </div>

        {/* Manual Form */}
        <form onSubmit={handleManualSubmit} className="flex flex-col gap-3.5">
          <div className="flex flex-col gap-1 text-start">
            <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
              {language === "ar" ? "البريد الإلكتروني المؤسسي" : "Work Email"}
            </label>
            <div className="relative flex items-center">
              <Mail className="absolute left-3 w-4 h-4 text-zinc-400" />
              <input
                type="email"
                placeholder="name@organization.ae"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 font-mono outline-hidden focus:ring-1 focus:ring-zinc-900 dark:focus:ring-white transition"
                required
              />
            </div>
          </div>

          <div className="flex flex-col gap-1 text-start">
            <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
              {language === "ar" ? "كلمة المرور" : "Password"}
            </label>
            <div className="relative flex items-center">
              <Lock className="absolute left-3 w-4 h-4 text-zinc-400" />
              <input
                type="password"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 font-mono outline-hidden focus:ring-1 focus:ring-zinc-900 dark:focus:ring-white transition"
                required
              />
            </div>
          </div>

          {/* Auto-login Toggle & Autofill Pill */}
          <div className="flex items-center justify-between text-xs pt-0.5">
            <label className="flex items-center gap-2 cursor-pointer select-none text-zinc-600 dark:text-zinc-300">
              <input
                type="checkbox"
                checked={autoLogin}
                onChange={(e) => handleToggleAutoLogin(e.target.checked)}
                className="w-3.5 h-3.5 rounded text-emerald-600 focus:ring-emerald-500 border-zinc-300 dark:border-zinc-700 dark:bg-zinc-800 cursor-pointer"
              />
              <span className="text-[11px] font-medium">
                {language === "ar" ? "تسجيل دخول تلقائي مستقبلاً" : "Auto-login on next visit"}
              </span>
            </label>
            <button
              type="button"
              onClick={handleFillDemo}
              className="text-[11px] text-emerald-600 dark:text-emerald-400 hover:underline font-semibold cursor-pointer"
            >
              {language === "ar" ? "ملء تلقائي للبيانات" : "Autofill Demo"}
            </button>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 rounded-xl bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 font-bold text-xs hover:opacity-90 disabled:opacity-50 transition shadow-xs flex items-center justify-center gap-2 cursor-pointer"
          >
            {loading && !loadingMsg.includes("Auto") ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>{language === "ar" ? "جارٍ التحقق..." : "Authenticating..."}</span>
              </>
            ) : (
              <>
                <span>{language === "ar" ? "تسجيل الدخول بالبيانات" : "Sign In with Credentials"}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </form>

        {/* Footer info */}
        <div className="flex items-center justify-between text-[11px] text-zinc-400 pt-2 border-t border-zinc-100 dark:border-zinc-800">
          <button
            type="button"
            onClick={toggleLanguage}
            className="hover:text-zinc-700 dark:hover:text-zinc-200 cursor-pointer"
          >
            {language === "ar" ? "English" : "تبديل إلى العربية"}
          </button>
          <span className="font-mono">UAE PDPL Law 45/2021</span>
        </div>
      </div>
    </div>
  );
}
