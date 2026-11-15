"use client";

import React, { useState, useRef, useEffect } from "react";
import { useApp } from "@/context/AppContext";
import { api, RAGResponse, RAGCitationItem } from "@/lib/api";
import {
  Bot,
  Sparkles,
  Send,
  X,
  ShieldCheck,
  AlertTriangle,
  RotateCcw,
  CheckCircle2,
} from "lucide-react";

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  textEn: string;
  textAr?: string;
  citations?: RAGCitationItem[];
  confidence?: number;
  promptGuardFlagged?: boolean;
  timestamp: string;
}

export function SovereignChatbot() {
  const { language, activeTenant, selectedDocument } = useApp();

  const [isOpen, setIsOpen] = useState(false);
  const [inputQuery, setInputQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [targetScope, setTargetScope] = useState<"document" | "tenant">("document");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome-1",
      sender: "assistant",
      textEn: "Sovereign DocIntel AI online. Running on-premise in UAE with zero external data egress. Ask questions regarding extracted document fields, validity dates, or regulatory compliance.",
      textAr: "المساعد الذكي السيادي متصل محلياً داخل الدولة بدون أي خروج للبيانات. تفضل بالسؤال عن حقول المستندات، تواريخ الصلاحية، أو معايير الامتثال.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    const handleOpen = () => setIsOpen(true);
    window.addEventListener("open-sovereign-chatbot", handleOpen);
    return () => window.removeEventListener("open-sovereign-chatbot", handleOpen);
  }, []);

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const samplePrompts = [
    {
      en: "What is the Emirates ID number and expiry date?",
      ar: "ما هو رقم الهوية وتاريخ الانتهاء؟",
    },
    {
      en: "Is the Trade License valid or expired?",
      ar: "هل الرخصة التجارية سارية أم منتهية الصلاحية؟",
    },
    {
      en: "What is the TRN and total VAT amount?",
      ar: "ما هو الرقم الضريبي ومبلغ ضريبة القيمة المضافة؟",
    },
  ];

  const handleSendMessage = async (queryText?: string) => {
    const q = (queryText || inputQuery).trim();
    if (!q || isLoading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      textEn: q,
      textAr: q,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery("");
    setIsLoading(true);

    try {
      const docId = targetScope === "document" && selectedDocument ? selectedDocument.id : undefined;
      const response: RAGResponse = await api.rag.query(q, docId, 5);

      const botMsg: ChatMessage = {
        id: `bot-${Date.now()}`,
        sender: "assistant",
        textEn: response.answer || "No response received.",
        textAr: response.answer_ar || response.answer || "لم يتم استلام رد.",
        citations: response.citations || [],
        confidence: response.confidence,
        promptGuardFlagged: response.prompt_guard_flagged,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `bot-err-${Date.now()}`,
        sender: "assistant",
        textEn: `Failed to retrieve answer from sovereign RAG: ${err?.message || "Internal RAG error"}`,
        textAr: `تعذر استرجاع الإجابة من نموذج البحث المحلي: ${err?.message || "خطأ داخلي"}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <>
      {/* Floating Launcher Button (Linear / Raycast Style) */}
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="fixed bottom-5 end-5 z-50 flex items-center gap-2 px-3.5 py-2.5 rounded-full bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 border border-zinc-700/80 shadow-xl hover:scale-[1.02] active:scale-95 transition-all text-xs font-semibold group"
        aria-label="Open Sovereign AI Chatbot"
      >
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
        </span>
        <Sparkles className="w-3.5 h-3.5 text-emerald-400 dark:text-emerald-600 group-hover:rotate-12 transition-transform" />
        <span className="hidden sm:inline">
          {language === "ar" ? "المساعد السيادي" : "Sovereign AI"}
        </span>
      </button>

      {/* Slide-over Drawer (Studio Dark Glass) */}
      {isOpen && (
        <div className="fixed bottom-18 end-4 sm:end-6 z-50 w-[94vw] sm:w-[440px] h-[580px] max-h-[82vh] bg-zinc-950 text-zinc-100 border border-zinc-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-150">
          {/* Header */}
          <div className="p-3.5 bg-zinc-900/90 border-b border-zinc-800 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center">
                <Bot className="w-4 h-4 text-emerald-400" />
              </div>
              <div>
                <div className="font-semibold text-xs flex items-center gap-1.5">
                  <span>{language === "ar" ? "المساعد الذكي السيادي" : "Sovereign RAG AI"}</span>
                  <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                    AIR-GAPPED
                  </span>
                </div>
                <div className="text-[10px] text-zinc-400 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-emerald-500" />
                  <span>{activeTenant?.nameEn || "UAE In-Country Node"}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={() =>
                  setMessages([
                    {
                      id: `welcome-${Date.now()}`,
                      sender: "assistant",
                      textEn: "Conversation reset. Ready for your document intelligence queries.",
                      textAr: "تمت إعادة تعيين المحادثة. جاهز للإجابة عن أسئلتك.",
                      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                    },
                  ])
                }
                title="Reset conversation"
                className="p-1 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                title="Close assistant"
                className="p-1 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Scope Segmented Control */}
          <div className="px-3 py-1.5 bg-zinc-900/40 border-b border-zinc-800/80 flex items-center justify-between text-[11px]">
            <span className="text-zinc-400 font-medium">Scope:</span>
            <div className="flex items-center gap-1 bg-zinc-900 p-0.5 rounded-lg border border-zinc-800">
              <button
                onClick={() => setTargetScope("document")}
                className={`px-2 py-0.5 rounded-md text-[10px] font-medium transition ${
                  targetScope === "document"
                    ? "bg-zinc-800 text-zinc-100 shadow-xs font-semibold"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {selectedDocument
                  ? `Active (${selectedDocument.referenceNumber})`
                  : "Active Document"}
              </button>
              <button
                onClick={() => setTargetScope("tenant")}
                className={`px-2 py-0.5 rounded-md text-[10px] font-medium transition ${
                  targetScope === "tenant"
                    ? "bg-zinc-800 text-zinc-100 shadow-xs font-semibold"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                All Documents
              </button>
            </div>
          </div>

          {/* Messages Feed */}
          <div className="flex-1 overflow-y-auto p-3.5 space-y-3 text-xs">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex flex-col ${m.sender === "user" ? "items-end" : "items-start"}`}
              >
                <div
                  className={`max-w-[88%] rounded-xl p-3 space-y-1.5 shadow-xs ${
                    m.sender === "user"
                      ? "bg-zinc-800 text-zinc-100 border border-zinc-700/80"
                      : "bg-zinc-900/90 text-zinc-200 border border-zinc-800"
                  }`}
                >
                  <div className="leading-relaxed">
                    {language === "ar" ? m.textAr || m.textEn : m.textEn}
                  </div>

                  {/* Prompt Guard Alert */}
                  {m.promptGuardFlagged && (
                    <div className="flex items-center gap-1.5 p-1.5 rounded bg-rose-950/40 border border-rose-800/60 text-rose-300 text-[10px]">
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                      <span>Security: Suspicious prompt injection neutralized</span>
                    </div>
                  )}

                  {/* Verified Citations */}
                  {m.citations && m.citations.length > 0 && (
                    <div className="pt-2 border-t border-zinc-800 space-y-1">
                      <div className="text-[10px] font-medium text-zinc-400 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                        <span>Verified Citations ({m.citations.length})</span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {m.citations.map((c, idx) => (
                          <div
                            key={c.chunk_id || idx}
                            className="px-1.5 py-0.5 rounded bg-zinc-950 border border-zinc-800 text-[10px] text-zinc-300 font-mono flex items-center gap-1"
                            title={c.snippet}
                          >
                            <span className="text-emerald-400 font-semibold">P.{c.page}</span>
                            <span className="text-zinc-400 truncate max-w-[120px]">
                              {c.snippet.substring(0, 24)}...
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Timestamp & Confidence */}
                  {m.confidence !== undefined && m.confidence > 0 && (
                    <div className="text-[9px] text-zinc-500 font-mono flex items-center justify-between pt-1">
                      <span>RAG: {Math.round(m.confidence * 100)}%</span>
                      <span>{m.timestamp}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex items-center gap-2 p-2.5 bg-zinc-900 rounded-xl border border-zinc-800 text-xs text-zinc-400 w-fit animate-pulse">
                <Sparkles className="w-3.5 h-3.5 text-emerald-400 animate-spin" />
                <span>
                  {language === "ar" ? "جاري استرجاع البيانات السيادية..." : "Retrieving local sovereign chunks..."}
                </span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts */}
          {messages.length <= 2 && (
            <div className="px-3 py-1.5 bg-zinc-900/30 border-t border-zinc-800/80 flex flex-wrap gap-1">
              {samplePrompts.slice(0, 2).map((sp, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(language === "ar" ? sp.ar : sp.en)}
                  className="px-2 py-0.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[10px] text-zinc-400 hover:text-zinc-200 truncate transition"
                >
                  {language === "ar" ? sp.ar : sp.en}
                </button>
              ))}
            </div>
          )}

          {/* Input Bar */}
          <div className="p-3 bg-zinc-900/80 border-t border-zinc-800 flex items-center gap-2">
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              placeholder={
                language === "ar"
                  ? "اسأل المساعد عن أي حقل أو تاريخ صلاحية..."
                  : "Ask about fields, validity, TRN..."
              }
              className="flex-1 px-3 py-1.5 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder:text-zinc-500 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500 disabled:opacity-50"
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={!inputQuery.trim() || isLoading}
              className="p-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 disabled:opacity-30 transition shadow-xs"
              aria-label="Send query"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
