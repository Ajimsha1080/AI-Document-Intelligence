"use client";

import React, { useState, useEffect } from "react";
import { useApp, ToastNotification } from "@/context/AppContext";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { CommandCenterScreen } from "@/components/screens/CommandCenterScreen";
import { ReviewWorkspaceScreen } from "@/components/screens/ReviewWorkspaceScreen";
import { AskWorkspaceScreen } from "@/components/screens/AskWorkspaceScreen";
import { SchemasScreen } from "@/components/screens/SchemasScreen";
import { GovernanceScreen } from "@/components/screens/GovernanceScreen";
import { WelcomeScreen } from "@/components/screens/WelcomeScreen";
import { LandingScreen } from "@/components/screens/LandingScreen";
import { LoginModal } from "@/components/screens/LoginModal";
import { CommandPalette } from "@/components/common/CommandPalette";
import { UploadModal } from "@/components/common/UploadModal";
import { CheckCircle2, AlertCircle, Info } from "lucide-react";

export function Shell() {
  const {
    currentScreen,
    toasts,
    dismissToast,
    isAuthenticated,
    isUploadModalOpen,
    setIsUploadModalOpen,
    isCommandPaletteOpen,
    setIsCommandPaletteOpen,
  } = useApp();
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  // Logged-out users see only login
  if (!isAuthenticated) {
    return (
      <div className="flex h-screen w-screen bg-zinc-950 items-center justify-center p-4">
        <LoginModal isOpen={true} onClose={() => {}} />
      </div>
    );
  }

  // If user navigated to landing screen, render full landing page layout
  if (currentScreen === "landing") {
    return (
      <div className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-50 flex flex-col">
        <Header onOpenLoginModal={() => setIsLoginModalOpen(true)} />
        <main className="flex-1">
          <LandingScreen />
        </main>
      </div>
    );
  }

  // Screen Switcher
  const renderCurrentScreen = () => {
    switch (currentScreen) {
      case "command":
      case "dashboard":
      case "documents":
      case "upload":
        return <CommandCenterScreen />;
      case "review":
        return <ReviewWorkspaceScreen />;
      case "ask":
        return <AskWorkspaceScreen />;
      case "schemas":
      case "builder":
        return <SchemasScreen />;
      case "governance":
      case "audit":
      case "settings":
      case "team":
        return <GovernanceScreen />;
      case "welcome":
        return <WelcomeScreen />;
      default:
        return <CommandCenterScreen />;
    }
  };

  return (
    <div className="flex h-screen bg-[#FAFAFA] dark:bg-zinc-950 text-[#0A0A0A] dark:text-zinc-100 overflow-hidden font-sans">
      {/* Sidebar Navigation */}
      <Sidebar />

      {/* Main Content Viewport */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Sticky Header */}
        <Header onOpenLoginModal={() => setIsLoginModalOpen(true)} />

        {/* Dynamic Screen Viewport */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-[1560px] w-full mx-auto">{renderCurrentScreen()}</div>
        </main>
      </div>

      {/* ⌘K Command Palette Modal */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
      />

      {/* Login & User Profile Modal */}
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
      />

      {/* Live Toast Notifications */}
      {toasts.length > 0 && (
        <div className="fixed bottom-4 end-4 z-50 flex flex-col gap-2 max-w-sm pointer-events-none">
          {toasts.map((toast) => (
            <ToastItem key={toast.id} toast={toast} onDismiss={dismissToast} />
          ))}
        </div>
      )}
    </div>
  );
}

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: ToastNotification;
  onDismiss: (id: string) => void;
}) {
  const [isFading, setIsFading] = useState(false);

  useEffect(() => {
    // Shade / fade out starting after 2 seconds
    const fadeTimer = setTimeout(() => {
      setIsFading(true);
    }, 2000);

    // Completely dismiss after the 350ms smooth transition
    const dismissTimer = setTimeout(() => {
      onDismiss(toast.id);
    }, 2350);

    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(dismissTimer);
    };
  }, [toast.id, onDismiss]);

  return (
    <div
      onClick={() => onDismiss(toast.id)}
      className={`p-3.5 rounded-xl border shadow-2xl flex items-start gap-2.5 text-xs pointer-events-auto cursor-pointer transform transition-all duration-350 ease-out ${
        isFading
          ? "opacity-0 translate-y-2 scale-95 pointer-events-none"
          : "opacity-100 translate-y-0 scale-100 animate-in fade-in slide-in-from-bottom-2"
      } ${
        toast.type === "success"
          ? "bg-zinc-950 text-zinc-100 border-zinc-700"
          : toast.type === "error"
          ? "bg-rose-950 text-rose-100 border-rose-800"
          : "bg-zinc-900 text-zinc-100 border-zinc-700"
      }`}
    >
      {toast.type === "success" && (
        <CheckCircle2 className="w-4 h-4 text-zinc-100 shrink-0 mt-0.5" />
      )}
      {toast.type === "error" && (
        <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
      )}
      {toast.type === "info" && (
        <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
      )}
      <div className="flex-1 min-w-0">
        <p className="font-semibold leading-snug break-words">{toast.messageEn}</p>
        {toast.messageAr && (
          <p className="text-[11px] opacity-80 mt-0.5 font-normal leading-snug break-words">
            {toast.messageAr}
          </p>
        )}
      </div>
    </div>
  );
}
