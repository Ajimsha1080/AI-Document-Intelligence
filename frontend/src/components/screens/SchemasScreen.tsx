"use client";

import React, { useState } from "react";
import { useApp } from "@/context/AppContext";
import { DocumentTypeSchema, SchemaFieldDefinition } from "@/types";
import { Plus, Trash2, Save } from "lucide-react";

export function SchemasScreen() {
  const { schemas, updateSchema, userRole, showToast } = useApp();
  const [selectedSchemaId, setSelectedSchemaId] = useState<string>(schemas[0]?.id || "");
  const [activeTab, setActiveTab] = useState<"fields" | "rules">("fields");

  const currentSchema = schemas.find((s) => s.id === selectedSchemaId) || schemas[0];

  // Local editing state for schema
  const [schemaFields, setSchemaFields] = useState<SchemaFieldDefinition[]>(currentSchema?.fields || []);
  const [newFieldKey, setNewFieldKey] = useState("");
  const [newFieldNameEn, setNewFieldNameEn] = useState("");
  const [newFieldNameAr, setNewFieldNameAr] = useState("");
  const [newFieldType, setNewFieldType] = useState<any>("string");

  const handleSelectSchema = (s: DocumentTypeSchema) => {
    setSelectedSchemaId(s.id);
    setSchemaFields(s.fields || []);
  };

  const handleAddField = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFieldKey.trim() || !newFieldNameEn.trim()) return;

    const newField: SchemaFieldDefinition = {
      id: `field-${Date.now()}`,
      key: newFieldKey.trim().toLowerCase().replace(/\s+/g, "_"),
      nameEn: newFieldNameEn.trim(),
      nameAr: newFieldNameAr.trim() || newFieldNameEn.trim(),
      dataType: newFieldType,
      required: true,
      confidenceThreshold: 0.85,
      section: "general",
    };

    setSchemaFields((prev) => [...prev, newField]);
    setNewFieldKey("");
    setNewFieldNameEn("");
    setNewFieldNameAr("");
  };

  const handleRemoveField = (fieldId: string) => {
    setSchemaFields((prev) => prev.filter((f) => f.id !== fieldId));
  };

  const handleSaveSchema = async () => {
    if (!currentSchema) return;
    try {
      const updated: DocumentTypeSchema = {
        ...currentSchema,
        fields: schemaFields,
      };
      await updateSchema(updated);
      showToast("success", "Schema updated successfully", "تم حفظ المخطط بنجاح");
    } catch (err: any) {
      showToast("error", err.message || "Failed to update schema", "تعذر حفظ المخطط");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header (Matching screens/Schemas.dc.html) */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-1.5 text-xs text-zinc-400">
          <span>Configure</span>
          <span>/</span>
          <span>Document types</span>
          <span>/</span>
          <span className="font-semibold text-zinc-800 dark:text-zinc-200">{currentSchema?.nameEn}</span>
        </div>
        <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
          Document Types & Extraction Schemas
        </h1>
        <p className="text-xs text-zinc-500">
          Configure bilingual Arabic/English field definitions, minimum confidence thresholds, and sovereign validation rules.
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6 items-start">
        {/* Left: Schema Selector List */}
        <aside className="w-full lg:w-72 shrink-0 border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-900 p-3 flex flex-col gap-2 shadow-xs">
          <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider px-2 py-1">
            Registered Types
          </span>

          {schemas.map((s) => {
            const isSelected = s.id === currentSchema?.id;
            return (
              <button
                key={s.id}
                onClick={() => handleSelectSchema(s)}
                className={`p-3 rounded-lg text-start flex flex-col gap-1 transition ${
                  isSelected
                    ? "bg-zinc-100 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 shadow-xs"
                    : "hover:bg-zinc-50 dark:hover:bg-zinc-800/50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-zinc-900 dark:text-zinc-100">{s.nameEn}</span>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-zinc-100 text-zinc-900 border border-zinc-300 dark:bg-zinc-800 dark:text-zinc-100 dark:border-zinc-700">
                    Live
                  </span>
                </div>
                <span className="text-[11px] text-zinc-400 font-medium">
                  {(s.fields || []).length} fields · {(s.rules || []).length} rules · {s.code}
                </span>
              </button>
            );
          })}
        </aside>

        {/* Right: Schema Field Editor */}
        <main className="flex-1 w-full border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-900 flex flex-col shadow-xs overflow-hidden">
          {/* Metadata bar */}
          <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 grid grid-cols-1 sm:grid-cols-3 gap-3 bg-zinc-50/50 dark:bg-zinc-950/40">
            <div>
              <label className="text-[11px] font-semibold text-zinc-500">English Name</label>
              <input
                type="text"
                value={currentSchema?.nameEn || ""}
                disabled
                className="w-full mt-1 px-3 py-1.5 text-xs bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-zinc-700 dark:text-zinc-300"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-zinc-500">Arabic Name</label>
              <input
                type="text"
                dir="rtl"
                value={currentSchema?.nameAr || ""}
                disabled
                className="w-full mt-1 px-3 py-1.5 text-xs bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-zinc-700 dark:text-zinc-300"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-zinc-500">API Code</label>
              <input
                type="text"
                value={currentSchema?.code || ""}
                disabled
                className="w-full mt-1 px-3 py-1.5 text-xs bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-zinc-700 dark:text-zinc-300 font-medium"
              />
            </div>
          </div>

          {/* Tab selector */}
          <div className="flex items-center gap-1 px-4 border-b border-zinc-200 dark:border-zinc-800 text-xs font-semibold">
            <button
              onClick={() => setActiveTab("fields")}
              className={`py-3 px-3 border-b-2 transition ${
                activeTab === "fields"
                  ? "border-zinc-900 dark:border-white text-zinc-900 dark:text-zinc-100"
                  : "border-transparent text-zinc-400 hover:text-zinc-700"
              }`}
            >
              Fields ({schemaFields.length})
            </button>
            <button
              onClick={() => setActiveTab("rules")}
              className={`py-3 px-3 border-b-2 transition ${
                activeTab === "rules"
                  ? "border-zinc-900 dark:border-white text-zinc-900 dark:text-zinc-100"
                  : "border-transparent text-zinc-400 hover:text-zinc-700"
              }`}
            >
              Validation Rules ({(currentSchema?.rules || []).length})
            </button>
          </div>

          {/* Fields Table */}
          {activeTab === "fields" ? (
            <div className="flex flex-col">
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-start">
                  <thead>
                    <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 text-zinc-500 font-semibold">
                      <th className="p-3 text-start">Key</th>
                      <th className="p-3 text-start">Label (EN / AR)</th>
                      <th className="p-3 text-start">Type</th>
                      <th className="p-3 text-start">Required</th>
                      <th className="p-3 text-start">Min Confidence</th>
                      <th className="p-3 text-end">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                    {schemaFields.map((f) => (
                      <tr key={f.id} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-800/30">
                        <td className="p-3 font-medium text-zinc-700 dark:text-zinc-300">{f.key}</td>
                        <td className="p-3">
                          <div className="flex flex-col">
                            <span className="font-semibold text-zinc-900 dark:text-zinc-100">{f.nameEn}</span>
                            <span className="text-[11px] text-zinc-400">{f.nameAr}</span>
                          </div>
                        </td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 uppercase">
                            {f.dataType}
                          </span>
                        </td>
                        <td className="p-3">
                          <span className={f.required ? "text-zinc-900 dark:text-zinc-100 font-semibold" : "text-zinc-400"}>
                            {f.required ? "Required" : "Optional"}
                          </span>
                        </td>
                        <td className="p-3 font-medium text-zinc-500">
                          {Math.round((f.confidenceThreshold || 0.85) * 100)}%
                        </td>
                        <td className="p-3 text-end">
                          {userRole === "admin" && (
                            <button
                              type="button"
                              onClick={() => handleRemoveField(f.id)}
                              className="text-zinc-400 hover:text-rose-600 transition"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Add Field Inline Form (Admin only) */}
              {userRole === "admin" && (
                <form onSubmit={handleAddField} className="p-3 bg-zinc-50 dark:bg-zinc-950/60 border-t border-zinc-200 dark:border-zinc-800 flex flex-wrap items-center gap-2 text-xs">
                  <input
                    type="text"
                    placeholder="field_key"
                    value={newFieldKey}
                    onChange={(e) => setNewFieldKey(e.target.value)}
                    className="w-32 px-2.5 py-1.5 border border-zinc-200 dark:border-zinc-800 rounded bg-white dark:bg-zinc-900 outline-hidden font-medium"
                  />
                  <input
                    type="text"
                    placeholder="English Label"
                    value={newFieldNameEn}
                    onChange={(e) => setNewFieldNameEn(e.target.value)}
                    className="flex-1 min-w-[140px] px-2.5 py-1.5 border border-zinc-200 dark:border-zinc-800 rounded bg-white dark:bg-zinc-900 outline-hidden"
                  />
                  <input
                    type="text"
                    dir="rtl"
                    placeholder="الاسم بالعربية"
                    value={newFieldNameAr}
                    onChange={(e) => setNewFieldNameAr(e.target.value)}
                    className="flex-1 min-w-[140px] px-2.5 py-1.5 border border-zinc-200 dark:border-zinc-800 rounded bg-white dark:bg-zinc-900 outline-hidden"
                  />
                  <select
                    value={newFieldType}
                    onChange={(e) => setNewFieldType(e.target.value)}
                    className="w-24 px-2 py-1.5 border border-zinc-200 dark:border-zinc-800 rounded bg-white dark:bg-zinc-900 outline-hidden"
                  >
                    <option value="string">String</option>
                    <option value="date">Date</option>
                    <option value="number">Number</option>
                    <option value="currency">Currency</option>
                  </select>
                  <button
                    type="submit"
                    className="px-3 py-1.5 bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 font-semibold rounded hover:opacity-90 transition flex items-center gap-1"
                  >
                    <Plus className="w-3 h-3" />
                    <span>Add</span>
                  </button>
                </form>
              )}
            </div>
          ) : (
            /* Rules Tab */
            <div className="p-5 divide-y divide-zinc-100 dark:divide-zinc-800/60 text-xs">
              {(currentSchema?.rules || []).map((r) => (
                <div key={r.id} className="py-3 flex items-center justify-between">
                  <div className="flex flex-col gap-0.5">
                    <span className="font-semibold text-zinc-900 dark:text-zinc-100">{r.nameEn}</span>
                    <span className="text-[11px] font-medium text-zinc-400">
                      Rule Type: {r.ruleType} · Target Field: {r.targetField}
                    </span>
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-zinc-100 text-zinc-900 border border-zinc-300 dark:bg-zinc-800 dark:text-zinc-100 dark:border-zinc-700">
                    Enforced
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Footer Save Button */}
          {userRole === "admin" && (
            <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex justify-end">
              <button
                type="button"
                onClick={handleSaveSchema}
                className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-white dark:bg-zinc-100 dark:hover:bg-zinc-200 dark:text-zinc-900 font-semibold text-xs rounded-lg transition flex items-center gap-1.5 shadow-xs"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save Schema Changes</span>
              </button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
