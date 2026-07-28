"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { ManaSymbol } from "@/components/ManaSymbol";
import DeckView from "@/components/DeckView";

interface CommanderInfo {
  name: string;
  type_line: string;
  color_identity: string[];
  art_crop: string;
  image: string;
}

interface StrategyData {
  gameplan: string;
  early_game: string;
  mid_game: string;
  late_game: string;
  key_actions: string[];
  key_cards: string[];
  ramp: string[];
  draw: string[];
  removal: string[];
  wipes: string[];
}

interface DeckData {
  commander: string;
  sections: Record<string, string[]>;
  prices: Record<string, number>;
  total_price: number;
  card_count: number;
  warnings?: string[];
  strategy?: StrategyData;
}

const BUILD_LOG_STEPS = [
  { icon: "🔍", text: "Validating commander rules…" },
  { icon: "📡", text: "Fetching EDHREC recommendations…" },
  { icon: "🗂️", text: "Scanning your card collection…" },
  { icon: "🐉", text: "Searching for creatures…" },
  { icon: "💎", text: "Looking for mana rocks and ramp…" },
  { icon: "⚡", text: "Picking removal and interaction spells…" },
  { icon: "📖", text: "Finding card draw engines…" },
  { icon: "📜", text: "Selecting sorceries…" },
  { icon: "✨", text: "Choosing enchantments…" },
  { icon: "🏔️", text: "Building out the mana base…" },
  { icon: "⚖️", text: "Balancing the mana curve…" },
  { icon: "🔒", text: "Validating all 100 cards…" },
  { icon: "🎲", text: "Putting the finishing touches…" },
];

