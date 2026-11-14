import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "@/context/AppContext";

export const metadata: Metadata = {
  title: "Sanad DocIntel | UAE Sovereign Document Intelligence Platform",
  description:
    "Multi-tenant Document Intelligence SaaS tailored for UAE Banking, KYC, and Trade Compliance. 100% In-Country Data Boundary.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" dir="ltr" suppressHydrationWarning>
      <body className="antialiased min-h-screen">
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}
