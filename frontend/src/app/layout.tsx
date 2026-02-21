import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import { AuthProvider } from "@/context/AuthContext";

export const metadata: Metadata = {
  title: "Coins – Kenya Price Comparison",
  description:
    "Compare grocery prices across Naivas, Carrefour, and Quickmart. Build your shopping list and always get the best deal.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 antialiased">
        <AuthProvider>
          <Navbar />
          <main>{children}</main>
          <footer className="mt-16 border-t border-gray-200 py-8 text-center text-sm text-gray-500">
            <p>
              Coins &mdash; Helping Kenyans save on groceries. Prices updated
              regularly from Naivas, Carrefour &amp; Quickmart.
            </p>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
