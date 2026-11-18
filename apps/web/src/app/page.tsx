"use client";
import { FormEvent, useState } from "react";

type TripIntent = {
  destination?: string | null; earliest_departure?: string | null; latest_departure?: string | null;
  trip_length_days?: number | null; budget_total?: number | null; currency: string;
  preferred_airlines: string[]; avoid_layovers: boolean;
  preferred_departure_period?: string | null; must_haves: string[]; nice_to_haves: string[];
  notes: string[]; extraction_method: "ai" | "fallback";
};
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const examples = [
  "A week in Japan in March, flexible by a few days. Prefer evening nonstop flights.",
  "A long weekend in New York next month. I prefer Alaska or Delta and hotels near transit.",
  "Visit Paris for 8 days this fall. Keep flights and hotels under $2,000."
];

export default function Home() {
  const [request, setRequest] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TripIntent | null>(null);
  const [error, setError] = useState("");
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!request.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/trips/interpret`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request })
      });
      if (!response.ok) throw new Error("The trip assistant couldn't process that request.");
      setResult(await response.json());
    } catch (err) { setError(err instanceof Error ? err.message : "Something went wrong."); }
    finally { setLoading(false); }
  }
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 py-8 md:px-10">
      <header className="flex items-center justify-between">
        <a href="/" className="text-xl font-bold tracking-tight">✈ TravelSmart</a>
        <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800">AI trip planner</span>
      </header>
      <section className="grid flex-1 items-center gap-12 py-16 lg:grid-cols-[1.05fr_.95fr]">
        <div>
          <p className="mb-4 text-sm font-semibold uppercase tracking-[.18em] text-emerald-700">Better dates. Better trips.</p>
          <h1 className="max-w-xl text-5xl font-semibold leading-[1.08] tracking-tight md:text-6xl">Your next trip, <span className="text-emerald-700">smarter.</span></h1>
          <p className="mt-6 max-w-lg text-lg leading-8 text-slate-600">Tell us where you want to go and what matters to you. TravelSmart will help find the dates, flights, stays, and rewards strategy that make the most sense.</p>
          <div className="mt-8 flex flex-wrap gap-2 text-sm text-slate-600">
            {["Flexible dates", "Flight + hotel value", "Airline preferences", "Points & miles"].map(item => <span key={item} className="rounded-full border border-slate-200 bg-white px-3 py-2">{item}</span>)}
          </div>
        </div>
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm md:p-8">
          <h2 className="text-2xl font-semibold">Where would you like to go?</h2>
          <p className="mt-2 text-sm leading-6 text-slate-500">No exact dates needed. Describe your ideal trip in your own words.</p>
          <form onSubmit={handleSubmit} className="mt-6">
            <label htmlFor="trip-request" className="mb-2 block text-sm font-medium">Your trip idea</label>
            <textarea id="trip-request" value={request} onChange={e => setRequest(e.target.value)} placeholder="I'd love to visit Tokyo for about a week in March..." className="min-h-36 w-full resize-y rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 outline-none transition focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100" />
            <div className="mt-3 flex flex-wrap gap-2">
              {examples.map(example => <button key={example} type="button" onClick={() => setRequest(example)} className="rounded-full bg-slate-100 px-3 py-2 text-left text-xs text-slate-600 transition hover:bg-emerald-50 hover:text-emerald-800">Try an example</button>)}
            </div>
            <button type="submit" disabled={loading || !request.trim()} className="mt-5 w-full rounded-xl bg-emerald-700 px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50">{loading ? "Understanding your trip..." : "Understand my trip →"}</button>
          </form>
          {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}
          {result && <section className="mt-6 rounded-2xl border border-emerald-100 bg-emerald-50/70 p-4" aria-live="polite">
            <div className="flex items-center justify-between gap-3"><h3 className="font-semibold">Here&apos;s what I understood</h3><span className="rounded-full bg-white px-2 py-1 text-[11px] font-medium text-emerald-800">{result.extraction_method === "ai" ? "AI interpreted" : "Demo fallback"}</span></div>
            <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div><dt className="text-slate-500">Destination</dt><dd className="font-medium">{result.destination ?? "Not specified"}</dd></div>
              <div><dt className="text-slate-500">Trip length</dt><dd className="font-medium">{result.trip_length_days ? `${result.trip_length_days} days` : "Flexible"}</dd></div>
              <div><dt className="text-slate-500">Travel window</dt><dd className="font-medium">{result.earliest_departure ?? "Flexible"} – {result.latest_departure ?? "Flexible"}</dd></div>
              <div><dt className="text-slate-500">Budget</dt><dd className="font-medium">{result.budget_total ? `${result.currency} ${result.budget_total.toLocaleString()}` : "Not specified"}</dd></div>
            </dl>
            <div className="mt-4 space-y-2 text-sm">
              <p><strong>Airlines:</strong> {result.preferred_airlines.join(", ") || "No preference specified"}</p>
              <p><strong>Nonstop:</strong> {result.avoid_layovers ? "Requested" : "Flexible"}</p>
              <p><strong>Departure time:</strong> {result.preferred_departure_period ?? "Flexible"}</p>
              {result.must_haves.length > 0 && <p><strong>Must-haves:</strong> {result.must_haves.join(", ")}</p>}
              {result.nice_to_haves.length > 0 && <p><strong>Preferences:</strong> {result.nice_to_haves.join(", ")}</p>}
            </div>
            <p className="mt-4 text-xs leading-5 text-slate-500">This is the preference-understanding prototype. Live flight and hotel prices are not connected yet, so no prices or availability are being quoted.</p>
          </section>}
        </div>
      </section>
      <footer className="border-t border-slate-200 py-5 text-xs text-slate-500">TravelSmart · Plan flexibly. Travel wisely.</footer>
    </main>
  );
}
