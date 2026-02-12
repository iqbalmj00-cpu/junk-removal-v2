import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Script from "next/script";
import GoogleAnalytics from "@/components/GoogleAnalytics";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Clean Sweep Junk Removal Houston | Same-Day Pickup & Eco-Friendly Disposal",
  description: "Professional junk removal in Houston, TX. Furniture, appliances, yard waste, full cleanouts. Upfront pricing, same-day service, eco-friendly disposal. Call (832) 793-6566.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        {/* Material Icons for new pages */}
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet" />
        <Script
          src="https://www.googletagmanager.com/gtag/js?id=G-56CMER4LL2"
          strategy="afterInteractive"
        />
        <Script id="google-analytics" strategy="afterInteractive">
          {`
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', 'G-56CMER4LL2');
          `}
        </Script>
      </head>
      <body className={inter.className}>
        <GoogleAnalytics />
        {children}
        <Script id="dashboard-tracking" strategy="afterInteractive">
          {`
            (function() {
              function post(type, data) {
                fetch("/api/track", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(Object.assign({ type: type }, data))
                }).catch(function(err) { console.error("SYJ track error:", err); });
              }
              post("event", {
                event: "page_view",
                page: window.location.pathname
              });
              document.addEventListener("click", function(e) {
                var el = e.target.closest("[data-track]");
                if (!el) return;
                var action = el.getAttribute("data-track");
                if (["book_now_click", "book_now", "quote_upload", "booking_finalized"].indexOf(action) > -1) {
                  post("event", { event: action === "book_now" ? "book_now_click" : action, page: window.location.pathname });
                }
              });
              window.syj = window.syj || {};
              window.syj.track = function(event, page, metadata) {
                post("event", { event: event, page: page || window.location.pathname, metadata: metadata || {} });
              };
              window.syj.sendLead = function(data) {
                post("lead", data);
              };
              window.syj.sendQuote = function(data) {
                post("quote", data);
              };
            })();
          `}
        </Script>
      </body>
    </html>
  );
}
