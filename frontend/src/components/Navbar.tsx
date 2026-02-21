"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function Navbar() {
  const path = usePathname();
  const { user, logout } = useAuth();

  const links = [
    { href: "/", label: "Search" },
    { href: "/compare", label: "Compare" },
    { href: "/list", label: "My List" },
  ];

  return (
    <nav className="sticky top-0 z-50 border-b border-gray-200 bg-white shadow-sm">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2">
          <span className="text-2xl font-black text-green-600">coins</span>
          <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">
            KE
          </span>
        </Link>

        {/* Nav links + auth */}
        <div className="flex items-center gap-1">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                path === l.href
                  ? "bg-green-600 text-white"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              }`}
            >
              {l.label}
            </Link>
          ))}

          <div className="ml-3 border-l border-gray-200 pl-3">
            {user ? (
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-700">
                  {user.name}
                </span>
                <button
                  onClick={logout}
                  className="rounded-lg px-3 py-2 text-sm font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-900"
                >
                  Sign out
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                className="rounded-lg px-4 py-2 text-sm font-medium text-green-600 hover:bg-green-50"
              >
                Sign in
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
