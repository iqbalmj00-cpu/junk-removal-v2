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
              var DASHBOARD_URL = "https://scaleyourjunk.vercel.app";
              var API_KEY = "bc47077cec5a30d12dfb961d5b8980125d3b4e02eba9b8728b3ce03cc7290a86";
              var SITE_TOKEN = "2e9fefa7-4741-46b1-81a5-5d4800f2adfa";
              function trackEvent(event, page, metadata) {
                fetch(DASHBOARD_URL + "/api/ingest/website-event", {
                  method: "POST",
                  headers: {
                    "Content-Type": "application/json",
                    "x-api-key": API_KEY,
                    "x-site-token": SITE_TOKEN
                  },
                  body: JSON.stringify({ event: event, page: page || window.location.pathname, metadata: metadata || {} })
                }).catch(function(err) { console.error("Track error:", err); });
              }
              trackEvent("page_view");
              document.addEventListener("click", function(e) {
                var el = e.target.closest("[data-track]");
                if (!el) return;
                var action = el.getAttribute("data-track");
                if (action === "book_now") trackEvent("book_now_click");
                if (action === "quote_upload") trackEvent("quote_upload");
                if (action === "booking_finalized") trackEvent("booking_finalized");
              });
              window.syj = { track: trackEvent };
            })();
          `}
        </Script>
      </body>
    </html>
  );
}
