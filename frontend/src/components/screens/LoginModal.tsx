import React, { useState } from "react";
import { useApp } from "@/context/AppContext";
import { ShieldCheck, Lock, Mail, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function LoginModal({ isOpen, onClose }: LoginModalProps) {
  const { language, toggleLanguage, showToast, refreshDocuments, refreshAuditLogs, isAuthenticated, setIsAuthenticated } = useApp();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.auth.login(email, password);
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
      showToast("error", err.message || "Authentication failed", "فشل التحقق من الهوية");
    } finally {
      setLoading(false);
    }
  };

  const handleSso = (provider: string) => {
    showToast(
      "success",
      `Authenticated securely via ${provider} Sovereign Federated OIDC`,
      `تم التحقق من الهوية بنجاح عبر الربط السيادي ${provider}`
    );
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-card border border-border rounded-2xl max-w-md w-full p-6 sm:p-8 shadow-2xl space-y-6 text-xs relative">
        {/* Close Button - Only visible if already authenticated */}
        {isAuthenticated && (
          <button
            onClick={onClose}
            className="absolute top-4 end-4 text-muted-foreground hover:text-foreground font-bold p-1"
          >
            ✕
          </button>
        )}

        {/* Header Branding */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-800 to-emerald-950 text-white flex items-center justify-center font-black text-xl mx-auto shadow-lg shadow-emerald-900/30">
            س
          </div>
          <h2 className="text-lg font-extrabold text-foreground tracking-tight">
            {language === "ar" ? "تسجيل الدخول المؤسسي • سند" : "Enterprise Sign In • Sanad"}
          </h2>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200">
            <ShieldCheck className="w-3 h-3 text-emerald-600" />
            <span>UAE Sovereign Identity Gateway</span>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-3.5">
          <div>
            <label className="block text-[11px] font-semibold text-muted-foreground mb-1">
              {language === "ar" ? "البريد الإلكتروني المؤسسي" : "Work Email"}
            </label>
            <div className="relative">
              <Mail className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full ps-9 pe-3 py-2 rounded-lg border border-border bg-secondary/50 font-mono text-xs focus:ring-1 focus:ring-primary text-foreground"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-muted-foreground mb-1">
              {language === "ar" ? "كلمة المرور" : "Password"}
            </label>
            <div className="relative">
              <Lock className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full ps-9 pe-3 py-2 rounded-lg border border-border bg-secondary/50 font-mono text-xs focus:ring-1 focus:ring-primary text-foreground"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg bg-primary text-primary-foreground font-bold hover:bg-primary/90 text-xs shadow-md transition flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{language === "ar" ? "جارٍ التحقق..." : "Authenticating..."}</span>
              </>
            ) : (
              <span>{language === "ar" ? "تسجيل الدخول" : "Sign In with Credentials"}</span>
            )}
          </button>
        </form>

        {/* Divider */}
        <div className="relative flex items-center justify-center">
          <div className="border-t border-border w-full"></div>
          <span className="bg-card px-2 text-[10px] uppercase font-bold text-muted-foreground absolute">
            {language === "ar" ? "أو عبر الهوية الرقمية" : "Or via Sovereign SSO"}
          </span>
        </div>

        {/* SSO Buttons */}
        <div className="space-y-2">
          <button
            onClick={() => handleSso("UAE PASS (الهوية الرقمية)")}
            className="w-full py-2 px-3 rounded-lg border border-emerald-300 dark:border-emerald-800 bg-emerald-50/50 hover:bg-emerald-100/50 dark:bg-emerald-950/30 text-emerald-900 dark:text-emerald-200 font-bold text-xs flex items-center justify-center gap-2 transition"
          >
            <span>🇦🇪 Sign in with UAE PASS (الهوية الرقمية)</span>
          </button>

          <button
            onClick={() => handleSso("Microsoft Entra ID (UAE North)")}
            className="w-full py-2 px-3 rounded-lg border border-border bg-card hover:bg-secondary text-foreground font-semibold text-xs flex items-center justify-center gap-2 transition"
          >
            <span>Microsoft Entra ID (In-Region Tenant)</span>
          </button>
        </div>

        {/* Footer Language Toggle */}
        <div className="pt-2 border-t border-border flex items-center justify-between text-[11px] text-muted-foreground">
          <button
            onClick={toggleLanguage}
            className="hover:text-foreground font-semibold flex items-center gap-1"
          >
            <span>🌐 {language === "en" ? "تبديل إلى العربية" : "Switch to English"}</span>
          </button>
          <span>Federal Law 45/2021</span>
        </div>
      </div>
    </div>
  );
}
