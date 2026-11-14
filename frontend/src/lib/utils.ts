import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Normalizes digits to Arabic-Indic (Eastern Arabic numerals: ٠١٢٣٤٥٦٧٨٩)
 */
export function toArabicIndicDigits(value: string | number): string {
  const arabicNumerals = ["٠", "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩"];
  return String(value).replace(/[0-9]/g, (digit) => arabicNumerals[parseInt(digit, 10)]);
}

/**
 * Formats UAE Dirham currency amounts according to current locale
 */
export function formatCurrencyAED(amount: number, useArabicNumerals: boolean = false): string {
  const formattedStandard = new Intl.NumberFormat("en-AE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);

  if (useArabicNumerals) {
    return `${toArabicIndicDigits(formattedStandard)} د.إ`;
  }
  return `AED ${formattedStandard}`;
}

/**
 * Formats date to display format with optional Arabic numerals
 */
export function formatDateBilingual(dateStr: string, isArabic: boolean = false): string {
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;

    const formatted = d.toLocaleDateString(isArabic ? "ar-AE" : "en-GB", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });

    return formatted;
  } catch {
    return dateStr;
  }
}
