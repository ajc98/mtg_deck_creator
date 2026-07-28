"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { ManaSymbol, ManaCost } from "./ManaSymbol";

// ── Types ────────────────────────────────────────────────────────────────────

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
  deck_id?: string;
  commander: string;
  sections: Record<string, string[]>;
  prices: Record<string, number>;
  total_price: number;
  card_count: number;
  warnings?: string[];
  strategy?: StrategyData;
}

interface Commander {
  name: string;
  colors: string[];
  color_names: string[];
  type_line: string;
}

interface ScryfallCard {
  name: string;
  mana_cost?: string;
  cmc: number;
  type_line: string;
  oracle_text?: string;
  color_identity: string[];
  image_uris?: { normal: string; art_crop: string };
  card_faces?: Array<{ image_uris?: { normal: string } }>;
  prices: { usd?: string; usd_foil?: string };
  purchase_uris?: { tcgplayer?: string };
}

interface Printing {
  image: string;
  set: string;
  year: string;
  usd: number | null;
  usd_foil: number | null;
}

// ── Constants ────────────────────────────────────────────────────────────────

const SECTION_ORDER = [
  "Commander", "Creatures", "Planeswalkers", "Artifacts",
  "Enchantments", "Instants", "Sorceries", "Other", "Lands",
];

const SECTION_ICONS: Record<string, string> = {
  Commander: "👑", Creatures: "🐉", Planeswalkers: "⭐",
  Artifacts: "⚙️", Enchantments: "✨", Instants: "⚡",
  Sorceries: "📜", Other: "🃏", Lands: "🏔️",
};

const SECTION_DESCRIPTIONS: Record<string, string> = {
  Other: "Sagas, Battles, and other unusual card types that don't fit a standard category.",
};

// ── Archetype strategy guides ────────────────────────────────────────────────

interface ArchGuide {
  icon: string;
  gameplan: string;
  earlyGame: string;
  midGame: string;
  lateGame: string;
  keyActions: string[];
}

