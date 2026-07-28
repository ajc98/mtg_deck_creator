"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import DeckView from "./DeckView";
import { ManaSymbol } from "./ManaSymbol";

export interface Commander {
  name: string;
  colors: string[];
  color_names: string[];
  type_line: string;
  has_deck: boolean;
}

export function ColorPip({ color }: { color: string }) {
  return <ManaSymbol symbol={color} className="w-5 h-5" />;
}

export default function CommanderSearch() {
  const [query, setQuery]             = useState("");
  const [results, setResults]         = useState<Commander[]>([]);
  const [open, setOpen]               = useState(false);
  const [selected, setSelected]       = useState<Commander | null>(null);
  const [activeIndex, setActiveIndex] = useState(-1);

  const inputRef       = useRef<HTMLInputElement>(null);
  const containerRef   = useRef<HTMLDivElement>(null);
  const debounceRef    = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Tracks the name we just selected so the debounce effect doesn't reopen the dropdown
  const justSelectedRef = useRef<string>("");

  const fetchResults = useCallback(async (q: string) => {
    try {
      const res = await fetch(`/api/commanders/search?q=${encodeURIComponent(q)}`);
      const data: Commander[] = await res.json();
      setResults(data);
      setOpen(true);
      setActiveIndex(-1);
    } catch {
      setResults([]);
    }
  }, []);

  // Debounce search on query change, but skip if query matches a just-selected commander
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query === justSelectedRef.current) return;
    if (!query.trim()) {
      setOpen(false);
      return;
    }
    debounceRef.current = setTimeout(() => fetchResults(query), 250);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, fetchResults]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleSelect(commander: Commander) {
    justSelectedRef.current = commander.name;
    setSelected(commander);
    setQuery(commander.name);
    setOpen(false);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && activeIndex >= 0) {
      handleSelect(results[activeIndex]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    justSelectedRef.current = ""; // user is typing again — allow searches
    setQuery(e.target.value);
    if (selected) setSelected(null);
  }

  function handleClear() {
    justSelectedRef.current = "";
    setQuery("");
    setSelected(null);
    setOpen(false);
    inputRef.current?.focus();
  }

  function handleFocus() {
    if (query && query !== justSelectedRef.current) {
      fetchResults(query);
    } else if (!query) {
      fetchResults("");
    }
  }

  return (
    <div className="space-y-8">
      {/* Search box */}
      <div ref={containerRef} className="relative">
        <div className="relative flex items-center">
          <span className="absolute left-4 text-gray-400 pointer-events-none">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
            </svg>
          </span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={handleInputChange}
            onFocus={handleFocus}
            onKeyDown={handleKeyDown}
            placeholder="Search for a commander…"
            className="w-full bg-gray-800 border border-gray-700 rounded-xl pl-12 pr-12 py-4 text-white
                       placeholder-gray-500 text-lg focus:outline-none focus:border-indigo-500
                       focus:ring-2 focus:ring-indigo-500/30 transition"
          />
          {query && (
            <button onClick={handleClear} className="absolute right-4 text-gray-500 hover:text-gray-300 transition">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Dropdown — capped at 320px with scroll */}
        {open && results.length > 0 && (
          <div className="absolute z-50 mt-2 w-full bg-gray-800 border border-gray-700 rounded-xl
                          shadow-2xl overflow-hidden max-h-80 flex flex-col">
            <ul className="overflow-y-auto">
              {results.map((cmd, i) => (
                <li key={cmd.name}>
                  <button
                    onMouseDown={() => handleSelect(cmd)}
                    className={`w-full flex items-center gap-3 px-4 py-3 text-left transition
                      ${i === activeIndex ? "bg-indigo-600" : "hover:bg-gray-700"}`}
                  >
                    <div className="flex gap-1 shrink-0">
                      {cmd.colors.length === 0
                        ? <ColorPip color="C" />
                        : cmd.colors.map((c) => <ColorPip key={c} color={c} />)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-white truncate">{cmd.name}</div>
                      <div className="text-xs text-gray-400 truncate">{cmd.type_line}</div>
                    </div>
                    {cmd.has_deck && (
                      <span className="shrink-0 text-xs bg-indigo-600/70 text-indigo-200 rounded-full px-2 py-0.5">
                        deck ready
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {open && results.length === 0 && query.trim() !== "" && (
          <div className="absolute z-50 mt-2 w-full bg-gray-800 border border-gray-700 rounded-xl
                          shadow-2xl px-4 py-6 text-center text-gray-400">
            No commanders found for &ldquo;{query}&rdquo;
          </div>
        )}
      </div>

      {/* Deck view */}
      {selected && <DeckView commander={selected} />}
    </div>
  );
}
