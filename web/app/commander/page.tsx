"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ManaSymbol, ManaCost, OracleText } from "@/components/ManaSymbol";

// ── Types ──────────────────────────────────────────────────────────────────

interface SearchResult {
  name: string;
  colors: string[];
  type_line: string;
  in_collection: boolean;
  has_deck: boolean;
}

interface CardFace {
  name: string;
  mana_cost: string;
  type_line: string;
  oracle_text: string;
  image: string;
  art_crop: string;
}

interface CommanderInfo {
  name: string;
  type_line: string;
  oracle_text: string;
  mana_cost: string;
  cmc: number;
  color_identity: string[];
  edhrec_rank: number | null;
  image: string;
  art_crop: string;
  price: number | null;
  tcgplayer_url: string;
  has_deck: boolean;
  faces: CardFace[];
}

// ── Mana symbol helpers ────────────────────────────────────────────────────

function ColorPip({ color }: { color: string }) {
  return <ManaSymbol symbol={color} className="w-5 h-5" />;
}

// ── EDHREC rank helpers ────────────────────────────────────────────────────

function rankTier(rank: number | null): { label: string; color: string; bar: number } {
  if (rank === null) return { label: "Unranked", color: "text-gray-500", bar: 0 };
  if (rank <= 500)   return { label: "Top commander",  color: "text-yellow-400", bar: 100 };
  if (rank <= 1500)  return { label: "Very popular",   color: "text-green-400",  bar: 75  };
  if (rank <= 3000)  return { label: "Popular",        color: "text-blue-400",   bar: 50  };
  if (rank <= 6000)  return { label: "Moderate",       color: "text-gray-300",   bar: 25  };
  return               { label: "Niche",           color: "text-gray-500",   bar: 10  };
}

// ── Search dropdown ────────────────────────────────────────────────────────