const ARCHETYPE_GUIDES: Record<string, ArchGuide> = {
  counters: {
    icon: "⚡",
    gameplan: "Build a dominant board state by placing and proliferating +1/+1 counters on your creatures. Your board snowballs exponentially — a few doublings turn 1/1s into 8/8s.",
    earlyGame: "Ramp first. Set up mana acceleration and play cheap creatures that enter with counters or generate them immediately.",
    midGame: "Activate proliferate effects every turn. Look for Doubling Season, Hardened Scales, or similar multiplicative effects. Each doubling compounds dramatically.",
    lateGame: "Your creatures grow out of control. Win through combat with towering threats, or use poison/infect counters as an alternate win condition.",
    keyActions: [
      "Proliferate every turn when possible — even one extra counter per permanent adds up fast",
      "Protect cards that double or multiply counters, they are the highest-priority removal targets",
      "Use sacrifice outlets to reset creatures and re-trigger enters-the-battlefield counter effects",
    ],
  },
  sacrifice: {
    icon: "💀",
    gameplan: "Generate repeated value by creating creatures and sacrificing them for profit. Death triggers and Aristocrats effects drain opponents while building your advantage.",
    earlyGame: "Establish a token producer AND a sacrifice outlet in your opening turns. Even 1/1 tokens become a value engine with the right setup.",
    midGame: "Create sacrifice loops: produce tokens, sacrifice for triggers, repeat. Drain life, draw cards, and build pressure. Ashnod's Altar or Phyrexian Altar are engine pieces.",
    lateGame: "Win through life drain (Blood Artist effects), combo off with infinite sacrifice loops, or swing with a massive token army after an Overrun effect.",
    keyActions: [
      "Always keep a sacrifice outlet open — never tap them unless you're going off",
      "Count drain triggers before attacking; you may win without ever going to combat",
      "Prioritize creatures that create tokens when they die or enter the battlefield",
    ],
  },
  tokens: {
    icon: "🐣",
    gameplan: "Flood the battlefield with creature tokens, then buff them with anthem effects or an Overrun to swing for lethal.",
    earlyGame: "Establish token producers as fast as possible. Any card that creates multiple tokens per turn is a priority.",
    midGame: "Build critical mass. Add anthem effects that buff all your tokens simultaneously. Width beats single large threats.",
    lateGame: "Cast a mass pump spell (Craterhoof Behemoth, Overrun, Triumph of the Hordes) and attack with everything for lethal.",
    keyActions: [
      "Look for ways to make tokens that produce OTHER tokens — cascading value multiplies quickly",
      "Keep a pump/overrun effect in hand as your win button, not as a tempo play",
      "Protect your token-doublers (Parallel Lives, Anointed Procession) at all costs",
    ],
  },
  graveyard: {
    icon: "⚰️",
    gameplan: "Use the graveyard as a second hand. Fill it aggressively with powerful cards and reanimate or recur them for free value.",
    earlyGame: "Self-mill and discard strategically. Get your best threats into the graveyard quickly — every discard is a setup.",
    midGame: "Start recurring threats. Reanimation spells are your 2-for-1s. The graveyard is an inexhaustible resource.",
    lateGame: "Reanimate your biggest threats repeatedly. Opponents exhaust their interaction; you never run out of threats.",
    keyActions: [
      "Discard deliberately — treat your graveyard as a toolbox, not a trash pile",
      "Keep recursion engines alive; without them your strategy stalls",
      "Watch for graveyard hate (Rest in Peace, Tormod's Crypt) — develop a backup plan",
    ],
  },
  dragons: {
    icon: "🐉",
    gameplan: "Ramp aggressively into expensive, game-ending Dragon threats. Even one or two Dragons in play is often enough to close out a game.",
    earlyGame: "Ramp, ramp, ramp. You need 6–8+ mana as fast as possible. Prioritize land ramp over artifact ramp for resilience.",
    midGame: "Land your first Dragon. Each one provides immediate board impact. Dragon Tempest or Warstorm Surge turns each Dragon into a Lightning Bolt.",
    lateGame: "Your Dragons overwhelm opponents through sheer power in combat. Stack flying threats and attack in waves.",
    keyActions: [
      "Always leave mana for a counterspell after casting your first big Dragon",
      "Dragon Tempest and haste enablers are must-haves — Dragons without haste are vulnerable on entry",
      "Prioritize Swiftfoot Boots / Lightning Greaves to protect your most important Dragon",
    ],
  },
  voltron: {
    icon: "⚔️",
    gameplan: "Suit up your commander with Auras and Equipment to deal 21 commander damage as fast as possible. Speed is everything.",
    earlyGame: "Deploy your commander turns 2-3. Equip or enchant immediately. Every turn of free attacks matters.",
    midGame: "Keep stacking equipment. Double strike + one strong pump spell = lethal in one turn. Protect your commander with hexproof/indestructible.",
    lateGame: "Once you have 10+ commander damage dealt to a player, they are forced to answer you. Push through the final 11+ damage.",
    keyActions: [
      "Count commander damage carefully — 21 commander damage kills a player regardless of their life total",
      "Prioritize hexproof and indestructible; a commander that dies costs you 2 extra mana each time",
      "Spread attacks across opponents to avoid becoming the single threat everyone focuses on",
    ],
  },
  combat: {
    icon: "⚔️",
    gameplan: "Win through repeated, efficient combat. Extra attack phases and on-attack triggers generate overwhelming card and damage advantage.",
    earlyGame: "Curve out aggressively. Cheap creatures that attack early establish presence and begin generating triggers.",
    midGame: "Get extra combat phases online. Every additional attack step doubles your damage output and trigger count.",
    lateGame: "Execute a turn with 3+ combat phases for lethal. Keep mana open for protection spells going into your win turn.",
    keyActions: [
      "Save your extra combat spells for the game-winning turn, not for incremental value",
      "Track each player's life total carefully and plan your lethal attack in advance",
      "Attack triggers (haste, double strike, trample) multiply with each extra combat phase",
    ],
  },
  spellslinger: {
    icon: "🪄",
    gameplan: "Cast instants and sorceries to trigger powerful payoff cards. Every spell you cast fires multiple effects simultaneously.",
    earlyGame: "Find and protect your payoffs (Guttersnipe, Niv-Mizzet, Thousand-Year Storm). Without payoffs, your spells do far less.",
    midGame: "Chain spells together. Copy effects (Fork, Twincast, Bonus Round) multiply your triggers. Build toward a chain-spell turn.",
    lateGame: "Go off: cast multiple spells in one turn, triggering each payoff multiple times for lethal damage or overwhelming card advantage.",
    keyActions: [
      "Count your spell payoffs before going off — waiting one turn for more payoffs is often correct",
      "Cantrips (draw-a-card spells) are your gas; prioritize them in the late game to stay ahead",
      "Hold a counterspell to protect your combo turn from disruption",
    ],
  },
  lifegain: {
    icon: "💚",
    gameplan: "Gain life in large quantities to trigger powerful payoff cards. Life total is a resource — spend it to gain advantage, then refill.",
    earlyGame: "Establish a consistent life-gain engine. Even 1-2 life per turn snowballs with the right payoffs in play.",
    midGame: "Multiply your lifegain with doublers (Nykthos Paragon, Heliod, Sun-Crowned). Each life gained triggers payoffs multiple times.",
    lateGame: "Win through drain effects, giant lifelinkers that are impossible to block profitably, or combo finishers enabled by large life totals.",
    keyActions: [
      "Prioritize 'whenever you gain life' payoffs over pure lifegain — triggers win games, raw life does not",
      "Opponents will remove your payoffs, not your life total — protect them aggressively",
      "Track your lifegain triggers; you'll chain far more than you expect in a single turn",
    ],
  },
  tribal: {
    icon: "👥",
    gameplan: "Fill the board with creatures of a shared tribe and benefit from cumulative synergies between them. Lords make every creature better.",
    earlyGame: "Curve out with tribal members. Each creature you add strengthens the others and sets up your tribal synergies.",
    midGame: "Find your tribal lords (grant +1/+1 to all). A single anthem makes your entire board threatening in combat.",
    lateGame: "Overwhelm opponents with a fully powered, lord-boosted army. Width and synergy beat individual powerful creatures.",
    keyActions: [
      "Tribal lords that buff all creatures of the type are your highest priority — protect them",
      "Changelings count as every creature type — look for hidden gems that fit any tribe",
      "Look for tribal synergies beyond just combat: draw, ramp, and removal within your tribe multiply your advantage",
    ],
  },
};

