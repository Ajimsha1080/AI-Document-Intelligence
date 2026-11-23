import React from "react";
import { useApp } from "@/context/AppContext";
import { Globe } from "lucide-react";

export function LanguageSwitcher() {
  const { language, toggleLanguage, useArabicDigits, toggleArabicDigits } = useApp();

  return (
    <div className="flex items-center gap-1.5 bg-secondary/80 p-1 rounded-lg border border-border/80">
      <button
        onClick={toggleLanguage}
        className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md transition-all bg-card text-foreground shadow-sm hover:bg-card/80 focus:ring-1 focus:ring-primary"
        title="Toggle English / Arabic"
      >
        <Globe className="w-3.5 h-3.5 text-primary" />
        <span>{language === "en" ? "العربية" : "English"}</span>
      </button>

      <button
        onClick={toggleArabicDigits}
        className={`px-2 py-1 text-xs font-semibold rounded-md transition-all ${
          useArabicDigits
            ? "bg-primary text-primary-foreground font-bold"
            : "text-muted-foreground hover:text-foreground"
        }`}
        title="Toggle Arabic-Indic Digits (٠-٩)"
      >
        {useArabicDigits ? "١٢٣" : "123"}
      </button>
    </div>
  );
}
