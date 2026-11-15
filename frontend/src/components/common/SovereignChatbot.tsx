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
  FileText,
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
      textEn: "Welcome to Sanad Sovereign DocIntel AI. I am your in-country, air-gapped document intelligence assistant. Ask questions about your extracted UAE documents, compliance rules, or validation statuses.",
      textAr: "مرحباً بك في المساعد الذكي السيادي لمنصة سند. أنا مساعدك المحلي للذكاء المستندي بدون أي تصدير خارجي. اسأل عن مستنداتك الإماراتية، قواعد الامتثال، أو نتائج التحقق.",
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
    {
      en: "Check compliance with Federal Decree-Law No. 45/2021",
      ar: "تحقق من الامتثال للمرسوم بقانون اتحادي رقم 45 لسنة 2021",
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
      {/* Floating Launcher Button */}
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="fixed bottom-6 end-6 z-50 flex items-center gap-2.5 px-4 py-3 rounded-full bg-emerald-700 hover:bg-emerald-600 active:scale-95 text-white font-bold text-xs shadow-2xl shadow-emerald-950/40 border border-emerald-500/40 transition-all duration-200 group"
        aria-label="Open Sovereign AI Chatbot"
      >
        <span className="relative flex h-3 w-3">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-300"></span>
        </span>
        <Bot className="w-5 h-5 text-emerald-100 group-hover:rotate-12 transition-transform" />
        <span className="hidden sm:inline">
          {language === "ar" ? "المساعد السيادي (RAG AI)" : "Sovereign AI Assistant"}
        </span>
      </button>

      {/* Slide-over Drawer / Chatbot Window */}
      {isOpen && (
        <div className="fixed bottom-20 end-4 sm:end-6 z-50 w-[94vw] sm:w-[460px] h-[620px] max-h-[85vh] bg-card border border-border rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom-6 duration-200">
          {/* Header */}
          <div className="p-4 bg-emerald-950 text-white border-b border-emerald-800 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-emerald-800/80 border border-emerald-700 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-emerald-300" />
              </div>
              <div>
                <div className="font-extrabold text-xs flex items-center gap-1.5">
                  <span>{language === "ar" ? "المساعد الذكي السيادي" : "Sovereign RAG Assistant"}</span>
                  <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-800 text-emerald-200 border border-emerald-700">
                    AIR-GAPPED
                  </span>
                </div>
                <div className="text-[10px] text-emerald-300/80 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-emerald-400" />
                  <span>{activeTenant?.nameEn || "UAE In-Country Cloud"}</span>
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
                      textEn: "Chat cleared. Ask anything about your UAE documents.",
                      textAr: "تمت إعادة تعيين المحادثة. تفضل بالسؤال عن مستنداتك.",
                      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                    },
                  ])
                }
                title="Reset conversation"
                className="p-1.5 rounded-lg text-emerald-300 hover:text-white hover:bg-emerald-900 transition"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                title="Close chatbot"
                className="p-1.5 rounded-lg text-emerald-300 hover:text-white hover:bg-emerald-900 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Scope Selector Bar */}
          <div className="px-3 py-2 bg-secondary/40 border-b border-border flex items-center justify-between text-[11px]">
            <div className="flex items-center gap-1.5 text-muted-foreground font-semibold">
              <FileText className="w-3.5 h-3.5" />
              <span>Scope:</span>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setTargetScope("document")}
                className={`px-2 py-0.5 rounded text-[10px] font-bold transition ${
                  targetScope === "document"
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {selectedDocument
                  ? `Active (${selectedDocument.referenceNumber})`
                  : "Active Document"}
              </button>
              <button
                onClick={() => setTargetScope("tenant")}
                className={`px-2 py-0.5 rounded text-[10px] font-bold transition ${
                  targetScope === "tenant"
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                All Tenant Documents
              </button>
            </div>
          </div>

          {/* Messages Viewport */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3.5 text-xs">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex flex-col ${m.sender === "user" ? "items-end" : "items-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl p-3 shadow-xs space-y-1.5 ${
                    m.sender === "user"
                      ? "bg-emerald-700 text-white rounded-br-none"
                      : "bg-secondary/70 border border-border text-foreground rounded-bl-none"
                  }`}
                >
                  {/* Bilingual Answer */}
                  <div className="leading-relaxed">
                    {language === "ar" ? m.textAr || m.textEn : m.textEn}
                  </div>

                  {/* Prompt Guard Neutralization Warning */}
                  {m.promptGuardFlagged && (
                    <div className="flex items-center gap-1.5 p-1.5 rounded-lg bg-rose-950/30 border border-rose-800 text-rose-300 text-[10px] font-semibold">
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                      <span>Sovereign Guard: Suspicious prompt injection sanitized</span>
                    </div>
                  )}

                  {/* Citations & Evidence Chips */}
                  {m.citations && m.citations.length > 0 && (
                    <div className="pt-2 border-t border-border/50 space-y-1.5">
                      <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                        <span>Verified Citations ({m.citations.length})</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {m.citations.map((c, idx) => (
                          <div
                            key={c.chunk_id || idx}
                            className="px-2 py-1 rounded-md bg-card border border-border text-[10px] text-foreground font-mono flex items-center gap-1"
                            title={c.snippet}
                          >
                            <span className="text-emerald-500 font-bold">P.{c.page}</span>
                            <span className="text-muted-foreground truncate max-w-[130px]">
                              {c.snippet.substring(0, 30)}...
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Confidence Badge */}
                  {m.confidence !== undefined && m.confidence > 0 && (
                    <div className="text-[9px] text-muted-foreground font-mono flex items-center justify-between pt-1">
                      <span>RAG Confidence: {Math.round(m.confidence * 100)}%</span>
                      <span>{m.timestamp}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex items-center gap-2 p-3 bg-secondary/50 rounded-2xl border border-border text-xs text-muted-foreground w-fit animate-pulse">
                <Sparkles className="w-4 h-4 text-emerald-500 animate-spin" />
                <span>
                  {language === "ar"
                    ? "جاري البحث في المستندات المحلية والتحقق من السياق..."
                    : "Retrieving sovereign chunks and synthesizing answer..."}
                </span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Suggested Sample Queries */}
          {messages.length <= 2 && (
            <div className="px-3 py-2 bg-secondary/30 border-t border-border/50 flex flex-wrap gap-1">
              {samplePrompts.slice(0, 2).map((sp, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(language === "ar" ? sp.ar : sp.en)}
                  className="px-2.5 py-1 rounded-lg bg-card hover:bg-secondary border border-border text-[10px] text-muted-foreground hover:text-foreground truncate transition"
                >
                  {language === "ar" ? sp.ar : sp.en}
                </button>
              ))}
            </div>
          )}

          {/* Input Bar */}
          <div className="p-3 bg-card border-t border-border flex items-center gap-2">
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              placeholder={
                language === "ar"
                  ? "اسأل المساعد الذكي عن أي معلومة في المستند..."
                  : "Ask sovereign AI about document fields, expiry, TRN..."
              }
              className="flex-1 px-3 py-2 rounded-xl bg-secondary/50 border border-border text-foreground placeholder:text-muted-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={!inputQuery.trim() || isLoading}
              className="p-2.5 rounded-xl bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 text-white shadow-sm transition active:scale-95"
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