const DEFAULT_GUIDE: ArchGuide = {
  icon: "🎯",
  gameplan: "Build board presence, maintain card advantage, and execute your win condition before opponents can stabilize. Every card you play should advance your game plan.",
  earlyGame: "Set up your mana base and ramp. Get your commander into play and start developing your strategy. Prioritize ramp and draw.",
  midGame: "Maintain card advantage. Use your removal wisely — save interaction for the most threatening board states, not the first thing played.",
  lateGame: "Identify the most dangerous opponent and apply focused pressure. Win through combat or your key card combinations.",
  keyActions: [
    "Always be spending mana — a full hand with untapped lands means you're playing too slowly",
    "Identify the archenemy at the table and encourage group pressure on them",
    "Keep 2-3 mana open for interaction whenever possible",
  ],
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function extractArchetypes(warnings: string[]): string[] {
  for (const w of warnings) {
    const m = w.match(/Detected archetypes: (.+)\./);
    if (m) return m[1].split(", ").map((s) => s.trim());
  }
  return [];
}

function cardImage(card: ScryfallCard): string {
  return card.image_uris?.normal ?? card.card_faces?.[0]?.image_uris?.normal ?? "";
}

function ColorPip({ color }: { color: string }) {
  return <ManaSymbol symbol={color} className="w-4 h-4" />;
}

// ── CardPanel ────────────────────────────────────────────────────────────────

function CardPanel({ name }: { name: string | null }) {
  const [card, setCard]               = useState<ScryfallCard | null>(null);
  const [loading, setLoading]         = useState(false);
  const [printings, setPrintings]     = useState<Printing[]>([]);
  const [printIdx, setPrintIdx]       = useState(0);
  const [showPrints, setShowPrints]   = useState(false);
  const [loadingPrints, setLoadingPrints] = useState(false);
  const [livePrice, setLivePrice]         = useState<number | null>(null);
  const [livePriceFoil, setLivePriceFoil] = useState<number | null>(null);
  const cacheRef = useRef<Map<string, ScryfallCard>>(new Map());

  useEffect(() => {
    if (!name) { setCard(null); return; }
    setLivePrice(null);
    setLivePriceFoil(null);
    const cached = cacheRef.current.get(name);
    if (cached) { setCard(cached); return; }
    setCard(null);
    setLoading(true);
    setPrintings([]);
    setPrintIdx(0);
    setShowPrints(false);
    fetch(`https://api.scryfall.com/cards/named?exact=${encodeURIComponent(name)}&format=json`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data: ScryfallCard | null) => {
        if (data) {
          cacheRef.current.set(name, data);
          setCard(data);
          if (!data.prices?.usd) {
            if (data.prices?.usd_foil) {
              setLivePrice(parseFloat(data.prices.usd_foil));
              setLivePriceFoil(parseFloat(data.prices.usd_foil));
            } else {
              const q = encodeURIComponent(`!"${name}"`);
              fetch(`https://api.scryfall.com/cards/search?q=${q}&unique=prints&order=released&dir=desc`)
                .then(r => r.ok ? r.json() : Promise.reject())
                .then(d => {
                  type PricedCard = { prices?: { usd?: string | null; usd_foil?: string | null } };
                  const all = (d?.data ?? []) as PricedCard[];
                  const withUsd  = all.filter(c => c.prices?.usd).sort((a,b) => parseFloat(a.prices!.usd!) - parseFloat(b.prices!.usd!));
                  const withFoil = all.filter(c => c.prices?.usd_foil).sort((a,b) => parseFloat(a.prices!.usd_foil!) - parseFloat(b.prices!.usd_foil!));
                  if (withUsd.length)       setLivePrice(parseFloat(withUsd[0].prices!.usd!));
                  else if (withFoil.length) setLivePrice(parseFloat(withFoil[0].prices!.usd_foil!));
                  if (withFoil.length)      setLivePriceFoil(parseFloat(withFoil[0].prices!.usd_foil!));
                })
                .catch(() => {});
            }
          }
        }
      })
      .catch(() => setCard(null))
      .finally(() => setLoading(false));
  }, [name]);

  useEffect(() => { setPrintings([]); setPrintIdx(0); setShowPrints(false); }, [name]);

  const fetchPrintings = useCallback(async () => {
    if (!name) return;
    if (printings.length > 0) { setShowPrints(true); return; }
    setLoadingPrints(true);
    try {
      const q = encodeURIComponent(`!"${name}"`);
      const res = await fetch(`https://api.scryfall.com/cards/search?q=${q}&unique=prints&order=released&dir=desc`);
      const data = await res.json();
      type RawPrinting = ScryfallCard & { set_name?: string; released_at?: string };
      const imgs: Printing[] = (data.data ?? [])
        .map((c: RawPrinting) => ({
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
  }, [name, printings.length]);

  if (!name) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-16 px-6 text-center text-gray-500 gap-3">
        <span className="text-5xl opacity-40">🃏</span>
        <p className="text-sm">Click a card to see details</p>
      </div>
    );
  }
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-16 text-gray-500 gap-3">
        <svg className="animate-spin w-6 h-6" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        <p className="text-sm">Loading…</p>
      </div>
    );
  }
  if (!card) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-16 px-6 text-center text-gray-500 gap-3">
        <span className="text-4xl opacity-40">⚠️</span>
        <p className="text-sm">{name}</p>
        <p className="text-xs">Card data unavailable</p>
      </div>
    );
  }

  const activeImage = showPrints && printings.length > 0 ? printings[printIdx].image : cardImage(card);
  const activePrinting = showPrints && printings.length > 0 ? printings[printIdx] : null;
  const usd      = activePrinting ? activePrinting.usd      : (card.prices?.usd      ? parseFloat(card.prices.usd)      : livePrice);
  const usd_foil = activePrinting ? activePrinting.usd_foil : (card.prices?.usd_foil ? parseFloat(card.prices.usd_foil) : livePriceFoil);

  return (
    <>
      <div className="relative">
        {activeImage ? (
          <img src={activeImage} alt={card.name} className="w-full rounded-t-2xl" />
        ) : (
          <div className="w-full aspect-[5/7] bg-gray-700 flex items-center justify-center rounded-t-2xl">
            <span className="text-gray-500 text-5xl">🃏</span>
          </div>
        )}
        {showPrints && printings.length > 1 && (
          <div className="absolute bottom-2 left-0 right-0 flex items-center justify-between px-2">
            <button onClick={() => setPrintIdx((i) => Math.max(i - 1, 0))} disabled={printIdx === 0}
              className="bg-black/60 hover:bg-black/80 text-white rounded-full w-7 h-7 flex items-center justify-center disabled:opacity-30 transition text-lg">‹</button>
            <span className="bg-black/60 text-white text-xs px-2 py-0.5 rounded-full">{printIdx + 1} / {printings.length}</span>
            <button onClick={() => setPrintIdx((i) => Math.min(i + 1, printings.length - 1))} disabled={printIdx === printings.length - 1}
              className="bg-black/60 hover:bg-black/80 text-white rounded-full w-7 h-7 flex items-center justify-center disabled:opacity-30 transition text-lg">›</button>
          </div>
        )}
      </div>
      <div className="p-4 space-y-2 flex-1">
        <div className="flex items-start justify-between gap-2">
          <div className="font-semibold text-white text-sm leading-tight">{card.name}</div>
          {card.mana_cost && <ManaCost cost={card.mana_cost} />}
        </div>
        <div className="text-xs text-indigo-300">{card.type_line}</div>
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <span>CMC <span className="text-white font-medium">{card.cmc}</span></span>
          {card.color_identity.length > 0 && (
            <div className="flex gap-0.5">{card.color_identity.map((c) => <ColorPip key={c} color={c} />)}</div>
          )}
        </div>
        {card.oracle_text && (
          <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-line border-t border-gray-700 pt-2">{card.oracle_text}</p>
        )}
        <div className="flex flex-wrap items-center gap-2">
          {usd !== null && usd > 0 && <span className="text-sm font-medium text-green-400">${usd.toFixed(2)}</span>}
          {usd_foil !== null && usd_foil > 0 && <span className="text-sm font-medium text-yellow-400">✨ ${usd_foil.toFixed(2)}</span>}
          {card.purchase_uris?.tcgplayer && (
            <a href={card.purchase_uris.tcgplayer} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs bg-orange-600/20 hover:bg-orange-600/40 border border-orange-600/50 text-orange-300 hover:text-orange-200 rounded-lg px-2 py-1 transition font-medium">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
              TCGPlayer
            </a>
          )}
        </div>
        {showPrints && printings[printIdx] && (
          <div className="text-xs text-gray-500 italic">{printings[printIdx].set} ({printings[printIdx].year})</div>
        )}
        <button onClick={fetchPrintings} disabled={loadingPrints}
          className="w-full text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white rounded-lg py-1.5 transition disabled:opacity-50">
          {loadingPrints ? "Loading arts…" : showPrints ? `Showing all ${printings.length} arts` : "See other arts"}
        </button>
      </div>
    </>
  );
}

