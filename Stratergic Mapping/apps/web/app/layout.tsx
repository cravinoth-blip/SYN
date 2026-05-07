import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "7Cs Disease Intelligence Platform",
  description: "Stratergic Mapping 7Cs workspace"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

