import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Patient Journey | Powered by SYN10X",
  description: "AI-generated patient journey maps from Snowflake evidence data",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Figtree:wght@300;400;500;600;700&family=Noto+Sans:wght@300;400;500;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body style={{ margin: 0, fontFamily: "'Figtree','Noto Sans','Segoe UI',sans-serif", background: "#F0F9FF" }}>
        {children}
      </body>
    </html>
  );
}
