import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Script from "next/script";
import GoogleAnalytics from "@/components/GoogleAnalytics";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Junk Removal App",
  description: "Clean simple junk removal",
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
              var DASHBOARD = "https://scaleyourjunk.vercel.app";
              var API_KEY = "bc47077cec5a30d12dfb961d5b8980125d3b4e02eba9b8728b3ce03cc7290a86";
              var SITE_TOKEN = "2e9fefa7-4741-46b1-81a5-5d4800f2adfa";
              var headers = {
                "Content-Type": "application/json",
                "x-api-key": API_KEY,
                "x-site-token": SITE_TOKEN
              };
              function post(endpoint, data) {
                fetch(DASHBOARD + endpoint, {
                  method: "POST",
                  headers: headers,
                  body: JSON.stringify(data)
                }).catch(function(err) { console.error("SYJ track error:", err); });
              }
              post("/api/ingest/website-event", {
                event: "page_view",
                page: window.location.pathname
              });
              document.addEventListener("click", function(e) {
                var el = e.target.closest("[data-track]");
                if (!el) return;
                var action = el.getAttribute("data-track");
                if (["book_now_click", "book_now", "quote_upload", "booking_finalized"].indexOf(action) > -1) {
                  post("/api/ingest/website-event", { event: action === "book_now" ? "book_now_click" : action, page: window.location.pathname });
                }
              });
              window.syj = window.syj || {};
              window.syj.track = function(event, page, metadata) {
                post("/api/ingest/website-event", { event: event, page: page || window.location.pathname, metadata: metadata || {} });
              };
              window.syj.sendLead = function(data) {
                post("/api/ingest/lead", data);
              };
              window.syj.sendQuote = function(data) {
                post("/api/ingest/quote", data);
              };
            })();
          `}
        </Script>
      </body>
    </html>
  );
}
