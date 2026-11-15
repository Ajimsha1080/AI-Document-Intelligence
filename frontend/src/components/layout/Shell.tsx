"use client";

import React, { useState } from "react";
import { useApp } from "@/context/AppContext";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { DashboardScreen } from "@/components/screens/DashboardScreen";
import { UploadZone } from "@/components/common/UploadZone";
import { DataTable } from "@/components/common/DataTable";
import { ReviewScreen } from "@/components/screens/ReviewScreen";
import { SchemaBuilderScreen } from "@/components/screens/SchemaBuilderScreen";
import { AuditLogScreen } from "@/components/screens/AuditLogScreen";
import { SettingsScreen } from "@/components/screens/SettingsScreen";
import { TeamScreen } from "@/components/screens/TeamScreen";
import { LoginModal } from "@/components/screens/LoginModal";
import { SovereignChatbot } from "@/components/common/SovereignChatbot";
import { CheckCircle2, AlertCircle, Info } from "lucide-react";

export function Shell() {
  const { currentScreen, toasts, dismissToast, language } = useApp();
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  // Screen Router
  const renderCurrentScreen = () => {
    switch (currentScreen) {
      case "dashboard":
        return <DashboardScreen />;
      case "upload":
        return <UploadZone />;
      case "documents":
        return <DataTable />;
      case "review":
        return <ReviewScreen />;
      case "builder":
        return <SchemaBuilderScreen />;
      case "audit":
        return <AuditLogScreen />;
      case "team":
        return <TeamScreen />;
      case "settings":
        return <SettingsScreen />;
      default:
        return <DashboardScreen />;
    }
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden text-foreground">
      {/* Sovereign Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Sticky Header with Profile Click to open LoginModal */}
        <Header onOpenLoginModal={() => setIsLoginModalOpen(true)} />

        {/* Dynamic Screen Viewport */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {renderCurrentScreen()}
          </div>
        </main>
      </div>

      {/* Login & SSO Modal */}
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
      />

      {/* Sovereign RAG AI Chatbot */}
      <SovereignChatbot />

      {/* Live Toast Notifications */}
      {toasts.length > 0 && (
        <div className="fixed bottom-4 end-4 z-50 flex flex-col gap-2 max-w-sm pointer-events-none">
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className={`p-3 rounded-xl border shadow-xl flex items-start gap-2.5 text-xs pointer-events-auto transition-all animate-fade-in ${
                toast.type === "success"
                  ? "bg-emerald-950 text-emerald-100 border-emerald-800"
                  : toast.type === "error"
                  ? "bg-rose-950 text-rose-100 border-rose-800"
                  : "bg-slate-900 text-slate-100 border-slate-700"
              }`}
            >
              {toast.type === "success" && <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />}
              {toast.type === "error" && <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />}
              {toast.type === "info" && <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />}

              <div className="flex-1 leading-snug">
                {language === "ar" ? toast.messageAr : toast.messageEn}
              </div>

              <button
                onClick={() => dismissToast(toast.id)}
                className="opacity-60 hover:opacity-100 text-sm font-bold"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
