"use client";

import React from "react";
import { useApp } from "@/context/AppContext";
import { ArrowRight, CheckCircle2 } from "lucide-react";

export function LandingScreen() {
  const { setCurrentScreen } = useApp();

  return (
    <div className="flex flex-col bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-50 -m-4 sm:-m-6 lg:-m-8">
      {/* Hero Dark Container */}
      <section className="bg-zinc-950 text-white border-b border-zinc-800 relative overflow-hidden py-16 px-6 lg:px-12">
        {/* Subtle grid pattern */}
        <div
          className="absolute inset-0 opacity-10 pointer-events-none"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
            backgroundSize: "40px 40px",
          }}
        />

        <div className="max-w-5xl mx-auto flex flex-col items-center text-center gap-6 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-zinc-800 bg-zinc-900/80 text-xs text-zinc-300">
            <span className="w-2 h-2 rounded-full bg-zinc-100 animate-pulse" />
            <span>In-country document AI for UAE banks & fintechs</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight max-w-4xl leading-[1.08]">
            Verified KYC data from any UAE document.{" "}
            <span className="text-white">In seconds. In-country.</span>
          </h1>

          <p className="text-base sm:text-lg text-zinc-400 max-w-2xl leading-relaxed">
            DocIntel reads Arabic and English documents, checks them against sovereign compliance rules, and sends only the uncertain ones to a human reviewer. Every value comes with its exact source and confidence score.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <button
              onClick={() => setCurrentScreen("command")}
              className="px-6 py-3 rounded-xl bg-zinc-100 text-zinc-950 font-bold text-sm hover:bg-white transition shadow-lg shadow-black/20 flex items-center gap-2"
            >
              <span>Open Command Center</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentScreen("review")}
              className="px-6 py-3 rounded-xl border border-zinc-800 bg-zinc-900 text-zinc-200 font-semibold text-sm hover:bg-zinc-800 transition"
            >
              Test Human Review Workspace
            </button>
          </div>

          <span className="text-xs text-zinc-500 font-medium">
            Runs 100% in UAE cloud region or on-prem · Zero foreign data egress
          </span>

          {/* Interactive Document Preview Box (Matching v2/Landing.dc.html) */}
          <div className="w-full max-w-4xl mt-8 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-2 shadow-2xl backdrop-blur-xs">
            <div className="rounded-xl bg-white dark:bg-zinc-900 p-6 text-zinc-900 dark:text-zinc-100 flex flex-col md:flex-row gap-6 items-center">
              {/* Simulated Card */}
              <div className="flex-1 w-full max-w-sm aspect-[1.586] rounded-xl border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-950 p-4 relative text-xs flex flex-col justify-between overflow-hidden shadow-md">
                <div className="flex items-center justify-between text-[10px] font-bold text-zinc-500 border-b border-zinc-200 dark:border-zinc-800 pb-1">
                  <span>IDENTITY CARD</span>
                  <span>بطاقة هوية</span>
                </div>
                <div className="flex gap-3 items-center">
                  <div className="w-14 h-16 bg-zinc-200 dark:bg-zinc-800 rounded flex items-center justify-center text-[10px] text-zinc-400">
                    Photo
                  </div>
                  <div className="flex flex-col gap-1 flex-1">
                    <span className="font-bold text-xs p-1 rounded border border-zinc-300 dark:border-zinc-700 bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100">
                      784-1990-1234567-1
                    </span>
                    <span className="font-semibold text-xs text-zinc-800 dark:text-zinc-200">
                      Sara Ahmed Example
                    </span>
                    <span className="text-[10px] text-zinc-400">EXP: 2031-02-03</span>
                  </div>
                </div>
                <div className="flex justify-between text-[9px] text-zinc-400">
                  <span>UAE RESIDENT</span>
                  <span className="text-zinc-900 dark:text-zinc-100 font-bold">100% Sovereign Ingest</span>
                </div>
              </div>

              {/* Extraction Summary */}
              <div className="flex-1 w-full flex flex-col gap-3 text-start">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm">Emirates ID · Extracted</span>
                  <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100 bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 rounded-full border border-zinc-200 dark:border-zinc-700">
                    1.8s P95
                  </span>
                </div>

                <div className="space-y-1.5 text-xs">
                  <div className="p-2 rounded-lg border border-zinc-200 dark:border-zinc-800 flex justify-between">
                    <span className="text-zinc-500">ID Number</span>
                    <span className="font-bold">784-1990-1234567-1 <span className="text-zinc-900 dark:text-zinc-100 font-bold">99%</span></span>
                  </div>
                  <div className="p-2 rounded-lg border border-zinc-200 dark:border-zinc-800 flex justify-between">
                    <span className="text-zinc-500">Full Name</span>
                    <span className="font-semibold">Sara Ahmed Example <span className="text-zinc-900 dark:text-zinc-100 font-bold">97%</span></span>
                  </div>
                  <div className="p-2 rounded-lg border border-zinc-200 dark:border-zinc-800 flex justify-between">
                    <span className="text-zinc-500">Expiry Date</span>
                    <span className="font-semibold">2031-02-03 <span className="text-amber-600">74%</span></span>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs font-medium text-zinc-900 dark:text-zinc-100 pt-1">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>Check digit valid · Not expired · ISO format passed</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Pillars Section */}
      <section className="py-16 px-6 lg:px-12 max-w-5xl mx-auto flex flex-col gap-10">
        <div className="flex flex-col gap-2">
          <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider">
            Architecture Pillars
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Built from day one for UAE sovereign compliance.
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex flex-col gap-3 shadow-xs">
            <span className="text-xs text-zinc-400 font-semibold">01 · READ</span>
            <h3 className="font-bold text-base">Arabic and English, together</h3>
            <p className="text-xs text-zinc-500 leading-relaxed">
              Deskews camera photos, auto-detects document types, and reads both Arabic cursive and English scripts on the same page.
            </p>
          </div>

          <div className="p-6 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex flex-col gap-3 shadow-xs">
            <span className="text-xs text-zinc-400 font-semibold">02 · VERIFY</span>
            <h3 className="font-bold text-base">Checks a compliance officer would</h3>
            <p className="text-xs text-zinc-500 leading-relaxed">
              Enforces UAE Luhn check digits, TRN format (15 digits starting with 100), expiration dates, and sanctions name screening.
            </p>
          </div>

          <div className="p-6 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex flex-col gap-3 shadow-xs">
            <span className="text-xs text-zinc-400 font-semibold">03 · SOVEREIGN</span>
            <h3 className="font-bold text-base">Zero foreign egress boundary</h3>
            <p className="text-xs text-zinc-500 leading-relaxed">
              Fully compliant with Federal Decree-Law No. 45/2021. Operates entirely in UAE cloud regions or air-gapped on-premise clusters.
            </p>
          </div>
        </div>

        <div className="p-8 rounded-2xl bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex flex-col sm:flex-row items-center justify-between gap-6 text-center sm:text-start">
          <div>
            <h3 className="text-lg font-bold">Ready to see DocIntel in action?</h3>
            <p className="text-xs text-zinc-500 mt-1">Jump into the live platform workspace now.</p>
          </div>
          <button
            onClick={() => setCurrentScreen("command")}
            className="px-5 py-2.5 rounded-xl bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 font-bold text-xs hover:opacity-90 transition shrink-0"
          >
            Enter Platform
          </button>
        </div>
      </section>
    </div>
  );
}