function BuildLog({ steps }: { steps: typeof BUILD_LOG_STEPS }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [steps.length]);

  return (
    <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1 scrollbar-hide">
      {steps.map((step, i) => {
        const isLatest = i === steps.length - 1;
        return (
          <div
            key={i}
            className={`flex items-center gap-3 text-sm animate-fade-slide-in transition-colors duration-500
              ${isLatest ? "text-white" : "text-gray-500"}`}
          >
            <span className={`text-lg shrink-0 transition-all duration-500 ${isLatest ? "opacity-100" : "opacity-30 text-base"}`}>
              {step.icon}
            </span>
            <span className={`transition-all duration-500 ${isLatest ? "font-medium" : ""}`}>
              {step.text}
            </span>
            {isLatest && (
              <span className="flex gap-1 ml-auto shrink-0">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: "300ms" }} />
              </span>
            )}
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}

export default function DeckPage() {
  const [artCrop, setArtCrop] = useState("");

  return (
    <main className="min-h-screen bg-gray-950 text-gray-100">
      {/* Commander art background — same treatment as commander page */}
      {artCrop && (
        <div
          className="fixed inset-0 opacity-10 bg-cover bg-center pointer-events-none transition-all duration-1000"
          style={{ backgroundImage: `url(${artCrop})` }}
        />
      )}

      <div className="relative z-10">
        <DeckBuilderContentWithArt
          onArtLoaded={(crop) => setArtCrop(crop)}
        />
      </div>
    </main>
  );
}

// Thin wrapper that reads commander name from sessionStorage and reports art_crop up to DeckPage
function DeckBuilderContentWithArt({
  onArtLoaded,
}: {
  onArtLoaded: (artCrop: string) => void;
}) {
  const [commanderName, setCommanderName] = useState("");

  useEffect(() => {
    const stored = sessionStorage.getItem("deckCommanderName") ?? "";
    setCommanderName(stored);
  }, []);

  const [info, setInfo]               = useState<CommanderInfo | null>(null);
  const [ownedOnly, setOwnedOnly]     = useState(false);
  const [lands, setLands]             = useState(36);
  const [building, setBuilding]       = useState(false);
  const [buildLog, setBuildLog]       = useState<typeof BUILD_LOG_STEPS>([]);
  const [builtDeck, setBuiltDeck]     = useState<DeckData | null>(null);
  const [error, setError]             = useState<string | null>(null);
  const [collectionCount, setCollectionCount] = useState(0);

  const logTimerRef   = useRef<ReturnType<typeof setInterval> | null>(null);
  const stepIndexRef  = useRef(0);

  useEffect(() => {
    if (!commanderName) return;
    fetch(`/api/commanders/info?name=${encodeURIComponent(commanderName)}`)
      .then(r => r.ok ? r.json() : null)
      .then((d: CommanderInfo | null) => {
        if (d) {
          setInfo(d);
          onArtLoaded(d.art_crop ?? "");
        }
      })
      .catch(() => {});
    fetch("/api/collection/status")
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setCollectionCount(d.count); })
      .catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [commanderName]);

  useEffect(() => () => { if (logTimerRef.current) clearInterval(logTimerRef.current); }, []);

  function startLogAnimation() {
    stepIndexRef.current = 0;
    setBuildLog([BUILD_LOG_STEPS[0]]);
    logTimerRef.current = setInterval(() => {
      stepIndexRef.current += 1;
      if (stepIndexRef.current < BUILD_LOG_STEPS.length) {
        setBuildLog(prev => [...prev, BUILD_LOG_STEPS[stepIndexRef.current]]);
      }
    }, 1400);
  }

  function stopLogAnimation() {
    if (logTimerRef.current) {
      clearInterval(logTimerRef.current);
      logTimerRef.current = null;
    }
  }

  async function handleBuild() {
    if (!commanderName) return;
    setBuilding(true);
    setError(null);
    setBuiltDeck(null);
    setBuildLog([]);
    startLogAnimation();
    try {
      const params = new URLSearchParams({
        commander: commanderName,
        owned_only: ownedOnly.toString(),
        lands: lands.toString(),
      });
      const res = await fetch(`/api/deck/build?${params}`, { method: "POST" });
      if (!res.ok) {
        const data = await res.json().catch(() => ({})) as { detail?: string };
        throw new Error(data.detail ?? `Build failed (${res.status})`);
      }
      const deck: DeckData = await res.json();
      setBuiltDeck(deck);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      stopLogAnimation();
      setBuilding(false);
    }
  }

  if (!commanderName) {
    return (
      <div className="text-center py-20 text-gray-500">
        No commander selected.{" "}
        <Link href="/commander" className="text-indigo-400 hover:underline">
          Go back
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-10 space-y-8">
      <Link
        href="/commander"
        className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to commanders
      </Link>

      <div className="space-y-1">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold text-white">{commanderName}</h1>
          {info?.color_identity && info.color_identity.length > 0 && (
            <div className="flex gap-1">
              {info.color_identity.map(c => (
                <ManaSymbol key={c} symbol={c} className="w-6 h-6" />
              ))}
            </div>
          )}
        </div>
        {info?.type_line && (
          <p className="text-indigo-300 text-sm">{info.type_line}</p>
        )}
      </div>

      {!builtDeck && (
        <div className="bg-gray-800/60 border border-gray-700/60 rounded-2xl p-6 space-y-6 backdrop-blur-sm">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
            Build Options
          </h2>

          <div className="flex flex-wrap gap-8 items-center">
            <label
              className={`flex items-center gap-3 select-none ${
                collectionCount === 0 ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
              }`}
            >
              <button
                type="button"
                role="switch"
                aria-checked={ownedOnly}
                onClick={() => collectionCount > 0 && setOwnedOnly(v => !v)}
                className={`w-10 h-6 rounded-full transition-colors relative flex items-center px-0.5
                  ${ownedOnly ? "bg-emerald-500" : "bg-gray-600"}`}
              >
                <span
                  className={`w-5 h-5 rounded-full bg-white shadow transition-transform
                    ${ownedOnly ? "translate-x-4" : "translate-x-0"}`}
                />
              </button>
              <span className="text-sm text-gray-300">
                Owned cards only
                {collectionCount === 0 && (
                  <span className="ml-1.5 text-xs text-gray-500">(upload a collection first)</span>
                )}
              </span>
            </label>

            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-400">Target lands</span>
              <input
                type="number"
                min={30}
                max={45}
                value={lands}
                onChange={e =>
                  setLands(Math.min(45, Math.max(30, parseInt(e.target.value) || 36)))
                }
                className="w-16 bg-gray-700 border border-gray-600 rounded-lg px-2 py-1.5
                           text-white text-sm text-center focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <button
            onClick={handleBuild}
            disabled={building}
            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500
                       disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold
                       px-8 py-3 rounded-xl transition text-sm"
          >
            {building ? (
              <>
                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Building deck…
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                Build Deck
              </>
            )}
          </button>

          {building && buildLog.length > 0 && (
            <div className="border-t border-gray-700/60 pt-5">
              <div className="text-xs text-gray-500 uppercase tracking-widest mb-3 font-medium">
                Building your deck
              </div>
              <BuildLog steps={buildLog} />
            </div>
          )}

          {error && (
            <div className="bg-red-900/30 border border-red-700/50 rounded-xl px-4 py-3 text-red-300 text-sm">
              {error}
            </div>
          )}
        </div>
      )}

      {builtDeck && info && (
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2 text-emerald-400 font-medium text-sm">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Deck ready — {builtDeck.card_count} cards
            </div>
            <button
              onClick={() => { setBuiltDeck(null); setError(null); setBuildLog([]); }}
              className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-white
                         transition bg-gray-800 hover:bg-gray-700 border border-gray-700
                         rounded-lg px-3 py-1.5"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Rebuild
            </button>
          </div>

          {/* Supplement / quality warnings */}
          {builtDeck.warnings && builtDeck.warnings.length > 0 && (
            <div className="space-y-2">
              {builtDeck.warnings.map((w, i) => {
                const isSupplementWarning = w.includes("collection only provided") || w.includes("card pool");
                return (
                  <div
                    key={i}
                    className={`flex items-start gap-3 rounded-xl px-4 py-3 text-sm border
                      ${isSupplementWarning
                        ? "bg-amber-900/30 border-amber-700/60 text-amber-200"
                        : "bg-gray-800/60 border-gray-700/60 text-gray-300"
                      }`}
                  >
                    <span className="shrink-0 mt-0.5 text-base">
                      {isSupplementWarning ? "⚠️" : "ℹ️"}
                    </span>
                    <span>{w}</span>
                  </div>
                );
              })}
            </div>
          )}

          <DeckView
            commander={{
              name: commanderName,
              colors: info.color_identity,
              color_names: info.color_identity,
              type_line: info.type_line,
            }}
            deckData={builtDeck}
          />
        </div>
      )}
    </div>
  );
}