// ── HandSimulator ─────────────────────────────────────────────────────────────

function HandSimulator({ sections }: { sections: Record<string, string[]> }) {
  const [hand, setHand]           = useState<string[]>([]);
  const [images, setImages]       = useState<Record<string, string>>({});
  const [loading, setLoading]     = useState(false);
  const [selectedCard, setSelectedCard] = useState<string | null>(null);

  const allCards = Object.entries(sections)
    .filter(([s]) => s !== "Commander")
    .flatMap(([, cards]) => cards);

  async function drawHand() {
    const shuffled = [...allCards];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    const newHand = shuffled.slice(0, 7);
    setHand(newHand);
    setImages({});
    setLoading(true);
    setSelectedCard(null);
    try {
      const res = await fetch("https://api.scryfall.com/cards/collection", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifiers: newHand.map((name) => ({ name })) }),
      });
      if (!res.ok) return;
      const data = await res.json();
      const imgs: Record<string, string> = {};
      for (const card of (data.data ?? []) as ScryfallCard[]) {
        const img = card.image_uris?.normal ?? card.card_faces?.[0]?.image_uris?.normal ?? "";
        if (img) imgs[card.name] = img;
      }
      setImages(imgs);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button
          onClick={drawHand}
          disabled={loading}
          className="inline-flex items-center gap-2 bg-violet-700/60 hover:bg-violet-600/70 border border-violet-600/50
                     text-violet-200 hover:text-white font-medium px-4 py-2 rounded-xl transition text-sm disabled:opacity-50"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {hand.length === 0 ? "Simulate Opening Hand" : "Draw New Hand"}
        </button>
        {hand.length > 0 && (
          <span className="text-xs text-gray-500">Click any card for details</span>
        )}
      </div>

      {hand.length > 0 && (
        <div className="space-y-3">
          {/* 7 card images */}
          <div className="flex gap-2 overflow-x-auto pb-2">
            {hand.map((name) => (
              <button
                key={name}
                onClick={() => setSelectedCard(selectedCard === name ? null : name)}
                title={name}
                className={`shrink-0 transition-all duration-200 rounded-lg overflow-hidden
                  ${selectedCard === name ? "ring-2 ring-violet-400 scale-105" : "hover:scale-105 opacity-90 hover:opacity-100"}`}
                style={{ width: 100 }}
              >
                {images[name] ? (
                  <img src={images[name]} alt={name} className="w-full rounded-lg" />
                ) : loading ? (
                  <div className="w-full bg-gray-700 rounded-lg flex items-center justify-center"
                    style={{ aspectRatio: "5/7" }}>
                    <svg className="animate-spin w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                  </div>
                ) : (
                  <div className="w-full bg-gray-700 rounded-lg flex items-center justify-center p-1 text-center"
                    style={{ aspectRatio: "5/7" }}>
                    <span className="text-gray-400 text-xs leading-tight">{name}</span>
                  </div>
                )}
              </button>
            ))}
          </div>

          {/* Selected card full detail panel */}
          {selectedCard && (
            <div className="bg-gray-800/60 border border-violet-700/40 rounded-2xl overflow-hidden max-w-xs">
              <div className="text-xs text-violet-300 px-4 pt-3 pb-1 font-medium uppercase tracking-widest">Card Details</div>
              <CardPanel key={selectedCard} name={selectedCard} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── StrategyGuide ─────────────────────────────────────────────────────────────

function StrategyGuide({
  archetypes,
  warnings,
  strategy,
  commanderName,
}: {
  archetypes: string[];
  warnings: string[];
  strategy?: StrategyData;
  commanderName: string;
}) {
  const [open, setOpen] = useState(false);

  // Use API-provided strategy when available; fall back to generic archetype templates
  const apiStrategy = strategy;
  const genericGuide = archetypes.length > 0 && ARCHETYPE_GUIDES[archetypes[0]]
    ? ARCHETYPE_GUIDES[archetypes[0]]
    : DEFAULT_GUIDE;

  const rampNote = warnings.find(w => w.includes("ramp cards"));
  const drawNote = warnings.find(w => w.includes("card draw"));
  const landNote = warnings.find(w => w.includes("lands —"));

  const guideIcon = genericGuide.icon;
  const gameplan  = apiStrategy?.gameplan   ?? genericGuide.gameplan;
  const earlyGame = apiStrategy?.early_game ?? genericGuide.earlyGame;
  const midGame   = apiStrategy?.mid_game   ?? genericGuide.midGame;
  const lateGame  = apiStrategy?.late_game  ?? genericGuide.lateGame;
  const keyActions = apiStrategy?.key_actions ?? genericGuide.keyActions;
  const keyCards   = apiStrategy?.key_cards   ?? [];

  return (
    <div className="bg-gray-800/40 border border-gray-700/60 rounded-2xl overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-700/30 transition"
      >
        <div className="flex items-center gap-3">
          <span className="text-lg">{guideIcon}</span>
          <div className="text-left">
            <div className="font-semibold text-white text-sm">How to Play This Deck</div>
            {archetypes.length > 0 && (
              <div className="text-xs text-indigo-300 mt-0.5">
                Strategy: {archetypes.map(a => a.charAt(0).toUpperCase() + a.slice(1)).join(" · ")}
              </div>
            )}
          </div>
        </div>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="px-5 pb-6 space-y-5 border-t border-gray-700/60 pt-5">
          {/* Game plan */}
          <div>
            <div className="text-xs text-gray-400 uppercase tracking-widest font-medium mb-2">Game Plan</div>
            <p className="text-sm text-gray-200 leading-relaxed">{gameplan}</p>
          </div>

          {/* Three-phase game plan */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              { label: "Early Game (Turns 1–3)", text: earlyGame, color: "border-green-700/50 bg-green-900/20" },
              { label: "Mid Game (Turns 4–6)", text: midGame, color: "border-yellow-700/50 bg-yellow-900/20" },
              { label: "Late Game (Turn 7+)", text: lateGame, color: "border-red-700/50 bg-red-900/20" },
            ].map(({ label, text, color }) => (
              <div key={label} className={`rounded-xl border p-3 ${color}`}>
                <div className="text-xs font-semibold text-gray-300 mb-1.5">{label}</div>
                <p className="text-xs text-gray-300 leading-relaxed">{text}</p>
              </div>
            ))}
          </div>

          {/* Key actions */}
          {keyActions.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 uppercase tracking-widest font-medium mb-2">Key Things to Do in a Match</div>
              <ul className="space-y-2">
                {keyActions.map((action, i) => (
                  <li key={i} className="flex gap-2.5 text-sm text-gray-300">
                    <span className="text-indigo-400 font-bold shrink-0 mt-0.5">{i + 1}.</span>
                    <span className="leading-relaxed">{action}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Key cards derived from the actual deck */}
          {keyCards.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 uppercase tracking-widest font-medium mb-2">
                Priority Cards to Find
              </div>
              <div className="flex flex-wrap gap-2">
                {keyCards.map((card) => (
                  <span key={card}
                    className="text-xs bg-indigo-900/40 border border-indigo-700/50 text-indigo-200 rounded-lg px-2.5 py-1">
                    {card}
                  </span>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-2">
                These cards directly interact with {commanderName}&apos;s ability — find them in your opening hand or first few draws.
              </p>
            </div>
          )}

          {/* Ramp / draw callouts when available from API */}
          {apiStrategy && (apiStrategy.ramp.length > 0 || apiStrategy.draw.length > 0) && (
            <div className="grid grid-cols-2 gap-3">
              {apiStrategy.ramp.length > 0 && (
                <div className="rounded-xl border border-emerald-700/40 bg-emerald-900/10 p-3">
                  <div className="text-xs font-semibold text-emerald-300 mb-1.5">Ramp</div>
                  <ul className="space-y-0.5">
                    {apiStrategy.ramp.slice(0, 4).map(c => (
                      <li key={c} className="text-xs text-gray-300">{c}</li>
                    ))}
                  </ul>
                </div>
              )}
              {apiStrategy.draw.length > 0 && (
                <div className="rounded-xl border border-blue-700/40 bg-blue-900/10 p-3">
                  <div className="text-xs font-semibold text-blue-300 mb-1.5">Card Draw</div>
                  <ul className="space-y-0.5">
                    {apiStrategy.draw.slice(0, 4).map(c => (
                      <li key={c} className="text-xs text-gray-300">{c}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Opening hand guide */}
          <div>
            <div className="text-xs text-gray-400 uppercase tracking-widest font-medium mb-2">Opening Hand — Keep or Mulligan?</div>
            <div className="text-sm text-gray-300 leading-relaxed space-y-1">
              <p><span className="text-green-400 font-medium">Keep</span> if you have 3–4 lands, at least 1 ramp piece, and at least 1 card from your strategy.</p>
              <p><span className="text-yellow-400 font-medium">Consider mulligan</span> if you have 2 or fewer lands, no ramp, or no synergy cards for your game plan.</p>
              <p><span className="text-red-400 font-medium">Mulligan</span> if you have 6–7 lands with no action, or 0–1 lands regardless of the rest of the hand.</p>
            </div>
          </div>

          {/* Quality notes from warnings */}
          {(rampNote || drawNote || landNote) && (
            <div className="border-t border-gray-700/40 pt-4 space-y-1.5">
              {[rampNote, drawNote, landNote].filter(Boolean).map((note, i) => (
                <div key={i} className="flex gap-2 text-xs text-gray-400">
                  <span className="text-amber-400 shrink-0">⚠</span>
                  <span>{note}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── DeckView ──────────────────────────────────────────────────────────────────

export default function DeckView({
  commander,
  deckData: externalDeckData,
}: {
  commander: Commander;
  deckData?: DeckData;
}) {
  const [deck, setDeck]               = useState<DeckData | null>(externalDeckData ?? null);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState<string | null>(null);
  const [selectedCard, setSelectedCard] = useState<string | null>(null);
  const [livePrices, setLivePrices]   = useState<Record<string, number>>({});
  const [showHand, setShowHand]       = useState(false);

  // Load deck from API when no external data provided
  useEffect(() => {
    if (externalDeckData) { setDeck(externalDeckData); return; }
    setDeck(null); setError(null); setLoading(true); setSelectedCard(null);
    fetch(`/api/commanders/deck?name=${encodeURIComponent(commander.name)}`)
      .then((r) => { if (!r.ok) throw new Error(`No deck found for ${commander.name}`); return r.json() as Promise<DeckData>; })
      .then(setDeck)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [commander.name, externalDeckData]);

  // Batch-fetch live prices from Scryfall when deck loads
  useEffect(() => {
    if (!deck) return;
    const allNames = Object.entries(deck.sections)
      .filter(([s]) => s !== "Commander")
      .flatMap(([, cards]) => cards);
    if (allNames.length === 0) return;

    const chunks: string[][] = [];
    for (let i = 0; i < allNames.length; i += 75) chunks.push(allNames.slice(i, i + 75));

    (async () => {
      const prices: Record<string, number> = {};
      for (let i = 0; i < chunks.length; i++) {
        if (i > 0) await new Promise((r) => setTimeout(r, 120));
        try {
          const res = await fetch("https://api.scryfall.com/cards/collection", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ identifiers: chunks[i].map((name) => ({ name })) }),
          });
          if (!res.ok) continue;
          const data = await res.json();
          for (const card of (data.data ?? []) as ScryfallCard[]) {
            const usd = parseFloat(card.prices?.usd ?? "0") || parseFloat(card.prices?.usd_foil ?? "0");
            if (usd > 0) prices[card.name] = usd;
          }
        } catch { /* ignore */ }
      }
      setLivePrices(prices);
    })();
  }, [deck]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-gray-400">
        <svg className="animate-spin w-6 h-6 mr-3" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        Loading deck…
      </div>
    );
  }
  if (error) {
    return <div className="bg-red-900/30 border border-red-700 rounded-xl px-6 py-5 text-red-300">{error}</div>;
  }
  if (!deck) return null;

  const archetypes = extractArchetypes(deck.warnings ?? []);
  const commanderCards = deck.sections["Commander"] ?? [];
  const landCards = deck.sections["Lands"] ?? [];
  const midSections = SECTION_ORDER.filter(
    (s) => s !== "Commander" && s !== "Lands" && (deck.sections[s]?.length ?? 0) > 0
  );

  // Use live Scryfall prices when available, fall back to DB prices
  function cardPrice(name: string): number {
    return livePrices[name] ?? deck!.prices[name] ?? 0;
  }

  const liveTotalPrice = Object.entries(deck.sections)
    .flatMap(([, cards]) => cards)
    .reduce((sum, name) => sum + cardPrice(name), 0);

  function SectionCard({ section }: { section: string }) {
    const cards = deck!.sections[section];
    const sectionTotal = cards.reduce((sum, c) => sum + cardPrice(c), 0);
    const desc = SECTION_DESCRIPTIONS[section];
    return (
      <div className="bg-gray-800/40 border border-gray-700/60 rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 bg-gray-700/40 border-b border-gray-700/60">
          <div className="flex items-center gap-2">
            <span>{SECTION_ICONS[section] ?? "🃏"}</span>
            <span className="font-semibold text-white">{section}</span>
            {desc && (
              <span className="text-xs text-gray-500" title={desc}>(?)</span>
            )}
            <span className="text-xs text-gray-400 bg-gray-600/60 rounded-full px-2 py-0.5">{cards.length}</span>
          </div>
          {sectionTotal > 0 && (
            <span className="text-xs text-gray-400">${sectionTotal.toFixed(2)}</span>
          )}
        </div>
        <ul className="divide-y divide-gray-700/30">
          {cards.map((card) => {
            const price = cardPrice(card);
            const isSelected = selectedCard === card;
            return (
              <li key={card} onClick={() => setSelectedCard(card)}
                className={`flex items-center justify-between px-4 py-2 transition cursor-pointer
                  ${isSelected ? "bg-indigo-600/30" : "hover:bg-gray-700/30"}`}>
                <span className={`text-sm truncate ${isSelected ? "text-indigo-300 font-medium" : "text-gray-200"}`}>{card}</span>
                {price > 0 ? (
                  <span className="text-xs text-gray-400 ml-2 shrink-0">${price.toFixed(2)}</span>
                ) : (
                  <span className="text-xs text-gray-600 ml-2 shrink-0">—</span>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="bg-gray-800/60 border border-gray-700 rounded-2xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-white">{commander.name}</h2>
            <p className="text-gray-400 text-sm mt-1">{commander.type_line}</p>
          </div>
          <div className="flex gap-3 text-sm">
            <div className="bg-gray-700/60 rounded-lg px-4 py-2 text-center">
              <div className="text-gray-400 text-xs uppercase tracking-wide">Cards</div>
              <div className="text-white font-bold text-lg">{deck.card_count}</div>
            </div>
            <div className="bg-gray-700/60 rounded-lg px-4 py-2 text-center">
              <div className="text-gray-400 text-xs uppercase tracking-wide">Est. Price</div>
              <div className="text-green-400 font-bold text-lg">
                ${(liveTotalPrice > 0 ? liveTotalPrice : deck.total_price).toFixed(2)}
              </div>
            </div>
          </div>
        </div>

        {/* Hand Simulator toggle */}
        <div className="border-t border-gray-700/50 pt-4">
          <button
            onClick={() => setShowHand((v) => !v)}
            className="inline-flex items-center gap-2 text-sm text-violet-300 hover:text-violet-200
                       bg-violet-900/20 hover:bg-violet-900/40 border border-violet-700/40 rounded-xl px-4 py-2 transition"
          >
            <span>🎴</span>
            {showHand ? "Hide Hand Simulator" : "Simulate Opening Hand"}
          </button>
          {showHand && (
            <div className="mt-4">
              <HandSimulator sections={deck.sections} />
            </div>
          )}
        </div>
      </div>

      {/* Strategy guide */}
      <StrategyGuide
        archetypes={archetypes}
        warnings={deck.warnings ?? []}
        strategy={deck.strategy}
        commanderName={commander.name}
      />

      {/* Two-column body */}
      <div className="flex gap-6 items-start">
        <div className="flex-1 min-w-0 space-y-4">
          {/* Commander row */}
          {commanderCards.length > 0 && (
            <div className="bg-indigo-900/30 border border-indigo-700/50 rounded-xl overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2.5 bg-indigo-800/40 border-b border-indigo-700/40">
                <span>👑</span>
                <span className="font-semibold text-white">Commander</span>
                <span className="text-xs text-indigo-300 bg-indigo-700/40 rounded-full px-2 py-0.5">{commanderCards.length}</span>
              </div>
              <div className="flex flex-wrap gap-3 px-4 py-3">
                {commanderCards.map((card) => {
                  const price = cardPrice(card);
                  const isSelected = selectedCard === card;
                  return (
                    <button key={card} onClick={() => setSelectedCard(card)}
                      className={`flex items-center gap-2 text-sm font-medium px-3 py-1.5 rounded-lg transition
                        ${isSelected ? "bg-indigo-600 text-white" : "bg-indigo-800/40 text-indigo-200 hover:bg-indigo-700/50 hover:text-white"}`}>
                      <span>{card}</span>
                      {price > 0 && <span className="text-xs opacity-70">${price.toFixed(2)}</span>}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Mid sections */}
          {midSections.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {midSections.map((s) => <SectionCard key={s} section={s} />)}
            </div>
          )}

          {/* Lands full-width */}
          {landCards.length > 0 && <SectionCard section="Lands" />}
        </div>

        {/* Sticky card panel */}
        <div className="w-64 xl:w-72 shrink-0 sticky top-6 self-start">
          <div className="bg-gray-800/60 border border-gray-700 rounded-2xl overflow-hidden flex flex-col min-h-64">
            <CardPanel key={selectedCard} name={selectedCard} />
          </div>
        </div>
      </div>
    </div>
  );
}
