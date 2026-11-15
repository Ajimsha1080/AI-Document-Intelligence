import React from "react";
import { useApp } from "@/context/AppContext";
import { cn } from "@/lib/utils";
import { ZoomIn, ZoomOut, RotateCcw, FileText, ChevronLeft, ChevronRight, Eye, EyeOff } from "lucide-react";

export function DocumentViewer() {
  const {
    selectedDocument,
    activeFieldKey,
    setActiveFieldKey,
    zoomLevel,
    setZoomLevel,
    activePage,
    setActivePage,
    piiMasked,
    togglePiiMasked,
    language,
  } = useApp();

  if (!selectedDocument) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center text-muted-foreground border rounded-xl bg-card">
        <FileText className="w-12 h-12 mb-3 stroke-1 text-muted-foreground/50" />
        <p className="text-sm font-semibold">
          {language === "ar" ? "لم يتم تحديد أي مستند" : "No document selected"}
        </p>
      </div>
    );
  }

  const handleZoomIn = () => setZoomLevel((z) => Math.min(z + 15, 200));
  const handleZoomOut = () => setZoomLevel((z) => Math.max(z - 15, 60));
  const handleResetZoom = () => setZoomLevel(100);

  return (
    <div className="flex flex-col h-full bg-slate-900/5 dark:bg-slate-950/60 rounded-xl border border-border overflow-hidden select-none">
      {/* Viewer Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-card/90 backdrop-blur text-xs">
        {/* Left: Document Info */}
        <div className="flex items-center gap-2">
          <span className="font-bold text-foreground truncate max-w-[160px] sm:max-w-xs">
            {selectedDocument.fileName}
          </span>
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-secondary text-muted-foreground">
            {selectedDocument.referenceNumber}
          </span>
        </div>

        {/* Center: Page Controls */}
        <div className="flex items-center gap-1.5 bg-secondary/80 px-2 py-0.5 rounded-lg border border-border">
          <button
            onClick={() => setActivePage(Math.max(1, activePage - 1))}
            disabled={activePage <= 1}
            className="p-1 rounded text-muted-foreground hover:text-foreground disabled:opacity-30"
            title="Previous Page"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span className="text-[11px] font-semibold text-foreground px-1">
            {activePage} / {selectedDocument.pageCount}
          </span>
          <button
            onClick={() => setActivePage(Math.min(selectedDocument.pageCount, activePage + 1))}
            disabled={activePage >= selectedDocument.pageCount}
            className="p-1 rounded text-muted-foreground hover:text-foreground disabled:opacity-30"
            title="Next Page"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Right: Zoom & PII Masking */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={togglePiiMasked}
            className={cn(
              "flex items-center gap-1 px-2 py-1 rounded text-[11px] font-semibold transition-all border",
              piiMasked
                ? "bg-emerald-50 text-emerald-800 border-emerald-300 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800"
                : "bg-amber-50 text-amber-800 border-amber-300 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800"
            )}
            title="Toggle PII Masking [M]"
          >
            {piiMasked ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            <span className="hidden sm:inline">{piiMasked ? "PII Masked" : "PII Unmasked"}</span>
          </button>

          <div className="flex items-center gap-1 bg-secondary p-0.5 rounded-lg border border-border">
            <button
              onClick={handleZoomOut}
              className="p-1 rounded text-muted-foreground hover:text-foreground"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="text-[11px] font-mono px-1 font-semibold text-muted-foreground min-w-[36px] text-center">
              {zoomLevel}%
            </span>
            <button
              onClick={handleZoomIn}
              className="p-1 rounded text-muted-foreground hover:text-foreground"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleResetZoom}
              className="p-1 rounded text-muted-foreground hover:text-foreground border-s border-border ps-1.5"
              title="Reset Zoom"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>

      {/* Document View Canvas */}
      <div className="flex-1 overflow-auto p-6 flex justify-center items-start bg-slate-100/70 dark:bg-slate-950/80">
        <div
          className="relative transition-all duration-150 origin-top shadow-2xl rounded-lg border border-border/80 bg-white text-slate-900"
          style={{
            transform: `scale(${zoomLevel / 100})`,
            width: selectedDocument.documentType === "emirates_id" ? "760px" : "680px",
            minHeight: selectedDocument.documentType === "emirates_id" ? "480px" : "880px",
          }}
        >
          {/* Document Content Rendering */}
          {selectedDocument.previewUrl && selectedDocument.previewUrl.startsWith("http") ? (
            <div className="relative w-full h-full flex flex-col items-center justify-center p-4 bg-slate-50 min-h-[480px]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={selectedDocument.previewUrl}
                alt={selectedDocument.fileName}
                className="w-full h-auto object-contain select-none pointer-events-none rounded"
                onError={(e) => {
                  // Fallback to synthetic view if image load fails
                  (e.target as HTMLElement).style.display = "none";
                }}
              />
            </div>
          ) : selectedDocument.documentType === "emirates_id" ? (
            /* Synthetic Emirates ID Render */
            <div className="p-6 h-full flex flex-col justify-between font-sans relative">
              {/* Header Banner */}
              <div className="flex items-start justify-between border-b-2 border-emerald-800 pb-3">
                <div>
                  <div className="text-[11px] font-bold text-slate-800 tracking-wider">UNITED ARAB EMIRATES</div>
                  <div className="text-[9px] text-slate-500">Federal Authority for Identity & Citizenship</div>
                </div>
                <div className="text-right">
                  <div className="text-[11px] font-bold text-slate-800">دولة الإمارات العربية المتحدة</div>
                  <div className="text-[9px] text-slate-500">الهيئة الاتحادية للهوية والجنسية</div>
                </div>
              </div>

              {/* ID Body */}
              <div className="grid grid-cols-12 gap-4 my-6 items-center">
                {/* Photo Placeholder */}
                <div className="col-span-4 h-48 bg-slate-200 rounded-lg border border-slate-300 flex flex-col items-center justify-center text-slate-400 text-xs">
                  <span className="text-2xl mb-1">👤</span>
                  <span className="text-[10px] font-mono">SYNTHETIC PHOTO</span>
                </div>

                {/* Information Column */}
                <div className="col-span-8 space-y-3 ps-2">
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase font-semibold">Identity Number / رقم الهوية</div>
                    <div className="text-xl font-bold font-mono tracking-wider text-rose-800">
                      {piiMasked ? "784-****-*******-1" : "784-1988-1234567-1"}
                    </div>
                  </div>

                  <div>
                    <div className="text-[10px] text-slate-500">Name / الاسم:</div>
                    <div className="text-sm font-bold text-slate-900">سالم راشد سيف الشامسي</div>
                    <div className="text-xs font-semibold text-slate-700">SALEM RASHED SAIF AL SHAMSI</div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs pt-2">
                    <div>
                      <div className="text-[10px] text-slate-500">Nationality / الجنسية:</div>
                      <div className="font-semibold text-slate-800">United Arab Emirates / الإمارات</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-500">Date of Birth / تاريخ الميلاد:</div>
                      <div className="font-semibold font-mono text-slate-800">15/04/1988</div>
                    </div>
                  </div>

                  <div className="pt-1">
                    <div className="text-[10px] text-slate-500">Expiry Date / تاريخ الانتهاء:</div>
                    <div className="font-bold font-mono text-emerald-800 text-sm">14/04/2028</div>
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="border-t border-slate-200 pt-2 flex items-center justify-between text-[9px] text-slate-400 font-mono">
                <span>CARD CHIP SECURE</span>
                <span>SOVEREIGN ARCHIVE • COMPLIANT WITH UAE PDPL</span>
              </div>
            </div>
          ) : selectedDocument.documentType === "uae_trade_license" ? (
            /* Synthetic UAE Trade License Render */
            <div className="p-8 h-full space-y-6 font-sans">
              <div className="text-center border-b-2 border-slate-900 pb-4">
                <div className="text-sm font-bold text-emerald-800">GOVERNMENT OF DUBAI / حكومة دبي</div>
                <div className="text-xs text-slate-600">Department of Economy and Tourism / دائرة الاقتصاد والسياحة</div>
                <div className="text-lg font-extrabold text-slate-900 mt-1">COMMERCIAL LICENSE / رخصة تجارية</div>
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="text-slate-500 block text-[10px]">License No / رقم الرخصة:</span>
                  <span className="font-mono font-bold text-sm text-slate-900">CN-1029384</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">Expiry Date / تاريخ الانتهاء:</span>
                  <span className="font-mono font-bold text-sm text-emerald-800">30/11/2027</span>
                </div>
              </div>

              <div className="space-y-1 text-xs pt-2">
                <span className="text-slate-500 block text-[10px]">Legal Name (EN):</span>
                <span className="font-bold text-slate-900 text-sm">GULF HORIZON LOGISTICS L.L.C.</span>
              </div>

              <div className="space-y-1 text-xs">
                <span className="text-slate-500 block text-[10px]">Trade Name (AR) / الاسم التجاري:</span>
                <span className="font-bold text-slate-900 text-sm">شركة أفق الخليج للخدمات اللوجستية ذ.م.م</span>
              </div>

              <div className="p-3 bg-slate-50 rounded border border-slate-200 text-xs">
                <span className="text-slate-500 block text-[10px]">Issuing Authority / سلطة الترخيص:</span>
                <span className="font-semibold text-slate-800">Dubai Department of Economy and Tourism (DET)</span>
              </div>

              {/* Official Seal */}
              <div className="pt-6 flex justify-end">
                <div className="w-24 h-24 rounded-full border-2 border-dashed border-rose-600 flex flex-col items-center justify-center text-rose-700 text-[10px] font-bold rotate-12">
                  <span>GOVT OF DUBAI</span>
                  <span>DET SEAL</span>
                </div>
              </div>
            </div>
          ) : (
            /* Commercial Invoice Render */
            <div className="p-8 h-full space-y-6 font-sans">
              <div className="flex justify-between items-start border-b pb-4">
                <div>
                  <div className="text-lg font-extrabold text-slate-900">TAX INVOICE / فاتورة ضريبية</div>
                  <div className="text-xs text-slate-500">TRN: 100234891100003</div>
                </div>
                <div className="text-right">
                  <div className="font-mono font-bold text-slate-900">TAX-2026-08819</div>
                  <div className="text-xs text-slate-500">Date: 10/11/2026</div>
                </div>
              </div>

              {/* Items Table */}
              <div className="border rounded overflow-hidden text-xs">
                <table className="w-full text-left">
                  <thead className="bg-slate-100 text-[10px] text-slate-600 uppercase border-b">
                    <tr>
                      <th className="p-2">Description</th>
                      <th className="p-2">Qty</th>
                      <th className="p-2">Unit Price</th>
                      <th className="p-2 text-right">Total (AED)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y text-slate-800">
                    {selectedDocument.tableData?.map((item) => (
                      <tr key={item.id}>
                        <td className="p-2">{item.itemDescription}</td>
                        <td className="p-2 font-mono">{item.quantity}</td>
                        <td className="p-2 font-mono">AED {item.unitPriceAED.toLocaleString()}</td>
                        <td className="p-2 font-mono text-right font-semibold">
                          AED {item.lineTotalAED.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Totals */}
              <div className="flex justify-end pt-4">
                <div className="w-56 space-y-1.5 text-xs font-semibold">
                  <div className="flex justify-between text-slate-600">
                    <span>Subtotal:</span>
                    <span className="font-mono">AED 45,000.00</span>
                  </div>
                  <div className="flex justify-between text-slate-600">
                    <span>UAE VAT (5%):</span>
                    <span className="font-mono">AED 2,250.00</span>
                  </div>
                  <div className="flex justify-between text-base font-extrabold text-slate-900 border-t pt-2">
                    <span>Grand Total:</span>
                    <span className="font-mono text-rose-800">
                      AED {selectedDocument.fields.find((f) => f.key === "total_amount")?.value || "48,150.00"}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Interactive Bounding Boxes Overlay */}
          {selectedDocument.fields.map((field) => {
            if (!field.bbox || field.bbox.page !== activePage) return null;

            const isCurrent = field.key === activeFieldKey;

            return (
              <button
                key={field.id}
                onClick={() => setActiveFieldKey(field.key)}
                className={cn(
                  "absolute rounded transition-all cursor-pointer text-left focus:outline-none",
                  isCurrent
                    ? "ring-2 ring-emerald-600 bg-emerald-500/25 border border-emerald-700 shadow-md z-30"
                    : "border border-amber-500/70 bg-amber-400/10 hover:bg-amber-400/25 z-20"
                )}
                style={{
                  left: `${field.bbox.x}%`,
                  top: `${field.bbox.y}%`,
                  width: `${field.bbox.width}%`,
                  height: `${field.bbox.height}%`,
                }}
                title={`${field.nameEn} (${Math.round(field.confidence * 100)}% confidence)`}
              >
                {isCurrent && (
                  <span className="absolute -top-5 start-0 px-1.5 py-0.2 bg-emerald-800 text-white text-[9px] font-bold rounded shadow-sm whitespace-nowrap">
                    {field.nameEn} • {Math.round(field.confidence * 100)}%
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
