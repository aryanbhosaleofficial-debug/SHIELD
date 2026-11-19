import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "S.H.I.E.L.D. — Solar Flare Early Warning System",
  description:
    "Solar Hazard Interception & Extra-orbital Logistics Dashboard — real-time solar flare detection " +
    "and forecasting built on real ISRO Aditya-L1 SoLEXS + HEL1OS data. Team Suryastra, Bharatiya " +
    "Antariksh Hackathon 2026.",
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
