import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { DashboardProvider } from "@/lib/dashboard-context";
import { TabShell } from "@/components/layout/TabShell";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AgentFlow",
  description: "Type what you want automated. We build and run it.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-[#030712] text-gray-50`}
      >
        <div className="flex h-screen">
          <Sidebar />
          <main className="flex-1 overflow-auto">
            <DashboardProvider>
              <TabShell>{children}</TabShell>
            </DashboardProvider>
          </main>
        </div>
      </body>
    </html>
  );
}