function SearchBox({
  onSelect,
  ownedOnly,
  collectionVersion,
}: {
  onSelect: (name: string) => void;
  ownedOnly: boolean;
  collectionVersion: number;
}) {
  const [query, setQuery]           = useState("");
  const [rawResults, setRawResults] = useState<SearchResult[]>([]);
  const [open, setOpen]             = useState(false);
  const [activeIdx, setActiveIdx]   = useState(-1);
  const containerRef                = useRef<HTMLDivElement>(null);
  const debounceRef                 = useRef<ReturnType<typeof setTimeout> | null>(null);
  const justPickedRef               = useRef("");
  const fullListRef                 = useRef<SearchResult[]>([]);

  const results = ownedOnly ? rawResults.filter(r => r.in_collection) : rawResults;

  // Bust the cache whenever the collection changes (upload / delete)
  useEffect(() => {
    fullListRef.current = [];
    setRawResults([]);
  }, [collectionVersion]);

  const search = useCallback(async (q: string) => {
    // Serve the cached full list instantly when the input is cleared
    if (!q.trim() && fullListRef.current.length > 0) {
      setRawResults(fullListRef.current);
      setOpen(true);
      setActiveIdx(-1);
      return;
    }
    const res = await fetch(`/api/commanders/search?q=${encodeURIComponent(q)}`);
    const data: SearchResult[] = await res.json();
    if (!q.trim()) fullListRef.current = data;
    setRawResults(data);
    setOpen(true);
    setActiveIdx(-1);
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query === justPickedRef.current && query !== "") return;
    if (!query.trim()) { search(""); return; }
    debounceRef.current = setTimeout(() => search(query), 250);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, search]);

  useEffect(() => {
    function outside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", outside);
    return () => document.removeEventListener("mousedown", outside);
  }, []);

  function pick(r: SearchResult) {
    justPickedRef.current = r.name;
    setQuery(r.name);
    setOpen(false);
    onSelect(r.name);
  }

  function onKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setActiveIdx(i => Math.min(i + 1, results.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActiveIdx(i => Math.max(i - 1, 0)); }
    else if (e.key === "Enter" && activeIdx >= 0) pick(results[activeIdx]);
    else if (e.key === "Escape") setOpen(false);
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-xl mx-auto">
      <div className="relative flex items-center">
        <span className="absolute left-4 text-gray-400 pointer-events-none">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
          </svg>
        </span>
        <input
          type="text"
          value={query}
          onChange={e => { justPickedRef.current = ""; setQuery(e.target.value); }}
          onFocus={() => { if (!query) search(""); else if (query !== justPickedRef.current) search(query); }}
          onKeyDown={onKey}
          placeholder="Search for a commander…"
          className="w-full bg-gray-800/80 border border-gray-700 rounded-xl pl-12 pr-4 py-4 text-white
                     placeholder-gray-500 text-lg focus:outline-none focus:border-indigo-500
                     focus:ring-2 focus:ring-indigo-500/30 transition backdrop-blur-sm"
        />
      </div>

      {open && results.length > 0 && (
        <div className="absolute z-50 mt-2 w-full bg-gray-900 border border-gray-700 rounded-xl
                        shadow-2xl overflow-hidden max-h-80 flex flex-col">
          <ul className="overflow-y-auto">
            {results.map((r, i) => (
              <li key={r.name}>
                <button
                  onMouseDown={() => pick(r)}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left transition
                    ${i === activeIdx ? "bg-indigo-600" : "hover:bg-gray-800"}`}
                >
                  <div className="flex gap-1 shrink-0">
                    {r.colors.length === 0
                      ? <ColorPip color="C" />
                      : r.colors.map(c => <ColorPip key={c} color={c} />)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-white truncate">{r.name}</div>
                    <div className="text-xs text-gray-400 truncate">{r.type_line}</div>
                  </div>
                  <div className="shrink-0 flex flex-col items-end gap-1">
                    {r.in_collection && (
                      <span className="text-xs bg-emerald-700/50 text-emerald-300 rounded-full px-2 py-0.5">
                        owned
                      </span>
                    )}
                    {r.has_deck && (
                      <span className="text-xs bg-indigo-600/60 text-indigo-200 rounded-full px-2 py-0.5">
                        deck ready
                      </span>
                    )}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── EDHREC commander data ──────────────────────────────────────────────────

interface EdhrecData {
  slug: string;
  num_decks: number;
  commander_rank: number | null;
  themes: { name: string; num_decks: number; href: string }[];
}

function commanderStrength(rank: number | null, num_decks: number): { label: string; color: string; detail: string } {
  if (rank === null) return { label: "Unknown", color: "text-gray-500", detail: "No data" };
  if (rank <= 25)  return { label: "Elite",       color: "text-yellow-300", detail: "Top 25 commander globally" };
  if (rank <= 100) return { label: "Tier 1",      color: "text-yellow-400", detail: "Top 100 — extremely popular" };
  if (rank <= 300) return { label: "Tier 2",      color: "text-green-400",  detail: "Top 300 — very strong pick" };
  if (rank <= 700) return { label: "Competitive", color: "text-blue-400",   detail: "Top 700 — solid choice" };
  if (rank <= 1500)return { label: "Moderate",    color: "text-gray-300",   detail: "Mid-range popularity" };
  return             { label: "Casual",        color: "text-gray-500",   detail: "Niche or budget pick" };
}

// ── Printing type ──────────────────────────────────────────────────────────

interface Printing {
  image: string;
  set: string;
  year: string;
  usd: number | null;
  usd_foil: number | null;
}

// ── Commander detail panel ─────────────────────────────────────────────────

function CommanderDetail({ info }: { info: CommanderInfo }) {
  const tier = rankTier(info.edhrec_rank);
  const router = useRouter();

  const [printings, setPrintings]         = useState<Printing[]>([]);
  const [printIdx, setPrintIdx]           = useState(0);
  const [showPrints, setShowPrints]       = useState(false);
  const [loadingPrints, setLoadingPrints] = useState(false);

  const [faceIdx, setFaceIdx]             = useState(0);

  const [edhrecData, setEdhrecData]       = useState<EdhrecData | null>(null);
  const [edhrecLoading, setEdhrecLoading] = useState(false);

  // Live price fetched from Scryfall when the DB has no price
  const [livePrice, setLivePrice]         = useState<number | null>(null);
  const [livePriceFoil, setLivePriceFoil] = useState<number | null>(null);

  const isCommanderFace = (f: CardFace) =>
    f.type_line.includes("Legendary") &&
    (f.type_line.includes("Creature") || f.type_line.includes("Planeswalker"));
  const hasFaces = info.faces.length >= 2 && info.faces.every(isCommanderFace);

  // Reset when a new commander is loaded
  useEffect(() => {
    setPrintings([]);
    setPrintIdx(0);
    setShowPrints(false);
    setFaceIdx(0);
    setEdhrecData(null);
    setLivePrice(null);
    setLivePriceFoil(null);
    setEdhrecLoading(true);

    fetch(`/api/commanders/edhrec?name=${encodeURIComponent(info.name)}`)
      .then(r => r.ok ? r.json() as Promise<EdhrecData> : null)
      .then(d => setEdhrecData(d))
      .catch(() => setEdhrecData(null))
      .finally(() => setEdhrecLoading(false));

    // If the DB has no price, search all printings on Scryfall and pick the cheapest
    if (!info.price) {
      const q = encodeURIComponent(`!"${info.name}"`);
      fetch(`https://api.scryfall.com/cards/search?q=${q}&unique=prints&order=released&dir=desc`)
        .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
        .then(d => {
          if (!d?.data?.length) { console.warn('[price] no printings found for', info.name); return; }
          type PricedCard = { prices?: { usd?: string | null; usd_foil?: string | null } };
          const all = d.data as PricedCard[];
          console.log('[price] printings:', all.length, '| sample prices:', all.slice(0,3).map(c => c.prices));
          // Prefer cheapest regular price; fall back to cheapest foil price
          const withUsd  = all.filter(c => c.prices?.usd).sort((a,b) => parseFloat(a.prices!.usd!) - parseFloat(b.prices!.usd!));
          const withFoil = all.filter(c => c.prices?.usd_foil).sort((a,b) => parseFloat(a.prices!.usd_foil!) - parseFloat(b.prices!.usd_foil!));
          if (withUsd.length)  setLivePrice(parseFloat(withUsd[0].prices!.usd!));
          else if (withFoil.length) setLivePrice(parseFloat(withFoil[0].prices!.usd_foil!));
          if (withFoil.length) setLivePriceFoil(parseFloat(withFoil[0].prices!.usd_foil!));
          console.log('[price] set livePrice=', withUsd[0]?.prices?.usd ?? withFoil[0]?.prices?.usd_foil ?? 'none');
        })
        .catch(e => console.error('[price] fetch failed:', e));
    }
  }, [info.name, info.price]);

  const fetchPrintings = useCallback(async () => {
    if (printings.length > 0) { setShowPrints(true); return; }
    setLoadingPrints(true);
    try {
      const q = encodeURIComponent(`!"${info.name}"`);
      const res = await fetch(
        `https://api.scryfall.com/cards/search?q=${q}&unique=prints&order=released&dir=desc`
      );
      const data = await res.json();
      type RawCard = {
        image_uris?: { normal: string };
        card_faces?: Array<{ image_uris?: { normal: string } }>;
        set_name?: string;
        released_at?: string;
        prices?: { usd?: string; usd_foil?: string };
      };
      const imgs: Printing[] = (data.data ?? [])
        .map((c: RawCard) => ({
          image: c.image_uris?.normal ?? c.card_faces?.[0]?.image_uris?.normal ?? "",
          set: c.set_name ?? "",
          year: (c.released_at ?? "").slice(0, 4),
          usd:      c.prices?.usd      ? parseFloat(c.prices.usd)      : null,
          usd_foil: c.prices?.usd_foil ? parseFloat(c.prices.usd_foil) : null,
        }))
        .filter((p: Printing) => p.image);
      setPrintings(imgs);
      setShowPrints(true);
      setPrintIdx(0);
    } catch { /* ignore */ }
    finally { setLoadingPrints(false); }
  }, [info.name, printings.length]);

  const activePrinting  = showPrints && printings.length > 0 ? printings[printIdx] : null;
  const activeFace      = hasFaces ? info.faces[faceIdx] : null;

  // Printings mode overrides face for the image; otherwise use face image if available
  const activeImage     = activePrinting?.image ?? activeFace?.image ?? info.image;
  const activeOracleText = activeFace?.oracle_text ?? info.oracle_text;
  const activeManaCost  = activeFace?.mana_cost ?? info.mana_cost;
  const activeTypeLine  = activeFace?.type_line ?? info.type_line;

  const activeUsd       = activePrinting ? activePrinting.usd      : (info.price != null && info.price > 0 ? info.price : livePrice);
  const activeUsdFoil   = activePrinting ? activePrinting.usd_foil : livePriceFoil;

  return (
    <div className="mt-10 flex flex-col lg:flex-row gap-8 items-start">
      {/* Card image + arts cycling */}
      <div className="shrink-0 w-full lg:w-72 xl:w-80 space-y-3">
        <div className="relative">
          {activeImage ? (
            <img
              src={activeImage}
              alt={info.name}
              className="w-full rounded-2xl shadow-2xl shadow-black/60 ring-1 ring-white/10"
            />
          ) : (
            <div className="w-full aspect-[5/7] bg-gray-800 rounded-2xl flex items-center justify-center ring-1 ring-white/10">
              <span className="text-6xl opacity-30">🃏</span>
            </div>
          )}
          {showPrints && printings.length > 1 && (
            <div className="absolute bottom-2 left-0 right-0 flex items-center justify-between px-2">
              <button
                onClick={() => setPrintIdx(i => Math.max(i - 1, 0))}
                disabled={printIdx === 0}
                className="bg-black/60 hover:bg-black/80 text-white rounded-full w-7 h-7 flex items-center justify-center disabled:opacity-30 transition text-lg"
              >‹</button>
              <span className="bg-black/60 text-white text-xs px-2 py-0.5 rounded-full">
                {printIdx + 1} / {printings.length}
              </span>
              <button
                onClick={() => setPrintIdx(i => Math.min(i + 1, printings.length - 1))}
                disabled={printIdx === printings.length - 1}
                className="bg-black/60 hover:bg-black/80 text-white rounded-full w-7 h-7 flex items-center justify-center disabled:opacity-30 transition text-lg"
              >›</button>
            </div>
          )}
        </div>

        {showPrints && printings[printIdx] && (
          <div className="text-xs text-gray-400 text-center italic">
            {printings[printIdx].set} ({printings[printIdx].year})
          </div>
        )}

        {/* Flip button for double-faced cards */}
        {hasFaces && !showPrints && (
          <button
            onClick={() => setFaceIdx(i => i === 0 ? 1 : 0)}
            className="w-full text-xs bg-gray-800 hover:bg-gray-700 border border-amber-700/50
                       text-amber-300 hover:text-amber-200 rounded-xl py-2 transition flex items-center justify-center gap-2"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {faceIdx === 0
              ? `Transform → ${info.faces[1].name}`
              : `← ${info.faces[0].name}`}
          </button>
        )}

        <button
          onClick={fetchPrintings}
          disabled={loadingPrints}
          className="w-full text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300
                     hover:text-white rounded-xl py-2 transition disabled:opacity-50"
        >
          {loadingPrints ? "Loading arts…"
            : showPrints ? `Showing all ${printings.length} printings`
            : "See other arts"}
        </button>
      </div>

      {/* Info panel */}
      <div className="flex-1 min-w-0 space-y-6">
        {/* Name */}
        <h1 className="text-3xl xl:text-4xl font-bold text-white leading-tight">{info.name}</h1>

        {/* Mana cost */}
        {activeManaCost && (
          <div>
            <div className="text-xs text-gray-400 uppercase tracking-widest mb-1.5">Mana Cost</div>
            <ManaCost cost={activeManaCost} size="w-6 h-6" />
          </div>
        )}

        {/* Type + CMC + identity */}
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <span className="text-indigo-300 font-medium">{activeTypeLine}</span>
          <span className="bg-gray-700/60 rounded-lg px-3 py-1 text-gray-300">
            CMC <span className="text-white font-bold ml-1">{info.cmc}</span>
          </span>
          {info.color_identity.length > 0 && (
            <div className="flex gap-1">
              {info.color_identity.map(c => <ColorPip key={c} color={c} />)}
            </div>
          )}
        </div>

        {/* Oracle text */}
        {activeOracleText && (
          <div className="bg-gray-800/60 border border-gray-700/60 rounded-xl p-5 text-sm text-gray-200 leading-relaxed">
            {hasFaces && (
              <div className="text-xs text-amber-400/70 mb-2 font-medium">
                {info.faces[faceIdx].name}
              </div>
            )}
            <OracleText text={activeOracleText} symbolSize="w-4 h-4" />
          </div>
        )}

        {/* Commander rank box — full width */}
        <div className="bg-gray-800/60 border border-gray-700/60 rounded-xl p-5 space-y-4">
          <div className="text-xs text-gray-400 uppercase tracking-widest font-medium">Commander Rank</div>
          {edhrecLoading ? (
            <div className="flex items-center gap-2 text-gray-500 text-sm">
              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Loading from EDHREC…
            </div>
          ) : edhrecData ? (() => {
            const strength = commanderStrength(edhrecData.commander_rank, edhrecData.num_decks);
            return (
              <div className="space-y-4">
                <div className="flex flex-wrap items-end gap-6">
                  {edhrecData.commander_rank !== null && (
                    <div>
                      <div className="text-3xl font-bold text-white">
                        #{edhrecData.commander_rank.toLocaleString()}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">among commanders</div>
                    </div>
                  )}
                  {edhrecData.num_decks > 0 && (
                    <div>
                      <div className="text-2xl font-bold text-indigo-300">
                        {edhrecData.num_decks.toLocaleString()}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">decks on EDHREC</div>
                    </div>
                  )}
                  <div>
                    <span className={`text-sm font-bold ${strength.color}`}>{strength.label}</span>
                    <div className="text-xs text-gray-500 mt-0.5">{strength.detail}</div>
                  </div>
                </div>

                {edhrecData.themes.length > 0 && (
                  <div className="space-y-2">
                    <div className="text-xs text-gray-500 uppercase tracking-wider">Top ways to play</div>
                    <div className="flex flex-wrap gap-2">
                      {edhrecData.themes.map((t, i) => (
                        <div
                          key={i}
                          className="flex items-center gap-2 bg-indigo-900/40 border border-indigo-700/50
                                     rounded-lg px-3 py-2"
                        >
                          <span className="text-indigo-200 font-medium text-sm">{t.name}</span>
                          {t.num_decks > 0 && (
                            <span className="text-xs text-gray-400">{t.num_decks.toLocaleString()} decks</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })() : (
            <div className="text-gray-500 text-sm">Commander data unavailable</div>
          )}
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* EDHREC rank */}
          <div className="bg-gray-800/60 border border-gray-700/60 rounded-xl p-5 space-y-3">
            <div className="text-xs text-gray-400 uppercase tracking-widest font-medium">Card Inclusion Rank</div>
            {info.edhrec_rank !== null ? (
              <>
                <div className="text-3xl font-bold text-white">
                  #{info.edhrec_rank.toLocaleString()}
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className={`text-sm font-semibold ${tier.color}`}>{tier.label}</span>
                  </div>
                  <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ${
                        tier.bar >= 75 ? "bg-yellow-400" :
                        tier.bar >= 50 ? "bg-green-400"  :
                        tier.bar >= 25 ? "bg-blue-400"   : "bg-gray-500"
                      }`}
                      style={{ width: `${tier.bar}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-500 leading-relaxed">
                    How often this card appears across all EDH decks on EDHREC. #1 = Sol Ring. Commanders rank lower because they only appear in their own decks.
                  </div>
                </div>
              </>
            ) : (
              <div className="text-gray-500 text-sm">Not ranked on EDHREC</div>
            )}
          </div>

          {/* Price */}
          <div className="bg-gray-800/60 border border-gray-700/60 rounded-xl p-5 space-y-2">
            <div className="text-xs text-gray-400 uppercase tracking-widest font-medium">Market Price</div>
            {activeUsd !== null && activeUsd > 0 ? (
              <div className="text-3xl font-bold text-green-400">${activeUsd.toFixed(2)}</div>
            ) : (
              <div className="text-gray-500 text-sm">Price not in local data</div>
            )}
            {activeUsdFoil !== null && activeUsdFoil > 0 && (
              <div className="text-sm text-yellow-400">✨ Foil ${activeUsdFoil.toFixed(2)}</div>
            )}
            <div className="text-xs text-gray-500">
              {showPrints && printings[printIdx] ? printings[printIdx].set : "Commander card only"}
            </div>
            {info.tcgplayer_url && (
              <a
                href={info.tcgplayer_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs bg-orange-600/20 hover:bg-orange-600/40
                           border border-orange-600/50 text-orange-300 hover:text-orange-200
                           rounded-lg px-3 py-1.5 transition font-medium"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                Buy on TCGPlayer
              </a>
            )}
          </div>
        </div>

        {/* Action */}
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => {
              sessionStorage.setItem("deckCommanderName", info.name);
              router.push("/deck");
            }}
            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white
                       font-semibold px-6 py-3 rounded-xl transition text-sm"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            Build Deck
          </button>
          {info.has_deck && (
            <Link
              href={`/?commander=${encodeURIComponent(info.name)}`}
              className="inline-flex items-center gap-2 bg-gray-700/60 hover:bg-gray-700 text-gray-200
                         font-medium px-6 py-3 rounded-xl transition text-sm border border-gray-600"
            >
              <span>🎴</span> View Pre-built Deck
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

// ── CSV format rules (must match API _VALID_NAME_COLS) ────────────────────
const VALID_NAME_COLS = ["name", "card name", "cardname"];

function validateCsvHeader(text: string): string | null {
  const firstLine = text.split(/\r?\n/)[0] ?? "";
  if (!firstLine.trim()) return "The file appears to be empty.";
  const cols = firstLine.split(",").map(c => c.replace(/^"|"$/g, "").toLowerCase().trim());
  if (!cols.some(c => VALID_NAME_COLS.includes(c))) {
    return (
      `Missing card-name column. The first row must contain one of: ${VALID_NAME_COLS.join(", ")}. ` +
      `Found: ${cols.join(", ") || "(none)"}.`
    );
  }
  return null;
}

// ── Collection upload panel ────────────────────────────────────────────────

function CollectionPanel({
  count,
  deckReady,
  onUploaded,
  onRemoved,
}: {
  count: number;
  deckReady: number;
  onUploaded: (count: number, decks: number) => void;
  onRemoved: () => void;
}) {
  const inputRef                        = useRef<HTMLInputElement>(null);
  const [uploading, setUploading]       = useState(false);
  const [removing, setRemoving]         = useState(false);
  const [confirming, setConfirming]     = useState(false);
  const [message, setMessage]           = useState<{ text: string; ok: boolean } | null>(null);
  const [showInfo, setShowInfo]         = useState(false);

  async function handleRemove() {
    setRemoving(true);
    setConfirming(false);
    setMessage(null);
    try {
      const res = await fetch("/api/collection", { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to remove collection");
      onRemoved();
    } catch (err) {
      setMessage({ text: (err as Error).message, ok: false });
    } finally {
      setRemoving(false);
    }
  }

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setMessage(null);

    // Client-side validation: read the header without uploading
    const headerText = await file.slice(0, 512).text();
    const headerError = validateCsvHeader(headerText);
    if (headerError) {
      setMessage({ text: headerError, ok: false });
      if (inputRef.current) inputRef.current.value = "";
      return;
    }

    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch("/api/collection/upload?source=uploaded", { method: "POST", body: form });
      let data: Record<string, unknown> = {};
      try { data = await res.json(); } catch { /* non-JSON body — ignore, use status below */ }
      if (!res.ok) throw new Error((data.detail as string) ?? `Upload failed (${res.status})`);
      const added = data.added as number;
      const skipped = data.skipped as number;
      setMessage({ text: `Imported ${added.toLocaleString()} cards (${skipped} skipped)`, ok: true });
      const stats = await fetch("/api/collection/status").then(r => r.ok ? r.json() : null);
      onUploaded(stats?.count ?? added, stats?.deck_ready ?? 0);
    } catch (err) {
      setMessage({ text: (err as Error).message, ok: false });
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={handleFile}
      />

      {/* Upload button */}
      <button
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
        className="flex items-center gap-2 text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700
                   text-gray-300 hover:text-white rounded-lg px-3 py-1.5 transition disabled:opacity-50"
      >
        {uploading ? (
          <>
            <svg className="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Uploading…
          </>
        ) : (
          <>
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            {count > 0 ? "Replace collection" : "Upload collection CSV"}
          </>
        )}
      </button>

      {/* Info icon — click to toggle floating panel */}
      <div className="relative">
        <button
          onClick={() => setShowInfo(v => !v)}
          className={`transition ${showInfo ? "text-indigo-400" : "text-gray-500 hover:text-gray-300"}`}
          aria-label="CSV format requirements"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20A10 10 0 0012 2z" />
          </svg>
        </button>

        {showInfo && (
          <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 w-72 z-50">
            {/* Arrow */}
            <div className="flex justify-center">
              <div className="w-2.5 h-2.5 bg-gray-900 border-l border-t border-gray-700 rotate-45 -mb-1.5" />
            </div>
            <div className="bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 space-y-2 text-xs text-gray-300 shadow-2xl">
              <p className="font-semibold text-white">CSV format requirements</p>
              <p>
                Must be a <span className="text-indigo-300">.csv</span> with a header row containing a column
                named <span className="text-indigo-300">Name</span> (also:{" "}
                <span className="text-indigo-300">Card Name</span>,{" "}
                <span className="text-indigo-300">CardName</span>).
              </p>
              <div className="font-mono bg-gray-950 rounded-lg px-3 py-2 text-gray-400 leading-relaxed whitespace-pre">
                {`Name\nSol Ring\nLightning Bolt\nCommand Tower`}
              </div>
              <p className="text-gray-500">
                Optional: <span className="italic">Count, Set, Foil</span> columns.
                Moxfield, ManaBox, and Archidekt exports work as-is.
              </p>
            </div>
          </div>
        )}
      </div>

      {count > 0 && (
        <div className="flex items-center gap-2">
          <div className="flex flex-col gap-0.5">
            <span className="text-xs text-indigo-400 font-medium">
              {deckReady} pre-built deck{deckReady !== 1 ? "s" : ""} available
            </span>
            <span className="text-xs text-emerald-400 font-medium">
              {count.toLocaleString()} cards in collection
            </span>
          </div>

          {/* Remove collection — two-step confirm */}
          {!confirming ? (
            <button
              onClick={() => setConfirming(true)}
              disabled={removing}
              className="ml-1 text-gray-600 hover:text-red-400 transition disabled:opacity-40"
              title="Remove collection"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M9 7V4h6v3M4 7h16" />
              </svg>
            </button>
          ) : (
            <div className="flex items-center gap-1.5 ml-1">
              <span className="text-xs text-gray-400">Remove?</span>
              <button
                onClick={handleRemove}
                disabled={removing}
                className="text-xs text-red-400 hover:text-red-300 font-medium transition disabled:opacity-40"
              >
                {removing ? "…" : "Yes"}
              </button>
              <button
                onClick={() => setConfirming(false)}
                className="text-xs text-gray-500 hover:text-gray-300 transition"
              >
                No
              </button>
            </div>
          )}
        </div>
      )}

      {message && (
        <div className={`w-full flex items-start gap-2 text-xs rounded-lg px-3 py-2
          ${message.ok
            ? "bg-emerald-900/30 border border-emerald-700/50 text-emerald-300"
            : "bg-red-900/30 border border-red-700/50 text-red-300"}`}
        >
          <span className="shrink-0 mt-0.5">{message.ok ? "✓" : "✗"}</span>
          <span>{message.text}</span>
        </div>
      )}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function CommanderPage() {
  const [selectedName, setSelectedName]   = useState<string | null>(null);
  const [info, setInfo]                   = useState<CommanderInfo | null>(null);
  const [loadingInfo, setLoadingInfo]     = useState(false);
  const [infoError, setInfoError]         = useState<string | null>(null);

  const [ownedOnly, setOwnedOnly]         = useState(false);
  const [collectionCount, setCollectionCount] = useState(0);
  const [deckReady, setDeckReady]         = useState(0);
  const [collectionVersion, setCollectionVersion] = useState(0);

  // Fetch collection stats on mount
  useEffect(() => {
    fetch("/api/collection/status")
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) { setCollectionCount(d.count); setDeckReady(d.deck_ready); } })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedName) { setInfo(null); return; }
    setInfo(null);
    setInfoError(null);
    setLoadingInfo(true);
    fetch(`/api/commanders/info?name=${encodeURIComponent(selectedName)}`)
      .then(r => { if (!r.ok) throw new Error("Not found"); return r.json() as Promise<CommanderInfo>; })
      .then(setInfo)
      .catch(e => setInfoError((e as Error).message))
      .finally(() => setLoadingInfo(false));
  }, [selectedName]);

  return (
    <main className="min-h-screen bg-gray-950 text-gray-100">
      {/* Art crop hero background */}
      {info?.art_crop && (
        <div
          className="fixed inset-0 opacity-10 bg-cover bg-center pointer-events-none transition-all duration-1000"
          style={{ backgroundImage: `url(${info.art_crop})` }}
        />
      )}

      <div className="relative z-10 max-w-5xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="flex items-center justify-center mb-10">
          <h1 className="text-lg font-bold text-white">Commander Browser</h1>
        </div>

        {/* Search + filters */}
        <div className="mb-2 space-y-3">
          {!selectedName && (
            <p className="text-center text-gray-400 text-base">
              Search your collection and explore any commander
            </p>
          )}

          <SearchBox onSelect={setSelectedName} ownedOnly={ownedOnly} collectionVersion={collectionVersion} />

          {/* Toolbar row */}
          <div className="flex flex-wrap items-center justify-between gap-3 px-1">
            {/* Owned-only toggle */}
            <button
              onClick={() => setOwnedOnly(v => !v)}
              className={`flex items-center gap-2 text-xs rounded-lg px-3 py-1.5 border transition font-medium
                ${ownedOnly
                  ? "bg-emerald-700/40 border-emerald-600 text-emerald-300"
                  : "bg-gray-800 border-gray-700 text-gray-400 hover:text-white hover:border-gray-600"
                } ${collectionCount === 0 ? "opacity-40 cursor-not-allowed" : ""}`}
              disabled={collectionCount === 0}
              title={collectionCount === 0 ? "Upload a collection first" : ""}
            >
              <span className={`w-2 h-2 rounded-full ${ownedOnly ? "bg-emerald-400" : "bg-gray-600"}`} />
              Owned only
            </button>

            {/* Collection upload */}
            <CollectionPanel
              count={collectionCount}
              deckReady={deckReady}
              onUploaded={(added, decks) => { setCollectionCount(added); setDeckReady(decks); setCollectionVersion(v => v + 1); }}
              onRemoved={() => { setCollectionCount(0); setDeckReady(0); setOwnedOnly(false); setCollectionVersion(v => v + 1); }}
            />
          </div>
        </div>

        {/* Loading */}
        {loadingInfo && (
          <div className="flex justify-center mt-16 text-gray-400 gap-3">
            <svg className="animate-spin w-6 h-6" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Loading commander…
          </div>
        )}

        {/* Error */}
        {infoError && (
          <div className="mt-8 bg-red-900/30 border border-red-700 rounded-xl px-6 py-4 text-red-300 text-sm">
            {infoError}
          </div>
        )}

        {/* Detail */}
        {info && !loadingInfo && <CommanderDetail info={info} />}

        {/* Empty state */}
        {!selectedName && !loadingInfo && (
          <div className="mt-20 text-center text-gray-600 space-y-3">
            <div className="text-6xl">⚔️</div>
            <p className="text-lg">Browse all MTG commanders</p>
            <p className="text-sm">Search any legendary creature or planeswalker</p>
          </div>
        )}
      </div>
    </main>
  );
}
