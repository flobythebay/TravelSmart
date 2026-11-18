import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "TravelSmart — Find your best trip",
  description: "AI-powered travel planning that optimizes dates, flights, hotels, and rewards.",
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
