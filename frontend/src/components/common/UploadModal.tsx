"use client";

import React, { useState, useRef } from "react";
import { useApp } from "@/context/AppContext";
import { api } from "@/lib/api";
import { UploadCloud, FileText, CheckCircle2, X, Loader2 } from "lucide-react";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function UploadModal({ isOpen, onClose }: UploadModalProps) {
  const { refreshDocuments, showToast, language, setCurrentScreen, setSelectedDocumentId } = useApp();
  const [isDragging, setIsDragging] = useState(false);
  const [selectedType, setSelectedType] = useState<string>("auto");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (file: File) => {
    setIsUploading(true);
    setUploadProgress(10);

    try {
      const typeOverride = selectedType === "auto" ? undefined : selectedType;
      const uploadedDoc = await api.documents.upload(file, typeOverride, (progress: number) => {
        setUploadProgress(progress);
      });

      setUploadProgress(100);
      showToast(
        "success",
        `Uploaded ${file.name} successfully. Processing pipeline started.`,
        `تم تحميل ${file.name} بنجاح. بدأت المعالجة الآلية.`
      );

      await refreshDocuments();
      if (uploadedDoc && uploadedDoc.id) {
        setSelectedDocumentId(uploadedDoc.id);
        setCurrentScreen("review");
      }
      onClose();
    } catch (err: any) {
      showToast(
        "error",
        err.message || "Failed to upload document",
        "تعذر تحميل المستند، يرجى المحاولة مرة أخرى"
      );
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-150">
      <div
        className="w-full max-w-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-2xl overflow-hidden p-6 text-zinc-900 dark:text-zinc-100 flex flex-col gap-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 flex items-center justify-center font-bold text-sm">
              <UploadCloud className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold tracking-tight">
                {language === "ar" ? "تحميل مستند للمعالجة" : "Upload Document"}
              </h2>
              <p className="text-xs text-zinc-500">
                {language === "ar" ? "معالجة سيادية داخل الدولة بنسبة 100%" : "In-Country Sovereign Boundary Guaranteed"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Document Type Selector */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400">
            {language === "ar" ? "نوع المستند (تلقائي أو محدد)" : "Document Type"}
          </label>
          <div className="grid grid-cols-4 gap-2 text-xs">
            {[
              { id: "auto", label: "Auto Detect" },
              { id: "emirates_id", label: "Emirates ID" },
              { id: "uae_trade_license", label: "Trade License" },
              { id: "commercial_invoice", label: "Invoice" },
            ].map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setSelectedType(t.id)}
                className={`px-2 py-1.5 rounded-lg border font-medium text-center truncate transition ${
                  selectedType === t.id
                    ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 border-transparent shadow-xs"
                    : "border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Dropzone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition ${
            isDragging
              ? "border-zinc-900 bg-zinc-100 dark:border-zinc-100 dark:bg-zinc-800"
              : "border-zinc-200 dark:border-zinc-800 hover:border-zinc-400 dark:hover:border-zinc-600 bg-zinc-50/50 dark:bg-zinc-950/40"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".png,.jpg,.jpeg,.pdf,.tiff"
            onChange={handleFileChange}
            className="hidden"
          />

          <div className="w-12 h-12 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center mb-3 text-zinc-600 dark:text-zinc-400">
            {isUploading ? (
              <Loader2 className="w-6 h-6 animate-spin text-zinc-900 dark:text-zinc-100" />
            ) : (
              <FileText className="w-6 h-6" />
            )}
          </div>

          <p className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
            {isUploading
              ? `Uploading... ${uploadProgress}%`
              : language === "ar"
              ? "اسحب المستند هنا أو اضغط للاختيار"
              : "Drag & drop document here, or click to browse"}
          </p>
          <p className="text-xs text-zinc-400 mt-1">
            PNG, JPG, PDF up to 25MB · Emirates ID, Trade License, Commercial Invoice
          </p>

          {isUploading && (
            <div className="w-full max-w-xs mt-4 bg-zinc-200 dark:bg-zinc-800 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-zinc-900 dark:bg-zinc-100 h-1.5 rounded-full transition-all duration-200"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          )}
        </div>

        <div className="flex items-center justify-between text-xs text-zinc-400 pt-2 border-t border-zinc-100 dark:border-zinc-800">
          <span className="flex items-center gap-1.5 text-zinc-900 dark:text-zinc-100 font-semibold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Zero-Egress Sovereign Boundary
          </span>
          <span className="text-zinc-400">UAE PDPL Law 45/2021</span>
        </div>
      </div>
    </div>
  );
}
