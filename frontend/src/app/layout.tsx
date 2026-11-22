import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "@/context/AppContext";

export const metadata: Metadata = {
  title: "DocIntel | UAE Sovereign Document Intelligence Platform",
  description:
    "Multi-tenant Document Intelligence SaaS tailored for UAE Banking, KYC, and Trade Compliance. 100% In-Country Sovereign Data Boundary.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" dir="ltr" suppressHydrationWarning>
      <body className="antialiased min-h-screen font-sans bg-[#FAFAFA] text-[#0A0A0A]">
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}
