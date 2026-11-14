import React, { useState, useRef } from "react";
import { useApp } from "@/context/AppContext";
import { DocumentTypeCode, DocumentItem } from "@/types";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ConfidenceBadge } from "@/components/common/ConfidenceBadge";
import { api } from "@/lib/api";
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
    dataMode,
    language,
    dir,
    showToast,
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

  const processFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const fileList = Array.from(files);
    for (const f of fileList) {
      const fileId = `up-${Date.now()}-${f.name.replace(/[^a-zA-Z0-9]/g, "_")}`;
      const item: UploadingFile = {
        id: fileId,
        name: f.name,
        sizeKB: Math.round(f.size / 1024),
        progress: 15,
        status: "preprocessing",
        type: selectedType,
      };

      setQueue((prev) => [item, ...prev]);

      try {
        if (dataMode === "live") {
          // 1. Upload to live FastAPI server
          setQueue((q) =>
            q.map((x) => (x.id === fileId ? { ...x, progress: 40, status: "ocr" } : x))
          );

          const docTypeParam = selectedType === "auto" ? "emirates_id" : selectedType;
          const initialDoc = await api.documents.upload(f, docTypeParam, (p) => {
            setQueue((q) =>
              q.map((x) => (x.id === fileId ? { ...x, progress: Math.min(p, 60) } : x))
            );
          });

          // 2. Poll extraction pipeline status
          let currentDoc = initialDoc;
          let attempts = 0;
          while (
            attempts < 40 &&
            (currentDoc.status === "processing" || (currentDoc.status as string) === "queued")
          ) {
            await new Promise((resolve) => setTimeout(resolve, 1200));
            attempts++;
            try {
              currentDoc = await api.documents.get(initialDoc.id);
            } catch {
              // keep waiting
            }
          }

          // 3. Mark complete & update application context
          setQueue((q) =>
            q.map((x) =>
              x.id === fileId
                ? {
                    ...x,
                    progress: 100,
                    status: currentDoc.status === "failed" ? "error" : "done",
                    detectedType: currentDoc.documentType,
                  }
                : x
            )
          );

          addDocument(currentDoc);
          setSelectedDocumentId(currentDoc.id);
          showToast(
            currentDoc.status === "failed" ? "error" : "success",
            `Document ${currentDoc.referenceNumber} processed (${currentDoc.status.replace("_", " ")})`,
            `تمت معالجة المستند ${currentDoc.referenceNumber} بنجاح`
          );
        } else {
          // Mock mode with deterministic flow
          setQueue((q) =>
            q.map((x) => (x.id === fileId ? { ...x, progress: 75, status: "ocr" } : x))
          );
          await new Promise((resolve) => setTimeout(resolve, 600));

          const mockDoc = await api.documents.upload(f, selectedType === "auto" ? "emirates_id" : selectedType);
          setQueue((q) =>
            q.map((x) =>
              x.id === fileId
                ? { ...x, progress: 100, status: "done", detectedType: mockDoc.documentType }
                : x
            )
          );
          addDocument(mockDoc);
          setSelectedDocumentId(mockDoc.id);
        }
      } catch (err: any) {
        setQueue((q) =>
          q.map((x) => (x.id === fileId ? { ...x, progress: 100, status: "error" } : x))
        );
        showToast("error", `Upload failed: ${err.message}`, "فشل رفع ومعالجة المستند");
      }
    }
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
