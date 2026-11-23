"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "@/context/AppContext";
import { ShieldCheck, Lock, Mail, Loader2, ArrowRight, Zap } from "lucide-react";
import { api } from "@/lib/api";

const DEMO_EMAIL = "admin@alhilal-demo.ae";
const DEMO_PASS = "AdminSecurePass2026!";

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

  const [email, setEmail] = useState(DEMO_EMAIL);
  const [password, setPassword] = useState(DEMO_PASS);
  const [loading, setLoading] = useState(false);
  const [autoLoginChecked, setAutoLoginChecked] = useState(true);

  const executeLogin = async (loginEmail: string, loginPass: string, isAuto = false) => {
    setLoading(true);
    try {
      await api.auth.login(loginEmail.trim().toLowerCase(), loginPass);
      setIsAuthenticated(true);
      await refreshDocuments();
      await refreshAuditLogs();
      onClose();
    } catch (err: any) {
      if (!isAuto) {
        showToast(
          "error",
          err.message || "Invalid credentials. Please verify your email and password.",
          "فشل التحقق من الهوية، يرجى التأكد من البيانات المدخلة"
        );
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("sanad_auto_login");
      const shouldAuto = saved !== "false";
      setAutoLoginChecked(shouldAuto);
      if (shouldAuto && !isAuthenticated && !loading) {
        executeLogin(DEMO_EMAIL, DEMO_PASS, true);
      }
    }
  }, [isOpen, isAuthenticated]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) return;
    await executeLogin(email, password, false);
  };

  const handleInstantAutoLogin = async () => {
    setEmail(DEMO_EMAIL);
    setPassword(DEMO_PASS);
    if (typeof window !== "undefined") {
      localStorage.setItem("sanad_auto_login", "true");
    }
    await executeLogin(DEMO_EMAIL, DEMO_PASS, false);
  };

  const toggleAutoLoginPreference = (e: React.ChangeEvent<HTMLInputElement>) => {
    const checked = e.target.checked;
    setAutoLoginChecked(checked);
    if (typeof window !== "undefined") {
      localStorage.setItem("sanad_auto_login", checked ? "true" : "false");
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 select-none">
      <div
        className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl max-w-md w-full p-6 sm:p-8 shadow-2xl flex flex-col gap-6 relative text-zinc-900 dark:text-zinc-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button - Only visible if already authenticated */}
        {isAuthenticated && (
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 font-bold p-1 rounded-md"
            aria-label="Close"
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

        {/* Normal Secure Form */}
        <form onSubmit={handleLogin} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5 text-start">
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
                className="w-full pl-9 pr-3 py-2.5 text-xs rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 font-mono outline-hidden focus:ring-1 focus:ring-zinc-900 dark:focus:ring-white transition"
                required
                autoComplete="email"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1.5 text-start">
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
                className="w-full pl-9 pr-3 py-2.5 text-xs rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 font-mono outline-hidden focus:ring-1 focus:ring-zinc-900 dark:focus:ring-white transition"
                required
                autoComplete="current-password"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 font-bold text-xs hover:opacity-90 disabled:opacity-50 transition shadow-xs flex items-center justify-center gap-2 cursor-pointer mt-1"
          >
            {loading ? (
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

          <div className="relative flex py-1 items-center">
            <div className="grow border-t border-zinc-200 dark:border-zinc-800"></div>
            <span className="shrink mx-2 text-[10px] text-zinc-400 uppercase tracking-widest font-mono">
              {language === "ar" ? "أو وصول سريع" : "Or Quick Access"}
            </span>
            <div className="grow border-t border-zinc-200 dark:border-zinc-800"></div>
          </div>

          <button
            type="button"
            onClick={handleInstantAutoLogin}
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 font-bold text-xs transition flex items-center justify-center gap-2 cursor-pointer shadow-xs"
          >
            <Zap className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
            <span>{language === "ar" ? "تسجيل دخول تلقائي بنقرة واحدة (مسؤول)" : "1-Click Instant Auto-Login (Admin)"}</span>
          </button>

          <label className="flex items-center gap-2 text-[11px] text-zinc-500 dark:text-zinc-400 cursor-pointer pt-0.5">
            <input
              type="checkbox"
              checked={autoLoginChecked}
              onChange={toggleAutoLoginPreference}
              className="rounded-sm border-zinc-300 dark:border-zinc-700 text-emerald-600 focus:ring-emerald-500"
            />
            <span>{language === "ar" ? "تفعيل تسجيل الدخول التلقائي في المرات القادمة" : "Auto-login automatically on launch"}</span>
          </label>
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
