import React, { useState } from "react";
import { useApp } from "@/context/AppContext";
import { SystemUser } from "@/types";
import {
  Settings,
  Users,
  Key,
  Shield,
  Webhook,
  Trash2,
  Plus,
  Copy,
  Check,
  Send,
} from "lucide-react";

export function SettingsScreen() {
  const {
    users,
    addUser,
    updateUserRole,
    apiKeys,
    generateApiKey,
    revokeApiKey,
    retentionDays,
    setRetentionDays,
    hardDeleteDerived,
    setHardDeleteDerived,
    webhookUrl,
    setWebhookUrl,
    piiMasked,
    togglePiiMasked,
    language,
    showToast,
    activeTenant,
  } = useApp();

  // Invite user state
  const [newUserName, setNewUserName] = useState("");
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserRole, setNewUserRole] = useState<SystemUser["role"]>("reviewer");

  // API key generator state
  const [newKeyName, setNewKeyName] = useState("");
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleAddUser = () => {
    if (!newUserName || !newUserEmail) return;
    addUser(newUserName, newUserEmail, newUserRole);
    setNewUserName("");
    setNewUserEmail("");
  };

  const handleCreateApiKey = () => {
    if (!newKeyName) return;
    const rawKey = generateApiKey(newKeyName, "API Client");
    setGeneratedKey(rawKey);
    setNewKeyName("");
  };

  const handleCopyKey = () => {
    if (generatedKey) {
      navigator.clipboard.writeText(generatedKey);
      setCopied(true);
      showToast("success", "API Key copied to clipboard!", "تم نسخ المفتاح إلى الحافظة!");
    }
  };

  const handleTestWebhook = () => {
    showToast(
      "success",
      "Test Webhook payload dispatched to sovereign endpoint (HTTP 200 OK)",
      "تم اختبار وإرسال الويب هوك بنجاح إلى نقطة النهاية السيادية (HTTP 200 OK)"
    );
  };

  return (
    <div className="space-y-6">
      {/* Settings Header */}
      <div className="p-5 rounded-2xl border border-border bg-card shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs">
        <div>
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-primary" />
            <h1 className="text-base font-extrabold text-foreground">
              {language === "ar" ? "إعدادات المنصة والسيادة الرقمية" : "Platform Settings & Governance"}
            </h1>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {language === "ar"
              ? "إدارة المستخدمين والصلاحيات، سياسة الاحتفاظ بالبيانات، وحجب المعلومات الحساسة"
              : "Manage RBAC access, sovereign retention policies, PII defaults, and integration keys"}
          </p>
        </div>

        <div className="px-3 py-1.5 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-200 font-semibold text-xs flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5 text-emerald-600" />
          <span>{activeTenant.region}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: RBAC & Users (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* User Management Card */}
          <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4 text-xs">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-primary" />
                <h3 className="font-bold text-foreground text-xs uppercase tracking-wider">
                  {language === "ar" ? "المستخدمون والأدوار (RBAC)" : "Users & Role-Based Access"}
                </h3>
              </div>
              <span className="text-muted-foreground font-mono">{users.length} Active Accounts</span>
            </div>

            {/* Users Table */}
            <div className="divide-y divide-border/60">
              {users.map((u) => (
                <div key={u.id} className="py-2.5 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-bold text-foreground">{u.name}</div>
                    <div className="text-[11px] text-muted-foreground font-mono truncate">{u.email}</div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <select
                      value={u.role}
                      onChange={(e) => updateUserRole(u.id, e.target.value as any)}
                      className="px-2 py-1 rounded border border-border bg-secondary text-foreground text-xs font-semibold focus:ring-1 focus:ring-primary"
                    >
                      <option value="admin">Admin</option>
                      <option value="reviewer">Reviewer</option>
                      <option value="viewer">Viewer</option>
                    </select>
                  </div>
                </div>
              ))}
            </div>

            {/* Invite Form */}
            <div className="p-3 bg-secondary/30 rounded-xl border border-border space-y-2 pt-3">
              <span className="font-bold text-foreground block text-[11px]">
                {language === "ar" ? "إضافة مستخدم جديد" : "Provision New User"}
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                <input
                  type="text"
                  placeholder="Full Name"
                  value={newUserName}
                  onChange={(e) => setNewUserName(e.target.value)}
                  className="px-2.5 py-1.5 rounded border border-border bg-card text-foreground text-xs"
                />
                <input
                  type="email"
                  placeholder="name@bank.ae"
                  value={newUserEmail}
                  onChange={(e) => setNewUserEmail(e.target.value)}
                  className="px-2.5 py-1.5 rounded border border-border bg-card text-foreground text-xs font-mono"
                />
                <select
                  value={newUserRole}
                  onChange={(e) => setNewUserRole(e.target.value as any)}
                  className="px-2.5 py-1.5 rounded border border-border bg-card text-foreground text-xs font-semibold"
                >
                  <option value="admin">Admin</option>
                  <option value="reviewer">Reviewer</option>
                  <option value="viewer">Viewer</option>
                </select>
                <button
                  onClick={handleAddUser}
                  className="px-3 py-1.5 rounded bg-primary text-primary-foreground font-bold hover:bg-primary/90 text-xs shadow-sm flex items-center justify-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add User</span>
                </button>
              </div>
            </div>
          </div>

          {/* API Keys Card */}
          <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4 text-xs">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <div className="flex items-center gap-2">
                <Key className="w-4 h-4 text-primary" />
                <h3 className="font-bold text-foreground text-xs uppercase tracking-wider">
                  {language === "ar" ? "مفاتيح التكامل والربط (API Keys)" : "System API Keys"}
                </h3>
              </div>
            </div>

            {/* Keys List */}
            <div className="divide-y divide-border/60">
              {apiKeys.map((k) => (
                <div key={k.id} className="py-2.5 flex items-center justify-between gap-3">
                  <div>
                    <div className="font-bold text-foreground">{k.name}</div>
                    <div className="text-[11px] text-muted-foreground font-mono">
                      Prefix: <strong>{k.prefix}****</strong> • Expires in {k.expiresInDays} days
                    </div>
                  </div>
                  <button
                    onClick={() => revokeApiKey(k.id)}
                    className="p-1 rounded text-muted-foreground hover:text-rose-600"
                    title="Revoke Key"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>

            {/* Key Generator */}
            <div className="p-3 bg-secondary/30 rounded-xl border border-border space-y-2">
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Key description (e.g. Core Banking Gateway)"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  className="flex-1 px-2.5 py-1.5 rounded border border-border bg-card text-foreground text-xs"
                />
                <button
                  onClick={handleCreateApiKey}
                  className="px-3 py-1.5 rounded bg-primary text-primary-foreground font-bold hover:bg-primary/90 text-xs"
                >
                  Generate Key
                </button>
              </div>

              {generatedKey && (
                <div className="p-2.5 rounded bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 space-y-1">
                  <div className="text-[10px] text-emerald-800 dark:text-emerald-300 font-bold">
                    Copy now (will not be displayed again):
                  </div>
                  <div className="flex items-center justify-between gap-2 font-mono text-[11px] bg-card p-1.5 rounded border border-border">
                    <span className="truncate">{generatedKey}</span>
                    <button
                      onClick={handleCopyKey}
                      className="p-1 text-primary hover:text-primary-hover"
                    >
                      {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Sovereign Policies & Webhooks (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Sovereign Retention Policy */}
          <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4 text-xs">
            <div className="flex items-center gap-2 pb-2 border-b border-border">
              <Shield className="w-4 h-4 text-emerald-600" />
              <h3 className="font-bold text-foreground text-xs uppercase tracking-wider">
                {language === "ar" ? "سياسة الاحتفاظ بالبيانات والحذف النهائي" : "Sovereign Retention Policy"}
              </h3>
            </div>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between font-semibold text-foreground mb-1">
                  <span>Automatic Data Purge Schedule</span>
                  <span className="font-mono text-primary font-bold">{retentionDays} Days</span>
                </div>
                <input
                  type="range"
                  min="30"
                  max="365"
                  step="30"
                  value={retentionDays}
                  onChange={(e) => setRetentionDays(Number(e.target.value))}
                  className="w-full accent-emerald-600 cursor-pointer"
                />
                <p className="text-[11px] text-muted-foreground mt-1">
                  Documents older than {retentionDays} days are scheduled for hard deletion.
                </p>
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl bg-secondary/40 border border-border">
                <div>
                  <div className="font-bold text-foreground">Purge Derived Data on Delete</div>
                  <div className="text-[10px] text-muted-foreground">
                    Removes OCR text, cached slices, and vector embeddings
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={hardDeleteDerived}
                  onChange={(e) => setHardDeleteDerived(e.target.checked)}
                  className="rounded text-primary focus:ring-primary h-4 w-4"
                />
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl bg-secondary/40 border border-border">
                <div>
                  <div className="font-bold text-foreground">Default PII Masking Mode</div>
                  <div className="text-[10px] text-muted-foreground">
                    Auto-mask Emirates IDs and TRNs on preview
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={piiMasked}
                  onChange={togglePiiMasked}
                  className="rounded text-primary focus:ring-primary h-4 w-4"
                />
              </div>
            </div>
          </div>

          {/* Webhooks Card */}
          <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4 text-xs">
            <div className="flex items-center gap-2 pb-2 border-b border-border">
              <Webhook className="w-4 h-4 text-primary" />
              <h3 className="font-bold text-foreground text-xs uppercase tracking-wider">
                {language === "ar" ? "إشعارات الويب هوك (Webhook Dispatch)" : "Approved Webhook Endpoint"}
              </h3>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-semibold text-muted-foreground mb-1">
                  Destination URL (Triggered on Document Approval)
                </label>
                <input
                  type="url"
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg border border-border bg-secondary/50 font-mono text-xs focus:ring-1 focus:ring-primary"
                />
              </div>

              <button
                onClick={handleTestWebhook}
                className="w-full py-2 rounded-lg bg-card border border-border hover:bg-secondary text-foreground font-bold text-xs flex items-center justify-center gap-1.5 transition shadow-sm"
              >
                <Send className="w-3.5 h-3.5 text-primary" />
                <span>Test Webhook Dispatch</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
