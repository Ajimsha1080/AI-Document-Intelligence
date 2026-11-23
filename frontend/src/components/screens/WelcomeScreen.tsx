"use client";

import React from "react";
import { useApp } from "@/context/AppContext";
import { ArrowRight, Shield, Sparkles, UploadCloud } from "lucide-react";

export function WelcomeScreen() {
  const { setCurrentScreen, setIsUploadModalOpen } = useApp();

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-8 py-4">
      {/* Hero Welcome Header */}
      <div className="flex flex-col gap-2">
        <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider">
          Onboarding & Quickstart
        </span>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          Getting started with DocIntel
        </h1>
        <p className="text-sm text-zinc-500 max-w-2xl leading-relaxed">
          The sovereign Document Intelligence platform for UAE Banking, Trade, and Insurance. Follow the quickstart steps below to test extraction, human-in-the-loop review, and sovereign RAG.
        </p>
      </div>

      {/* 4-Step Checklist Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-900 flex flex-col gap-3 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-zinc-400">01 · INGEST</span>
            <span className="w-2 h-2 rounded-full bg-zinc-900 dark:bg-zinc-100" />
          </div>
          <h3 className="font-bold text-base text-zinc-900 dark:text-zinc-100">Upload a UAE Document</h3>
          <p className="text-xs text-zinc-500 leading-relaxed">
            Drag and drop an Emirates ID front scan, trade license, or commercial invoice. Ingestion runs auto-deskew, OSD orientation, and bilingual Arabic-English OCR.
          </p>
          <button
            type="button"
            onClick={() => setIsUploadModalOpen(true)}
            className="mt-auto py-2 px-3 rounded-lg bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 text-xs font-semibold hover:opacity-90 transition flex items-center justify-between"
          >
            <span>Upload Document</span>
            <UploadCloud className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="p-5 border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-900 flex flex-col gap-3 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-zinc-400">02 · REVIEW</span>
            <span className="w-2 h-2 rounded-full bg-amber-500" />
          </div>
          <h3 className="font-bold text-base text-zinc-900 dark:text-zinc-100">Inspect & Correct</h3>
          <p className="text-xs text-zinc-500 leading-relaxed">
            Test the human-in-the-loop review workspace. Review Luhn checksum validation warnings, accept one-click check digit fixes, and test approval rules.
          </p>
          <button
            type="button"
            onClick={() => setCurrentScreen("review")}
            className="mt-auto py-2 px-3 rounded-lg border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 text-xs font-semibold hover:bg-zinc-50 dark:hover:bg-zinc-800 transition flex items-center justify-between"
          >
            <span>Open Review Workspace</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="p-5 border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-900 flex flex-col gap-3 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-zinc-400">03 · QUERY</span>
            <span className="w-2 h-2 rounded-full bg-blue-500" />
          </div>
          <h3 className="font-bold text-base text-zinc-900 dark:text-zinc-100">Ask Documents (Sovereign RAG)</h3>
          <p className="text-xs text-zinc-500 leading-relaxed">
            Ask natural language questions across all approved tenant documents. Every claim is strictly grounded in verified chunks with zero external API calls.
          </p>
          <button
            type="button"
            onClick={() => setCurrentScreen("ask")}
            className="mt-auto py-2 px-3 rounded-lg border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 text-xs font-semibold hover:bg-zinc-50 dark:hover:bg-zinc-800 transition flex items-center justify-between"
          >
            <span>Open Ask Pro</span>
            <Sparkles className="w-3.5 h-3.5 text-zinc-900 dark:text-zinc-100" />
          </button>
        </div>

        <div className="p-5 border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-900 flex flex-col gap-3 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-zinc-400">04 · GOVERN</span>
            <span className="w-2 h-2 rounded-full bg-purple-500" />
          </div>
          <h3 className="font-bold text-base text-zinc-900 dark:text-zinc-100">Audit & Sovereign Retention</h3>
          <p className="text-xs text-zinc-500 leading-relaxed">
            Configure tenant-scoped retention policies (1–3650 days), trigger caller-tenant sweeps, unmask PII with immutable audit trails, and manage API keys.
          </p>
          <button
            type="button"
            onClick={() => setCurrentScreen("governance")}
            className="mt-auto py-2 px-3 rounded-lg border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 text-xs font-semibold hover:bg-zinc-50 dark:hover:bg-zinc-800 transition flex items-center justify-between"
          >
            <span>Configure Governance</span>
            <Shield className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Sovereign Air-Gap Guarantee Banner */}
      <div className="p-5 border border-zinc-200 dark:border-zinc-800 rounded-xl bg-zinc-100/60 dark:bg-zinc-900/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 flex items-center justify-center font-bold">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
              UAE Sovereign Data Guarantee (Federal Decree-Law No. 45/2021)
            </h4>
            <p className="text-[11px] text-zinc-600 dark:text-zinc-400">
              Zero outbound network egress. Local Tesseract OCR + local FastEmbed + local Ollama backend.
            </p>
          </div>
        </div>
        <span className="px-3 py-1 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 text-xs rounded-full border border-zinc-300 dark:border-zinc-700 font-semibold whitespace-nowrap">
          UAE North Sovereign Zone
        </span>
      </div>
    </div>
  );
}
