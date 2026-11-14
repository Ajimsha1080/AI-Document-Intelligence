import React, { useState, useRef } from "react";
import { useApp } from "@/context/AppContext";
import { DocumentTypeCode, DocumentItem } from "@/types";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ConfidenceBadge } from "@/components/common/ConfidenceBadge";
import {
  UploadCloud,
  FileCheck,
  File,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  X,
} from "lucide-react";

interface UploadingFile {
  id: string;
  name: string;
  sizeKB: number;
  progress: number;
  status: "preprocessing" | "ocr" | "done" | "error";
  type: DocumentTypeCode | "auto";
  detectedType?: DocumentTypeCode;
}

export function UploadZone() {
  const {
    addDocument,
    documents,
    setSelectedDocumentId,
    setCurrentScreen,
    language,
    dir,
    t,
  } = useApp();

  const [isDragging, setIsDragging] = useState(false);
  const [selectedType, setSelectedType] = useState<DocumentTypeCode | "auto">("auto");
  const [queue, setQueue] = useState<UploadingFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const Arrow = dir === "rtl" ? ArrowLeft : ArrowRight;

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const processFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const newFiles: UploadingFile[] = Array.from(files).map((f) => ({
      id: Math.random().toString(36).substring(2, 9),
      name: f.name,
      sizeKB: Math.round(f.size / 1024),
      progress: 10,
      status: "preprocessing",
      type: selectedType,
    }));

    setQueue((prev) => [...newFiles, ...prev]);

    // Simulate async pipeline stages
    newFiles.forEach((item) => {
      let prog = 10;
      const interval = setInterval(() => {
        prog += 25;
        if (prog < 70) {
          setQueue((q) =>
            q.map((f) =>
              f.id === item.id ? { ...f, progress: prog, status: "preprocessing" } : f
            )
          );
        } else if (prog < 100) {
          setQueue((q) =>
            q.map((f) =>
              f.id === item.id ? { ...f, progress: prog, status: "ocr" } : f
            )
          );
        } else {
          clearInterval(interval);

          // Infer type if auto
          const lower = item.name.toLowerCase();
          let docType: DocumentTypeCode = "emirates_id";
          let docNameEn = "UAE Identity Card (Emirates ID)";
          let docNameAr = "بطاقة الهوية الإماراتية";

          if (item.type !== "auto") {
            docType = item.type;
          } else if (lower.includes("trade") || lower.includes("license") || lower.includes("ded")) {
            docType = "uae_trade_license";
            docNameEn = "UAE Commercial Trade License";
            docNameAr = "رخصة تجارية في دولة الإمارات";
          } else if (lower.includes("invoice") || lower.includes("tax") || lower.includes("vat")) {
            docType = "commercial_invoice";
            docNameEn = "Commercial Tax Invoice (VAT)";
            docNameAr = "فاتورة ضريبية تجارية";
          }

          const newDoc: DocumentItem = {
            id: `doc-${Date.now()}`,
            referenceNumber: `DOC-${Math.floor(1000 + Math.random() * 9000)}`,
            fileName: item.name,
            documentType: docType,
            documentTypeNameEn: docNameEn,
            documentTypeNameAr: docNameAr,
            status: "needs_review",
            overallConfidence: 0.94,
            uploadedAt: new Date().toISOString(),
            processedAt: new Date().toISOString(),
            fileSizeKB: item.sizeKB,
            pageCount: 1,
            extractedLanguage: "mixed",
            previewUrl: docType,
            validationErrors: [],
            fields: [
              {
                id: `f-${Date.now()}-1`,
                key: "reference_id",
                nameEn: "Extracted Reference",
                nameAr: "الرقم المرجعي المستخرج",
                value: `784-2026-${Math.floor(1000000 + Math.random() * 9000000)}-1`,
                originalValue: `784-2026-${Math.floor(1000000 + Math.random() * 9000000)}-1`,
                confidence: 0.98,
                section: "identity",
                page: 1,
              },
              {
                id: `f-${Date.now()}-2`,
                key: "entity_name",
                nameEn: "Entity / Holder Name",
                nameAr: "اسم الجهة / صاحب المستند",
                value: "شركة الخليج للحلول الرقمية ذ.م.م",
                originalValue: "شركة الخليج للحلول الرقمية ذ.م.م",
                confidence: 0.95,
                section: "company",
                page: 1,
              },
            ],
          };

          addDocument(newDoc);

          setQueue((q) =>
            q.map((f) =>
              f.id === item.id
                ? { ...f, progress: 100, status: "done", detectedType: docType }
                : f
            )
          );
        }
      }, 500);
    });
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    processFiles(e.dataTransfer.files);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    processFiles(e.target.files);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="space-y-6">
      {/* Upload Controls Box */}
      <div className="p-6 rounded-2xl border border-border bg-card shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-foreground">
              {language === "ar" ? "تحميل المستندات ومعالجتها محلياً" : "Document Ingestion & Sovereign Processing"}
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {language === "ar"
                ? "يدعم صيغ PDF، PNG، JPG، TIFF، DOCX مع فك الميلان وإزالة الضوضاء تلقائياً"
                : "Accepts PDF, PNG, JPG, TIFF, DOCX with automatic deskew, denoise, and orientation fix"}
            </p>
          </div>

          {/* Document Type Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-muted-foreground">
              {language === "ar" ? "نوع المستند:" : "Doc Type:"}
            </span>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value as any)}
              className="px-3 py-1.5 rounded-lg border border-border bg-secondary text-foreground text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="auto">✨ Auto-Detect (كشف آلي)</option>
              <option value="emirates_id">Emirates ID (الهوية الإماراتية)</option>
              <option value="uae_trade_license">UAE Trade License (رخصة تجارية)</option>
              <option value="commercial_invoice">Commercial Tax Invoice (فاتورة ضريبية)</option>
            </select>
          </div>
        </div>

        {/* Dropzone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-xl p-8 sm:p-12 text-center cursor-pointer transition-all flex flex-col items-center justify-center gap-3 ${
            isDragging
              ? "border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/20"
              : "border-border hover:border-emerald-600/70 hover:bg-secondary/40"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.png,.jpg,.jpeg,.tiff,.docx"
            onChange={handleFileChange}
            className="hidden"
          />

          <div className="w-14 h-14 rounded-full bg-primary/10 text-primary flex items-center justify-center shadow-inner">
            <UploadCloud className="w-7 h-7" />
          </div>

          <div className="space-y-1">
            <div className="text-sm font-bold text-foreground">
              {language === "ar"
                ? "اسحب الملفات وأفلتها هنا، أو اضغط للاختيار من جهازك"
                : "Drag & drop files here, or browse your local files"}
            </div>
            <div className="text-xs text-muted-foreground">
              PDF, PNG, JPG, TIFF, DOCX • {language === "ar" ? "حجم أقصى ٥٠ ميجابايت" : "Up to 50MB per file"}
            </div>
          </div>

          <button
            type="button"
            className="mt-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-bold hover:bg-primary/90 shadow-sm transition"
          >
            {language === "ar" ? "اختر الملفات" : "Select Documents"}
          </button>
        </div>
      </div>

      {/* Upload Processing Queue */}
      {queue.length > 0 && (
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 text-primary animate-spin" />
              <h3 className="text-xs font-bold text-foreground">
                {language === "ar" ? "طابور المعالجة الآلية الحالي" : "Active Ingestion Pipeline"}
              </h3>
            </div>
            <button
              onClick={() => setQueue([])}
              className="text-[11px] text-muted-foreground hover:text-foreground"
            >
              Clear Queue
            </button>
          </div>

          <div className="space-y-2.5">
            {queue.map((item) => (
              <div
                key={item.id}
                className="p-3 rounded-lg border border-border bg-secondary/30 space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <File className="w-4 h-4 text-primary shrink-0" />
                    <span className="font-semibold text-foreground truncate">{item.name}</span>
                    <span className="text-[10px] text-muted-foreground font-mono">({item.sizeKB} KB)</span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {item.status === "done" ? (
                      <span className="flex items-center gap-1 text-emerald-700 dark:text-emerald-400 font-bold text-xs">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Ready</span>
                      </span>
                    ) : (
                      <span className="text-[11px] text-muted-foreground font-medium flex items-center gap-1">
                        <Sparkles className="w-3 h-3 text-amber-500 animate-pulse" />
                        <span>{item.status === "preprocessing" ? "Preprocessing (Deskew)" : "Sovereign OCR & Layout"}</span>
                      </span>
                    )}
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="w-full h-1.5 rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${item.progress}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Uploads Table */}
      <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-border">
          <h3 className="text-xs font-bold text-foreground uppercase tracking-wider">
            {language === "ar" ? "أحدث المستندات المستلمة" : "Recent Ingested Documents"}
          </h3>
          <button
            onClick={() => setCurrentScreen("documents")}
            className="text-xs font-bold text-primary hover:underline flex items-center gap-1"
          >
            <span>{language === "ar" ? "عرض الأرشيف الكامل" : "View Full Archive"}</span>
            <Arrow className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="divide-y divide-border/60">
          {documents.slice(0, 4).map((doc) => (
            <div
              key={doc.id}
              className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                  <FileCheck className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="font-bold text-foreground truncate">{doc.fileName}</div>
                  <div className="text-[11px] text-muted-foreground">
                    {language === "ar" ? doc.documentTypeNameAr : doc.documentTypeNameEn} • {doc.referenceNumber}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <ConfidenceBadge score={doc.overallConfidence} showLabel={false} />
                <StatusBadge status={doc.status} />

                <button
                  onClick={() => {
                    setSelectedDocumentId(doc.id);
                    setCurrentScreen("review");
                  }}
                  className="px-3 py-1 rounded-md bg-secondary hover:bg-primary hover:text-primary-foreground font-semibold text-foreground transition text-xs flex items-center gap-1"
                >
                  <span>{language === "ar" ? "مراجعة" : "Review"}</span>
                  <Arrow className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
