import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MTG Deck Creator",
  description: "Commander deck builder from your collection",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
