"use client";

import React, { useState } from "react";
import { useApp } from "@/context/AppContext";
import { api } from "@/lib/api";
import { Send, Eye, EyeOff, Search, Download, Trash2 } from "lucide-react";

export function GovernanceScreen() {
  const {
    auditLogs,
    apiKeys,
    generateApiKey,
    revokeApiKey,
    retentionDays,
    saveRetentionDays,
    runRetentionSweep,
    testWebhook,
    webhookUrl: contextWebhookUrl,
    setWebhookUrl: setContextWebhookUrl,
    piiMasked,
    togglePiiMasked,
    userRole,
    showToast,
    users,
    addUser,
    deleteUser,
  } = useApp();

  const [activeTab, setActiveTab] = useState<"audit" | "team" | "apikeys" | "retention" | "webhooks">("audit");
  const [searchQuery, setSearchQuery] = useState("");
  const [actionFilter, setActionFilter] = useState("all");

  // Retention state
  const [sliderDays, setSliderDays] = useState(retentionDays || 90);
  const [isSavingRetention, setIsSavingRetention] = useState(false);
  const [isSweeping, setIsSweeping] = useState(false);

  // API Key state
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyRole, setNewKeyRole] = useState<string>("reviewer");
  const [createdKeyValue, setCreatedKeyValue] = useState<string | null>(null);

  // Webhook state
  const [webhookUrl, setWebhookUrl] = useState(contextWebhookUrl || "");
  const [isTestingWebhook, setIsTestingWebhook] = useState(false);
  const [isSavingWebhook, setIsSavingWebhook] = useState(false);
  const [webhookResult, setWebhookResult] = useState<any>(null);

  // Team invite state
  const [inviteName, setInviteName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [invitePassword, setInvitePassword] = useState("");
  const [generatedPasswordNotice, setGeneratedPasswordNotice] = useState<string | null>(null);
  const [inviteRole, setInviteRole] = useState<"admin" | "reviewer" | "viewer">("reviewer");

  const generateRandomPassword = () => {
    const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@#$%&*";
    const array = new Uint8Array(16);
    window.crypto.getRandomValues(array);
    let pwd = "";
    for (let i = 0; i < array.length; i++) {
      pwd += chars[array[i] % chars.length];
    }
    setInvitePassword(pwd);
    setGeneratedPasswordNotice(pwd);
  };

  const filteredLogs = auditLogs.filter((log) => {
    const matchesSearch =
      log.actorName?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.action?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.detailsEn?.toLowerCase().includes(searchQuery.toLowerCase());
    if (actionFilter === "all") return matchesSearch;
    return matchesSearch && log.action.toLowerCase().includes(actionFilter.toLowerCase());
  });

  const handleSaveRetention = async () => {
    setIsSavingRetention(true);
    try {
      await saveRetentionDays(sliderDays);
      showToast("success", `Retention updated to ${sliderDays} days`, "تم تحديث مدة الاستبقاء");
    } catch (err: any) {
      showToast("error", err.message || "Failed to update retention", "تعذر تحديث الاستبقاء");
    } finally {
      setIsSavingRetention(false);
    }
  };

  const handleRunSweep = async () => {
    setIsSweeping(true);
    try {
      await runRetentionSweep();
      showToast("success", "Retention sweep executed for caller tenant", "تم تشغيل مسح الاستبقاء للمستأجر الحالي");
    } catch (err: any) {
      showToast("error", err.message || "Sweep failed", "فشل تشغيل المسح");
    } finally {
      setIsSweeping(false);
    }
  };

  const handleGenerateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    try {
      const fullKey = await generateApiKey(newKeyName.trim(), newKeyRole);
      setCreatedKeyValue(fullKey);
      setNewKeyName("");
      showToast("success", "API key created", "تم إنشاء مفتاح API");
    } catch (err: any) {
      showToast("error", err.message || "Failed to create key", "تعذر إنشاء المفتاح");
    }
  };

  const handleRevokeKey = async (id: string) => {
    if (confirm("Are you sure you want to revoke this API key?")) {
      try {
        await revokeApiKey(id);
        showToast("info", "API key revoked", "تم إبطال المفتاح");
      } catch (err: any) {
        showToast("error", err.message || "Failed to revoke key", "تعذر إبطال المفتاح");
      }
    }
  };

  const handleTestWebhook = async () => {
    setIsTestingWebhook(true);
    try {
      const res = await testWebhook(webhookUrl);
      setWebhookResult(res);
      showToast("info", "Webhook test evaluated", "تم تقييم اختبار الويب هوك");
    } catch (err: any) {
      showToast("error", err.message || "Webhook test failed", "فشل اختبار الويب هوك");
    } finally {
      setIsTestingWebhook(false);
    }
  };

  const handleSaveWebhook = async () => {
    setIsSavingWebhook(true);
    try {
      await api.tenants.updateSettings({ webhook_url: webhookUrl });
      setContextWebhookUrl(webhookUrl);
      showToast("success", "Webhook URL saved successfully", "تم حفظ رابط الويب هوك بنجاح");
    } catch (err: any) {
      showToast("error", err.message || "Failed to save webhook URL", "تعذر حفظ رابط الويب هوك");
    } finally {
      setIsSavingWebhook(false);
    }
  };

  const handleInviteUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteName.trim() || !inviteEmail.trim()) {
      showToast("error", "Name and email are required", "الاسم والبريد مطلوبان");
      return;
    }
    if (!invitePassword || invitePassword.length < 8) {
      showToast("error", "Initial password must be at least 8 characters", "يجب أن تكون كلمة المرور 8 خانات على الأقل");
      return;
    }
    try {
      await addUser(inviteName.trim(), inviteEmail.trim(), inviteRole, invitePassword);
      setInviteName("");
      setInviteEmail("");
      showToast("success", "User added to workspace", "تمت إضافة المستخدم بنجاح");
    } catch (err: any) {
      showToast("error", err.message || "Failed to add user", "تعذر إضافة المستخدم");
    }
  };

  return (
    <div className="flex flex-col gap-5">
      {/* Header (Matching screens/Governance.dc.html) */}
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
          Audit, Access & Retention
        </h1>
        <p className="text-xs text-zinc-500">
          Who did what, who can do what, and how long sovereign data is preserved under UAE PDPL.
        </p>
      </div>

      {/* Tabs Bar */}
      <div className="flex items-center gap-1 border-b border-zinc-200 dark:border-zinc-800 text-xs font-medium">
        {[
          { id: "audit", label: "Audit Log", count: auditLogs.length },
          { id: "team", label: "Team & Roles", count: users.length },
          { id: "apikeys", label: "API Keys", count: apiKeys.length },
          { id: "retention", label: "Retention Policy" },
          { id: "webhooks", label: "Webhooks" },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id as any)}
            className={`px-3 py-2.5 border-b-2 transition flex items-center gap-1.5 ${
              activeTab === t.id
                ? "border-zinc-900 dark:border-white text-zinc-900 dark:text-zinc-100 font-bold"
                : "border-transparent text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
            }`}
          >
            <span>{t.label}</span>
            {t.count !== undefined && (
              <span className="font-mono text-[10px] text-zinc-400 bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.2 rounded-full">
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab 1: Audit Log */}
      {activeTab === "audit" && (
        <section className="border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-900 overflow-hidden shadow-xs flex flex-col">
          <div className="p-3 bg-zinc-50 dark:bg-zinc-950/60 border-b border-zinc-200 dark:border-zinc-800 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 flex-1 max-w-sm relative">
              <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5" />
              <input
                type="text"
                placeholder="Search audit trail by actor, action, doc..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs outline-hidden"
              />
            </div>

            <div className="flex items-center gap-2">
              <select
                value={actionFilter}
                onChange={(e) => setActionFilter(e.target.value)}
                className="px-2.5 py-1.5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs text-zinc-600 dark:text-zinc-300 outline-hidden"
              >
                <option value="all">All Actions</option>
                <option value="upload">Uploads</option>
                <option value="approve">Approvals</option>
                <option value="reject">Rejections</option>
                <option value="correct">Corrections</option>
                <option value="delete">Deletions</option>
              </select>
              {userRole === "admin" && (
                <button
                  type="button"
                  onClick={togglePiiMasked}
                  className={`px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition ${
                    piiMasked
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                      : "border-amber-200 bg-amber-50 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                  }`}
                >
                  {piiMasked ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  <span>{piiMasked ? "PII Masked (Active)" : "PII Unmasked (Audited)"}</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => showToast("info", "Signed CSV export triggered", "تم تصدير سجل التدقيق")}
                className="px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs font-medium flex items-center gap-1"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export CSV</span>
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-start">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/40 text-zinc-500 font-semibold">
                  <th className="p-3 text-start">Time</th>
                  <th className="p-3 text-start">Actor</th>
                  <th className="p-3 text-start">Action</th>
                  <th className="p-3 text-start">Details</th>
                  <th className="p-3 text-start">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                {filteredLogs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-zinc-400">
                      No audit records found.
                    </td>
                  </tr>
                ) : (
                  filteredLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-zinc-50/60 dark:hover:bg-zinc-800/30">
                      <td className="p-3 font-mono text-zinc-400 whitespace-nowrap">
                        {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "Just now"}
                      </td>
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <span className="w-6 h-6 rounded-full bg-zinc-100 dark:bg-zinc-800 text-[10px] font-bold flex items-center justify-center">
                            {(log.actorName || "U").slice(0, 2).toUpperCase()}
                          </span>
                          <span className="font-medium text-zinc-900 dark:text-zinc-100">
                            {log.actorName}
                          </span>
                        </div>
                      </td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                          {log.action}
                        </span>
                      </td>
                      <td className="p-3 text-zinc-600 dark:text-zinc-400">
                        {log.detailsEn}
                        {log.diff && (
                          <span className="block font-mono text-[10px] text-zinc-400 mt-0.5">
                            {log.diff.field}: {log.diff.oldValue} → {log.diff.newValue}
                          </span>
                        )}
                      </td>
                      <td className="p-3 font-mono text-zinc-400 text-[11px]">
                        {log.ipAddress || "127.0.0.1"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Tab 2: Team & Roles */}
      {activeTab === "team" && (
        <section className="flex flex-col gap-6">
          {userRole === "admin" && (
            <div className="flex flex-col gap-3">
              {generatedPasswordNotice && (
                <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 rounded-xl text-xs text-emerald-900 dark:text-emerald-200 flex items-center justify-between">
                  <div>
                    <span className="font-bold">Initial Password Generated: </span>
                    <span className="font-mono bg-white dark:bg-zinc-900 px-2 py-0.5 rounded border border-emerald-300 dark:border-emerald-700 font-semibold">{generatedPasswordNotice}</span>
                    <span className="text-[11px] text-zinc-500 ml-2">(Record securely — shown only once)</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setGeneratedPasswordNotice(null)}
                    className="text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
                  >
                    ✕ Dismiss
                  </button>
                </div>
              )}
              <form onSubmit={handleInviteUser} className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex flex-wrap items-end gap-3 shadow-xs">
                <div className="flex-1 min-w-[160px] flex flex-col gap-1">
                  <label className="text-xs font-semibold text-zinc-500">Name</label>
                  <input
                    type="text"
                    placeholder="Full name"
                    value={inviteName}
                    onChange={(e) => setInviteName(e.target.value)}
                    className="px-3 py-2 text-xs border border-zinc-200 dark:border-zinc-800 rounded-lg bg-zinc-50 dark:bg-zinc-950 outline-hidden"
                  />
                </div>
                <div className="flex-1 min-w-[180px] flex flex-col gap-1">
                  <label className="text-xs font-semibold text-zinc-500">Email Address</label>
                  <input
                    type="email"
                    placeholder="user@organization.ae"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    className="px-3 py-2 text-xs border border-zinc-200 dark:border-zinc-800 rounded-lg bg-zinc-50 dark:bg-zinc-950 outline-hidden"
                  />
                </div>
                <div className="flex-1 min-w-[180px] flex flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-semibold text-zinc-500">Initial Password</label>
                    <button
                      type="button"
                      onClick={generateRandomPassword}
                      className="text-[10px] text-emerald-600 hover:underline font-semibold"
                    >
                      Generate Random
                    </button>
                  </div>
                  <input
                    type="text"
                    placeholder="Min 8 characters"
                    value={invitePassword}
                    onChange={(e) => setInvitePassword(e.target.value)}
                    className="px-3 py-2 text-xs border border-zinc-200 dark:border-zinc-800 rounded-lg bg-zinc-50 dark:bg-zinc-950 font-mono outline-hidden"
                  />
                </div>
                <div className="w-32 flex flex-col gap-1">
                  <label className="text-xs font-semibold text-zinc-500">Role</label>
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value as any)}
                    className="px-3 py-2 text-xs border border-zinc-200 dark:border-zinc-800 rounded-lg bg-zinc-50 dark:bg-zinc-950 outline-hidden"
                  >
                    <option value="reviewer">Reviewer</option>
                    <option value="viewer">Viewer</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <button
                  type="submit"
                  className="px-4 py-2 bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 rounded-lg text-xs font-semibold hover:opacity-90"
                >
                  + Invite Member
                </button>
              </form>
            </div>
          )}

          <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-900 overflow-hidden shadow-xs">
            <table className="w-full text-xs text-start">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950/40 text-zinc-500 font-semibold">
                  <th className="p-3 text-start">User</th>
                  <th className="p-3 text-start">Email</th>
                  <th className="p-3 text-start">Role</th>
                  <th className="p-3 text-start">Status</th>
                  <th className="p-3 text-end">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-800/30">
                    <td className="p-3 font-semibold text-zinc-900 dark:text-zinc-100">{u.name}</td>
                    <td className="p-3 text-zinc-500 font-mono">{u.email}</td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 uppercase">
                        {u.role}
                      </span>
                    </td>
                    <td className="p-3">
                      <span className="text-emerald-600 font-semibold flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        Active
                      </span>
                    </td>
                    <td className="p-3 text-end">
                      {userRole === "admin" && u.role !== "admin" && (
                        <button
                          onClick={() => deleteUser(u.id)}
                          className="text-zinc-400 hover:text-rose-600 transition"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Tab 3: API Keys */}
      {activeTab === "apikeys" && (
        <section className="flex flex-col gap-6">
          {userRole === "admin" && (
            <form onSubmit={handleGenerateKey} className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex flex-wrap items-end gap-3 shadow-xs">
              <div className="flex-1 min-w-[200px] flex flex-col gap-1">
                <label className="text-xs font-semibold text-zinc-500">Key Name / Description</label>
                <input
                  type="text"
                  placeholder="e.g. Core Banking Integration"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  className="px-3 py-2 text-xs border border-zinc-200 dark:border-zinc-800 rounded-lg bg-zinc-50 dark:bg-zinc-950 outline-hidden"
                />
              </div>
              <div className="w-40 flex flex-col gap-1">
                <label className="text-xs font-semibold text-zinc-500">Permitted Role</label>
                <select
                  value={newKeyRole}
                  onChange={(e) => setNewKeyRole(e.target.value)}
                  className="px-3 py-2 text-xs border border-zinc-200 dark:border-zinc-800 rounded-lg bg-zinc-50 dark:bg-zinc-950 outline-hidden"
                >
                  <option value="reviewer">Reviewer</option>
                  <option value="viewer">Viewer</option>
                  <option value="api_client">API Client</option>
                </select>
              </div>
              <button
                type="submit"
                className="px-4 py-2 bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 rounded-lg text-xs font-semibold hover:opacity-90"
              >
                + Generate Key
              </button>
            </form>
          )}

          {createdKeyValue && (
            <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex flex-col gap-2">
              <span className="font-bold text-xs text-emerald-900 dark:text-emerald-200">
                Key Generated Successfully — Copy Now (Will Not Be Shown Again)
              </span>
              <code className="p-2 rounded bg-white dark:bg-zinc-900 border border-emerald-300 font-mono text-xs text-emerald-800 dark:text-emerald-300 select-all">
                {createdKeyValue}
              </code>
            </div>
          )}

          <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-900 overflow-hidden shadow-xs">
            <table className="w-full text-xs text-start">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950/40 text-zinc-500 font-semibold">
                  <th className="p-3 text-start">Key Name</th>
                  <th className="p-3 text-start">Prefix</th>
                  <th className="p-3 text-start">Role</th>
                  <th className="p-3 text-start">Status</th>
                  <th className="p-3 text-end">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                {apiKeys.map((k) => (
                  <tr key={k.id} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-800/30">
                    <td className="p-3 font-semibold text-zinc-900 dark:text-zinc-100">{k.name}</td>
                    <td className="p-3 font-mono text-zinc-400">{k.prefix || "uae_live_..."}</td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 uppercase">
                        {k.role}
                      </span>
                    </td>
                    <td className="p-3">
                      <span className="text-emerald-600 font-semibold">Active</span>
                    </td>
                    <td className="p-3 text-end">
                      {userRole === "admin" && (
                        <button
                          onClick={() => handleRevokeKey(k.id)}
                          className="text-zinc-400 hover:text-rose-600 transition"
                        >
                          Revoke
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Tab 4: Retention */}
      {activeTab === "retention" && (
        <section className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex flex-col gap-6 shadow-xs max-w-2xl">
          <div className="flex flex-col gap-1">
            <h3 className="font-bold text-sm text-zinc-900 dark:text-zinc-100">
              Sovereign Document Retention Window
            </h3>
            <p className="text-xs text-zinc-500 leading-relaxed">
              Define the legal preservation duration (1–3650 days). Documents older than this threshold are purged automatically by the daily sweeper, strictly scoped to the caller&apos;s tenant.
            </p>
          </div>

          <div className="flex flex-col gap-3">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">Retention Duration:</span>
              <span className="font-mono font-bold text-base text-emerald-600 dark:text-emerald-400">
                {sliderDays} Days (~{Math.round(sliderDays / 30)} months)
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={3650}
              value={sliderDays}
              onChange={(e) => setSliderDays(Number(e.target.value))}
              className="w-full accent-emerald-600 cursor-pointer"
            />
          </div>

          <div className="flex items-center gap-3 pt-3 border-t border-zinc-100 dark:border-zinc-800">
            {userRole === "admin" && (
              <>
                <button
                  type="button"
                  onClick={handleSaveRetention}
                  disabled={isSavingRetention}
                  className="px-4 py-2 bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 rounded-lg text-xs font-semibold hover:opacity-90 disabled:opacity-50"
                >
                  Save Policy
                </button>
                <button
                  type="button"
                  onClick={handleRunSweep}
                  disabled={isSweeping}
                  className="px-4 py-2 border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg text-xs font-semibold disabled:opacity-50"
                >
                  Run Retention Sweep Now
                </button>
              </>
            )}
          </div>
        </section>
      )}

      {/* Tab 5: Webhooks */}
      {activeTab === "webhooks" && (
        <section className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex flex-col gap-6 shadow-xs max-w-2xl">
          <div className="flex flex-col gap-1">
            <h3 className="font-bold text-sm text-zinc-900 dark:text-zinc-100">
              Approved Document Webhook Dispatcher
            </h3>
            <p className="text-xs text-zinc-500 leading-relaxed">
              When documents are approved, signed payloads (HMAC-SHA256 via <code>WEBHOOK_SIGNING_SECRET</code>) are dispatched to notify your downstream KYC core.
            </p>
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-xs font-semibold text-zinc-500">Webhook Target URL</label>
            <input
              type="text"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              className="px-3 py-2 text-xs border border-zinc-200 dark:border-zinc-800 rounded-lg bg-zinc-50 dark:bg-zinc-950 font-mono outline-hidden"
            />
          </div>

          <div className="flex items-center gap-3">
            {userRole === "admin" && (
              <button
                type="button"
                onClick={handleSaveWebhook}
                disabled={isSavingWebhook}
                className="px-4 py-2 bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 rounded-lg text-xs font-semibold hover:opacity-90 disabled:opacity-50"
              >
                Save Webhook URL
              </button>
            )}
            <button
              type="button"
              onClick={handleTestWebhook}
              disabled={isTestingWebhook}
              className="px-4 py-2 border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg text-xs font-semibold hover:opacity-90 disabled:opacity-50 flex items-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Test Webhook Dispatch</span>
            </button>
          </div>

          {webhookResult && (
            <div className="p-3 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-xs font-mono">
              <span className="font-bold text-zinc-700 dark:text-zinc-300 block mb-1">
                Dispatch Result:
              </span>
              <pre className="text-[11px] text-zinc-600 dark:text-zinc-400 overflow-x-auto">
                {JSON.stringify(webhookResult, null, 2)}
              </pre>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
