"use client";

import React, { useState } from "react";
import { useApp } from "@/context/AppContext";
import { ShieldCheck, Lock, Mail, Loader2, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";

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

  if (!isOpen) return null;

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.auth.login(email.trim().toLowerCase(), password);
      setIsAuthenticated(true);
      showToast(
        "success",
        `Authenticated as ${res.user.full_name || email} (${res.user.role})`,
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
    }
  };

  const handleFillDemo = () => {
    setEmail("admin@alhilal-demo.ae");
    setPassword("AdminSecurePass2026!");
  };

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
          >
            ✕
          </button>
        )}

        {/* Header Branding (Matching DocIntel v2) */}
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

        {/* Form */}
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
              />
            </div>
          </div>

          {/* Quick Demo Credentials Autofill Pill */}
          <div className="flex items-center justify-between text-[11px] text-zinc-400">
            <span>Default admin:</span>
            <button
              type="button"
              onClick={handleFillDemo}
              className="text-emerald-600 dark:text-emerald-400 hover:underline font-semibold"
            >
              Autofill Demo Admin Credentials
            </button>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 font-bold text-xs hover:opacity-90 disabled:opacity-50 transition shadow-xs flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Authenticating...</span>
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
            className="hover:text-zinc-700 dark:hover:text-zinc-200"
          >
            {language === "ar" ? "English" : "تبديل إلى العربية"}
          </button>
          <span className="font-mono">UAE PDPL Law 45/2021</span>
        </div>
      </div>
    </div>
  );
}
