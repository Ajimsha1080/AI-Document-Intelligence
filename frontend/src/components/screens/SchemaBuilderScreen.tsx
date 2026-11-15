import React, { useState } from "react";
import { useApp } from "@/context/AppContext";
import { DocumentTypeSchema, SchemaFieldDefinition, ValidationRuleDefinition, FieldDataType } from "@/types";
import {
  FileCode2,
  Plus,
  Trash2,
  Save,
} from "lucide-react";

export function SchemaBuilderScreen() {
  const { schemas, updateSchema, language } = useApp();

  const [selectedSchemaId, setSelectedSchemaId] = useState<string>(schemas[0]?.id || "sch-1");
  const activeSchema = schemas.find((s) => s.id === selectedSchemaId) || schemas[0];

  // Editable form state
  const [fields, setFields] = useState<SchemaFieldDefinition[]>(activeSchema.fields);
  const [rules, setRules] = useState<ValidationRuleDefinition[]>(activeSchema.rules);
  const [activeTab, setActiveTab] = useState<"fields" | "rules" | "json_preview">("fields");

  // New field state
  const [newKey, setNewKey] = useState("");
  const [newNameEn, setNewNameEn] = useState("");
  const [newNameAr, setNewNameAr] = useState("");
  const [newType, setNewType] = useState<FieldDataType>("string");
  const [newRequired, setNewRequired] = useState(true);
  const [newThreshold, setNewThreshold] = useState(0.85);

  const handleSelectSchema = (id: string) => {
    setSelectedSchemaId(id);
    const s = schemas.find((item) => item.id === id);
    if (s) {
      setFields(s.fields);
      setRules(s.rules);
    }
  };

  const handleAddField = () => {
    if (!newKey || !newNameEn) return;

    const newFieldObj: SchemaFieldDefinition = {
      id: `sf-${Date.now()}`,
      key: newKey.toLowerCase().replace(/\s+/g, "_"),
      nameEn: newNameEn,
      nameAr: newNameAr || newNameEn,
      dataType: newType,
      required: newRequired,
      confidenceThreshold: newThreshold,
      section: "general",
    };

    const updated = [...fields, newFieldObj];
    setFields(updated);
    setNewKey("");
    setNewNameEn("");
    setNewNameAr("");
  };

  const handleDeleteField = (id: string) => {
    setFields((prev) => prev.filter((f) => f.id !== id));
  };

  const handleSaveSchema = () => {
    const updatedSchema: DocumentTypeSchema = {
      ...activeSchema,
      fields,
      rules,
    };
    updateSchema(updatedSchema);
  };

  return (
    <div className="space-y-6">
      {/* Top Controls */}
      <div className="p-5 rounded-2xl border border-border bg-card shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs">
        <div>
          <div className="flex items-center gap-2">
            <FileCode2 className="w-5 h-5 text-primary" />
            <h1 className="text-base font-extrabold text-foreground">
              {language === "ar" ? "منشئ ومحرر مخططات المستندات" : "Document Type & Schema Engine"}
            </h1>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {language === "ar"
              ? "تحديد الحقول المستهدفة، قواعد التحقق، وعتبات الثقة دون الحاجة لكتابة كود برمجي"
              : "Configure extraction fields, validation rules, and confidence thresholds without code changes"}
          </p>
        </div>

        {/* Schema Switcher */}
        <div className="flex items-center gap-2">
          <select
            value={selectedSchemaId}
            onChange={(e) => handleSelectSchema(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-border bg-secondary font-bold text-foreground text-xs focus:ring-1 focus:ring-primary"
          >
            {schemas.map((s) => (
              <option key={s.id} value={s.id}>
                {language === "ar" ? s.nameAr : s.nameEn}
              </option>
            ))}
          </select>

          <button
            onClick={handleSaveSchema}
            className="px-4 py-1.5 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground font-bold text-xs flex items-center gap-1.5 shadow-sm transition"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{language === "ar" ? "حفظ ونشر المخطط" : "Save & Deploy"}</span>
          </button>
        </div>
      </div>

      {/* Tabs Bar */}
      <div className="flex items-center gap-2 border-b border-border pb-1 text-xs">
        <button
          onClick={() => setActiveTab("fields")}
          className={`px-3 py-1.5 rounded-t-lg font-bold transition ${
            activeTab === "fields"
              ? "bg-card border-b-2 border-primary text-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {language === "ar" ? "الحقول المعرفة" : "Defined Fields"} ({fields.length})
        </button>
        <button
          onClick={() => setActiveTab("rules")}
          className={`px-3 py-1.5 rounded-t-lg font-bold transition ${
            activeTab === "rules"
              ? "bg-card border-b-2 border-primary text-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {language === "ar" ? "قواعد التحقق" : "Validation Rules"} ({rules.length})
        </button>
        <button
          onClick={() => setActiveTab("json_preview")}
          className={`px-3 py-1.5 rounded-t-lg font-bold transition ${
            activeTab === "json_preview"
              ? "bg-card border-b-2 border-primary text-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {language === "ar" ? "معاينة JSON المخطط" : "Schema JSON Preview"}
        </button>
      </div>

      {/* Tab 1: Fields Editor */}
      {activeTab === "fields" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Defined Fields Table (8 cols) */}
          <div className="lg:col-span-8 p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4 text-xs">
            <h3 className="font-bold text-foreground text-xs uppercase tracking-wider">
              {language === "ar" ? "قائمة الحقول المستخرجة" : "Active Field Definitions"}
            </h3>

            <div className="divide-y divide-border/60">
              {fields.map((f) => (
                <div key={f.id} className="py-2.5 flex items-center justify-between gap-3">
                  <div className="space-y-0.5 min-w-0">
                    <div className="font-bold text-foreground flex items-center gap-2">
                      <span>{language === "ar" ? f.nameAr : f.nameEn}</span>
                      <code className="text-[10px] font-mono px-1 py-0.2 bg-secondary rounded text-muted-foreground">
                        {f.key}
                      </code>
                      {f.required && (
                        <span className="text-rose-500 font-bold" title="Required">
                          *
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-muted-foreground flex items-center gap-2">
                      <span>Type: <strong className="text-foreground">{f.dataType}</strong></span>
                      <span>•</span>
                      <span>Min Confidence: <strong className="font-mono text-foreground">{Math.round(f.confidenceThreshold * 100)}%</strong></span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDeleteField(f.id)}
                    className="p-1.5 rounded text-muted-foreground hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40"
                    title="Remove Field"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Add Field Form (4 cols) */}
          <div className="lg:col-span-4 p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4 text-xs">
            <h3 className="font-bold text-foreground text-xs uppercase tracking-wider flex items-center gap-1.5">
              <Plus className="w-4 h-4 text-primary" />
              <span>{language === "ar" ? "إضافة حقل جديد" : "Add Field Definition"}</span>
            </h3>

            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-semibold text-muted-foreground mb-1">
                  Field Key (snake_case)
                </label>
                <input
                  type="text"
                  value={newKey}
                  onChange={(e) => setNewKey(e.target.value)}
                  placeholder="e.g. passport_number"
                  className="w-full px-3 py-1.5 rounded-lg border border-border bg-secondary/50 font-mono text-xs focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-muted-foreground mb-1">
                  Name (English)
                </label>
                <input
                  type="text"
                  value={newNameEn}
                  onChange={(e) => setNewNameEn(e.target.value)}
                  placeholder="e.g. Passport Number"
                  className="w-full px-3 py-1.5 rounded-lg border border-border bg-secondary/50 text-xs focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-muted-foreground mb-1">
                  Name (Arabic)
                </label>
                <input
                  type="text"
                  value={newNameAr}
                  onChange={(e) => setNewNameAr(e.target.value)}
                  placeholder="مثال: رقم جواز السفر"
                  className="w-full px-3 py-1.5 rounded-lg border border-border bg-secondary/50 text-xs focus:ring-1 focus:ring-primary"
                  dir="rtl"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-muted-foreground mb-1">
                  Data Type
                </label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value as any)}
                  className="w-full px-3 py-1.5 rounded-lg border border-border bg-secondary text-xs font-semibold focus:ring-1 focus:ring-primary"
                >
                  <option value="string">String (نص عام)</option>
                  <option value="regex">Regex Pattern (تعبير نمطي)</option>
                  <option value="date">Date (تاريخ)</option>
                  <option value="number">Numeric (رقمي)</option>
                  <option value="currency">Currency AED (عملة)</option>
                </select>
              </div>

              <div>
                <div className="flex justify-between text-[11px] font-semibold text-muted-foreground mb-1">
                  <span>Confidence Threshold</span>
                  <span className="font-mono text-foreground">{Math.round(newThreshold * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="0.99"
                  step="0.01"
                  value={newThreshold}
                  onChange={(e) => setNewThreshold(Number(e.target.value))}
                  className="w-full accent-emerald-600"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="reqChk"
                  checked={newRequired}
                  onChange={(e) => setNewRequired(e.target.checked)}
                  className="rounded text-primary focus:ring-primary"
                />
                <label htmlFor="reqChk" className="text-xs font-semibold text-foreground cursor-pointer">
                  Required Field (حقل إلزامي)
                </label>
              </div>

              <button
                onClick={handleAddField}
                disabled={!newKey || !newNameEn}
                className="w-full py-2 rounded-lg bg-primary text-primary-foreground font-bold hover:bg-primary/90 text-xs shadow-sm transition disabled:opacity-40"
              >
                {language === "ar" ? "إضافة الحقل إلى المخطط" : "Add to Schema"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Validation Rules */}
      {activeTab === "rules" && (
        <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4 text-xs">
          <h3 className="font-bold text-foreground text-xs uppercase tracking-wider">
            {language === "ar" ? "قواعد التحقق المنطقية" : "Configured Cross-Field Validation Rules"}
          </h3>

          <div className="divide-y divide-border/60">
            {rules.map((r) => (
              <div key={r.id} className="py-3 flex items-center justify-between gap-3">
                <div className="space-y-0.5">
                  <div className="font-bold text-foreground flex items-center gap-2">
                    <span>{language === "ar" ? r.nameAr : r.nameEn}</span>
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                      {r.severity.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    Target Field: <code className="font-mono text-foreground font-bold">{r.targetField}</code> • Rule: {r.ruleType}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={r.enabled}
                    onChange={() => {
                      setRules((prev) =>
                        prev.map((rule) =>
                          rule.id === r.id ? { ...rule, enabled: !rule.enabled } : rule
                        )
                      );
                    }}
                    className="rounded text-primary focus:ring-primary"
                  />
                  <span className="text-[11px] font-semibold text-muted-foreground">Active</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: JSON Preview */}
      {activeTab === "json_preview" && (
        <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold font-mono text-muted-foreground uppercase">
              JSON Definition (Compliant with UAE Model Schema Protocol)
            </h3>
          </div>
          <pre className="p-4 rounded-xl bg-slate-950 text-emerald-400 font-mono text-xs overflow-x-auto leading-relaxed border border-slate-800 max-h-96">
            {JSON.stringify({ ...activeSchema, fields, rules }, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
