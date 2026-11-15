"use client";

import React, { useState } from "react";
import { useApp } from "@/context/AppContext";
import { SystemUser } from "@/types";
import { UserPlus } from "lucide-react";

export function TeamScreen() {
  const { users, addUser, language, showToast } = useApp();

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<SystemUser["role"]>("reviewer");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSendInvite = (e: React.FormEvent) => {
    e.preventDefault();
    const email = inviteEmail.trim();
    if (!email) return;

    setIsSubmitting(true);
    // Derive name from email prefix
    const derivedName = email.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    addUser(derivedName, email, inviteRole);

    showToast(
      "success",
      `Invitation sent to ${email} as ${inviteRole}`,
      `تم إرسال دعوة الانضمام إلى ${email}`
    );

    setInviteEmail("");
    setIsSubmitting(false);
  };

  const getRoleLabel = (role: SystemUser["role"]) => {
    switch (role) {
      case "admin":
        return language === "ar" ? "مسؤول النظام" : "Administrator";
      case "reviewer":
        return language === "ar" ? "مراجع" : "Reviewer";
      case "viewer":
        return language === "ar" ? "مشاهد" : "Viewer";
      default:
        return role;
    }
  };

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Page Title Section matching reference */}
      <div className="space-y-1">
        <div className="text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">
          {language === "ar" ? "إدارة الوصول والصلاحيات" : "ACCESS CONTROL"}
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
          {language === "ar" ? "فريق العمل" : "Team"}
        </h1>
        <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed max-w-3xl">
          {language === "ar"
            ? "يدير المسؤولون المستندات والاعتمادات والدليل. يقوم المراجعون باستخراج البيانات وتصحيحها واعتمادها."
            : "Administrators manage documents, approvals and the directory. Reviewers extract, correct and approve."}
        </p>
      </div>

      {/* Two Column Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Members Card (7 cols) */}
        <div className="lg:col-span-7 bg-card border border-border/80 rounded-2xl p-6 shadow-xs">
          <div className="pb-4 border-b border-border/80">
            <h2 className="text-sm font-bold text-foreground">
              {language === "ar" ? "أعضاء الفريق" : "Members"}
            </h2>
          </div>

          <div className="divide-y divide-border/60">
            {users.map((user) => (
              <div
                key={user.id}
                className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
              >
                <div className="space-y-0.5 min-w-0">
                  <div className="font-semibold text-sm text-foreground">
                    {user.name}
                  </div>
                  <div className="text-xs text-muted-foreground font-mono truncate">
                    {user.email}
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <span className="px-3 py-1 rounded-full text-xs font-medium bg-secondary text-secondary-foreground border border-border/60 select-none">
                    {getRoleLabel(user.role)}
                  </span>
                  <span className="text-xs text-muted-foreground font-mono">
                    {user.lastLogin || "16 Nov 2026"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Invite a Colleague Card (5 cols) */}
        <div className="lg:col-span-5 bg-card border border-border/80 rounded-2xl p-6 shadow-xs space-y-4">
          <div className="space-y-1">
            <h2 className="text-sm font-bold text-foreground">
              {language === "ar" ? "دعوة زميل عمل" : "Invite a colleague"}
            </h2>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {language === "ar"
                ? "سيتلقون دعوة عبر البريد الإلكتروني للانضمام بالدور الذي تحدده."
                : "They receive an email invitation and join with the role you choose."}
            </p>
          </div>

          <form onSubmit={handleSendInvite} className="space-y-3.5 pt-1">
            <div>
              <input
                type="email"
                required
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="name@company.ae"
                className="w-full px-4 py-2.5 rounded-xl border border-border/80 bg-secondary/30 hover:bg-secondary/50 focus:bg-background text-foreground placeholder:text-muted-foreground/70 text-xs focus:outline-none focus:ring-1 focus:ring-primary transition"
              />
            </div>

            <div>
              <select
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value as any)}
                className="w-full px-4 py-2.5 rounded-xl border border-border/80 bg-secondary/30 hover:bg-secondary/50 focus:bg-background text-foreground text-xs font-medium focus:outline-none focus:ring-1 focus:ring-primary transition cursor-pointer"
              >
                <option value="reviewer">{language === "ar" ? "مراجع (Reviewer)" : "Reviewer"}</option>
                <option value="admin">{language === "ar" ? "مسؤول (Administrator)" : "Administrator"}</option>
                <option value="viewer">{language === "ar" ? "مشاهد (Viewer)" : "Viewer"}</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={isSubmitting || !inviteEmail.trim()}
              className="w-full py-2.5 px-4 rounded-xl bg-[#064e3b] hover:bg-[#065f46] active:scale-[0.98] disabled:opacity-50 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-xs transition"
            >
              <UserPlus className="w-4 h-4" />
              <span>{language === "ar" ? "إرسال الدعوة" : "Send invitation"}</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
