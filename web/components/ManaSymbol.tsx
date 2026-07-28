/**
 * Renders official MTG mana symbols using Scryfall's SVG CDN.
 * Works for colors (W/U/B/R/G/C), generic numbers (0-20, X),
 * hybrid (W/U → WU.svg), phyrexian (W/P → WP.svg), snow (S),
 * tap (T), energy (E), etc.
 */

function symbolUrl(token: string): string {
  // "{W/U}" token is "W/U" — remove the slash for the filename
  return `https://svgs.scryfall.io/card-symbols/${token.replace("/", "")}.svg`;
}

interface ManaSymbolProps {
  /** The raw token inside {}, e.g. "W", "2", "W/U" */
  symbol: string;
  className?: string;
}

export function ManaSymbol({ symbol, className = "w-5 h-5" }: ManaSymbolProps) {
  return (
    <img
      src={symbolUrl(symbol)}
      alt={`{${symbol}}`}
      title={`{${symbol}}`}
      className={`inline-block ${className}`}
      draggable={false}
    />
  );
}

interface ManaCostProps {
  /** Full mana cost string from Scryfall, e.g. "{2}{W}{U}" */
  cost: string;
  /** Tailwind size class applied to each symbol. Default: "w-5 h-5" */
  size?: string;
}

export function ManaCost({ cost, size = "w-5 h-5" }: ManaCostProps) {
  const tokens = [...cost.matchAll(/\{([^}]+)\}/g)].map(m => m[1]);
  if (!tokens.length) return null;
  return (
    <span className="inline-flex gap-0.5 items-center flex-wrap">
      {tokens.map((t, i) => (
        <ManaSymbol key={i} symbol={t} className={size} />
      ))}
    </span>
  );
}

/**
 * Renders oracle text with inline mana/tap symbols replaced by SVG icons.
 * Preserves newlines as line breaks.
 */
export function OracleText({ text, symbolSize = "w-4 h-4" }: { text: string; symbolSize?: string }) {
  const paragraphs = text.split("\n").filter(p => p.trim() !== "");
  return (
    <div className="space-y-2">
      {paragraphs.map((para, pi) => (
        <p key={pi} className="leading-relaxed">
          {para.split(/(\{[^}]+\})/).map((part, i) => {
            const sym = part.match(/^\{([^}]+)\}$/);
            if (sym) {
              return (
                <ManaSymbol
                  key={i}
                  symbol={sym[1]}
                  className={`${symbolSize} inline align-middle mx-px`}
                />
              );
            }
            return <span key={i}>{part}</span>;
          })}
        </p>
      ))}
    </div>
  );
}
