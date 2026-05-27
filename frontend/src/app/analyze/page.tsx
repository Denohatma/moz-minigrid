"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";
import {
  Zap,
  MapPin,
  ArrowLeft,
  ArrowRight,
  Loader2,
  AlertTriangle,
  CheckCircle,
  Sun,
  DollarSign,
  ShieldAlert,
  Leaf,
  Network,
  Battery,
  Upload,
  FileSpreadsheet,
  X,
  Factory,
  TreePine,
  CloudRain,
  AlertOctagon,
  BarChart3,
  Shield,
  Briefcase,
  ThermometerSun,
  List,
  Search,
  Star,
  Users,
} from "lucide-react";
import Papa from "papaparse";
import MozMap from "@/components/MozMap";
import { analyzeSite, lookupCluster, downloadReport, fetchPrioritySites, streamChat } from "@/lib/api";
import type { AnalysisResult, ClusterInfo, PrioritySite, ChatMessage } from "@/lib/api";
import { MessageSquare, Send, Bot, User } from "lucide-react";

interface ParsedSite {
  name?: string;
  latitude: number;
  longitude: number;
  row: number;
}

type InputMode = "coordinates" | "upload" | "priority";

type WizardStep = "select" | "review" | "design" | "optimize" | "report";

export default function AnalyzePage() {
  const [step, setStep] = useState<WizardStep>("select");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [selectedSite, setSelectedSite] = useState<{
    lat: number;
    lng: number;
  } | null>(null);
  const [cluster, setCluster] = useState<ClusterInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [inputMode, setInputMode] = useState<InputMode>("coordinates");
  const [parsedSites, setParsedSites] = useState<ParsedSite[]>([]);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatStreaming, setChatStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);

  const handleMapClick = useCallback((lat: number, lng: number) => {
    setLatitude(lat.toFixed(6));
    setLongitude(lng.toFixed(6));
    setSelectedSite({ lat, lng });
    setInputMode("coordinates");
    setError(null);
  }, []);

  const handleFileSelect = useCallback(
    (site: ParsedSite) => {
      setLatitude(site.latitude.toFixed(6));
      setLongitude(site.longitude.toFixed(6));
      setSelectedSite({ lat: site.latitude, lng: site.longitude });
      setError(null);
    },
    []
  );

  const handleCoordinateSubmit = async () => {
    const lat = parseFloat(latitude);
    const lng = parseFloat(longitude);
    if (isNaN(lat) || isNaN(lng)) {
      setError("Please enter valid coordinates");
      return;
    }
    if (lat < -27 || lat > -10 || lng < 29 || lng > 42) {
      setError("Coordinates must be within Mozambique");
      return;
    }
    setSelectedSite({ lat, lng });
    setError(null);
    setIsLoading(true);

    try {
      const c = await lookupCluster(lat, lng);
      setCluster(c);
      setStep("review");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to look up site");
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedSite) return;
    setIsAnalyzing(true);
    setError(null);

    const parsedOverrides: Record<string, number> = {};
    for (const [k, v] of Object.entries(overrides)) {
      const num = parseFloat(v);
      if (!isNaN(num)) parsedOverrides[k] = num;
    }

    try {
      const data = await analyzeSite(
        { latitude: selectedSite.lat, longitude: selectedSite.lng },
        Object.keys(parsedOverrides).length > 0 ? parsedOverrides : undefined
      );
      setResult(data);
      setStep("design");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleRecalculate = async () => {
    if (!selectedSite) return;
    setIsAnalyzing(true);
    setError(null);
    const parsedOverrides: Record<string, number> = {};
    for (const [k, v] of Object.entries(overrides)) {
      const num = parseFloat(v);
      if (!isNaN(num)) parsedOverrides[k] = num;
    }
    try {
      const data = await analyzeSite(
        { latitude: selectedSite.lat, longitude: selectedSite.lng },
        Object.keys(parsedOverrides).length > 0 ? parsedOverrides : undefined
      );
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleChatSend = async () => {
    const msg = chatInput.trim();
    if (!msg || chatStreaming) return;
    const userMsg: ChatMessage = { role: "user", content: msg };
    setChatHistory((prev) => [...prev, userMsg]);
    setChatInput("");
    setChatStreaming(true);
    setStreamingText("");
    try {
      const fullText = await streamChat(
        msg,
        chatHistory,
        result,
        cluster,
        (partial) => setStreamingText(partial),
      );
      setChatHistory((prev) => [...prev, { role: "assistant", content: fullText }]);
    } catch {
      setChatHistory((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I couldn't process that request. Please check that the API key is configured." },
      ]);
    } finally {
      setChatStreaming(false);
      setStreamingText("");
    }
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, streamingText]);

  return (
    <div className="h-screen bg-afcen-navy flex flex-col overflow-hidden">
      {/* Header */}
      <header className="border-b border-white/10 bg-afcen-navy/95 backdrop-blur sticky top-0 z-50 shrink-0">
        <div className="px-4 py-2 flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <span className="text-sm font-semibold tracking-[0.18em] uppercase text-afcen-gold">AF</span>
            <span className="font-semibold text-afcen-cream text-sm">Moz</span>
          </Link>
          <span className="text-afcen-navy-mid">|</span>
          <StepIndicator current={step} />
        </div>
      </header>

      <div className="flex-1 flex min-h-0">
        {/* Left column: Map (top) + Chat (bottom) — 37.5% */}
        <div className="w-[37.5%] flex flex-col shrink-0 border-r border-white/8">
          {/* Map */}
          <div className="h-[40%] relative shrink-0">
            <MozMap onSiteSelect={handleMapClick} selectedSite={selectedSite} />
          </div>

          {/* Chat */}
          <div className="flex-1 flex flex-col min-h-0 bg-afcen-navy-light">
            <div className="px-3 py-2 border-y border-white/8 flex items-center gap-2 shrink-0 bg-afcen-navy">
              <MessageSquare className="h-3.5 w-3.5 text-afcen-gold" />
              <span className="text-xs font-semibold uppercase tracking-[0.12em] text-afcen-cream">Assistant</span>
              <span className="text-[9px] text-afcen-cream/40 ml-auto tracking-wider uppercase">AFUR + Data</span>
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-3">
              {chatHistory.length === 0 && !chatStreaming && (
                <div className="text-center py-6 space-y-3">
                  <Bot className="h-7 w-7 text-afcen-gold/30 mx-auto" />
                  <p className="text-[11px] text-afcen-cream/40 max-w-[200px] mx-auto leading-relaxed">
                    Ask about site data, policy, design tradeoffs, or financial analysis.
                  </p>
                  <div className="space-y-1.5">
                    {[
                      "Is this site viable for a mini-grid?",
                      "What does the AFUR guide say about voltage drop?",
                      "How can I reduce the LCOE?",
                      "Explain the subsidy gap",
                    ].map((q) => (
                      <button
                        key={q}
                        onClick={() => { setChatInput(q); }}
                        className="block w-full text-left text-[11px] text-afcen-cream/50 hover:text-afcen-cream bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.04] rounded-md px-3 py-1.5 transition"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {chatHistory.map((msg, i) => (
                <div key={i} className={`flex gap-2 ${msg.role === "user" ? "justify-end" : ""}`}>
                  {msg.role === "assistant" && <Bot className="h-3.5 w-3.5 text-afcen-gold mt-1 shrink-0" />}
                  <div
                    className={`rounded-lg px-3 py-2 text-xs leading-relaxed max-w-[90%] ${
                      msg.role === "user"
                        ? "bg-afcen-gold/15 text-afcen-cream"
                        : "bg-white/[0.04] text-afcen-cream/80"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  </div>
                  {msg.role === "user" && <User className="h-3.5 w-3.5 text-afcen-cream/40 mt-1 shrink-0" />}
                </div>
              ))}

              {chatStreaming && streamingText && (
                <div className="flex gap-2">
                  <Bot className="h-3.5 w-3.5 text-afcen-gold mt-1 shrink-0" />
                  <div className="rounded-lg px-3 py-2 text-xs leading-relaxed max-w-[90%] bg-white/[0.04] text-afcen-cream/80">
                    <div className="whitespace-pre-wrap">{streamingText}</div>
                  </div>
                </div>
              )}

              {chatStreaming && !streamingText && (
                <div className="flex gap-2 items-center">
                  <Bot className="h-3.5 w-3.5 text-afcen-gold shrink-0" />
                  <div className="flex gap-1">
                    <div className="w-1.5 h-1.5 bg-afcen-gold rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <div className="w-1.5 h-1.5 bg-afcen-gold rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <div className="w-1.5 h-1.5 bg-afcen-gold rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>

            <div className="p-2 border-t border-white/8 shrink-0 bg-afcen-navy">
              <div className="flex gap-1.5">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleChatSend()}
                  placeholder="Ask anything..."
                  className="flex-1 rounded-md bg-white/[0.05] border border-white/[0.08] px-3 py-2 text-xs text-afcen-cream placeholder:text-afcen-cream/30 focus:outline-none focus:ring-1 focus:ring-afcen-gold/50"
                />
                <button
                  onClick={handleChatSend}
                  disabled={chatStreaming || !chatInput.trim()}
                  className="rounded-md bg-afcen-gold px-2.5 py-2 text-afcen-navy hover:bg-afcen-gold-light disabled:opacity-40 transition shrink-0"
                >
                  <Send className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Tool panel — 75% */}
        <div className="flex-1 bg-afcen-navy-light overflow-y-auto">
          {step === "select" && (
            <SiteSelectPanel
              latitude={latitude}
              longitude={longitude}
              onLatChange={setLatitude}
              onLngChange={setLongitude}
              onSubmit={handleCoordinateSubmit}
              error={error}
              isLoading={isLoading}
              hasSelection={!!selectedSite}
              inputMode={inputMode}
              onInputModeChange={setInputMode}
              parsedSites={parsedSites}
              onSitesParsed={setParsedSites}
              onFileSelect={handleFileSelect}
              onError={setError}
            />
          )}

          {step === "review" && selectedSite && (
            <ReviewPanel
              site={selectedSite}
              cluster={cluster}
              onBack={() => setStep("select")}
              onProceed={handleAnalyze}
              isAnalyzing={isAnalyzing}
            />
          )}

          {step === "design" && result && (
            <DesignPanel result={result} onBack={() => setStep("review")} onNext={() => setStep("optimize")} />
          )}

          {step === "optimize" && result && selectedSite && (
            <OptimizePanel
              result={result}
              site={selectedSite}
              overrides={overrides}
              onOverrideChange={(key, val) => setOverrides(prev => ({ ...prev, [key]: val }))}
              onRecalculate={handleRecalculate}
              isRecalculating={isAnalyzing}
              onBack={() => setStep("design")}
              onNext={() => setStep("report")}
            />
          )}

          {step === "report" && result && selectedSite && (
            <ReportPanel result={result} site={selectedSite} onBack={() => setStep("optimize")} />
          )}
        </div>
      </div>
    </div>
  );
}

function StepIndicator({ current }: { current: WizardStep }) {
  const steps: { key: WizardStep; label: string; icon: typeof MapPin }[] = [
    { key: "select", label: "Select Site", icon: MapPin },
    { key: "review", label: "Review Data", icon: Search },
    { key: "design", label: "System Design", icon: Battery },
    { key: "optimize", label: "Optimize Costs", icon: DollarSign },
    { key: "report", label: "PFS Report", icon: Briefcase },
  ];
  const currentIdx = steps.findIndex((s) => s.key === current);

  return (
    <div className="flex items-center flex-1 min-w-0">
      {steps.map((s, i) => {
        const Icon = s.icon;
        const done = i < currentIdx;
        const active = i === currentIdx;
        const upcoming = i > currentIdx;

        return (
          <div key={s.key} className="flex items-center flex-1 last:flex-none">
            <div className="flex items-center gap-2 shrink-0">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center transition-all ${
                  done
                    ? "bg-afcen-gold shadow-[0_0_8px_rgba(211,165,74,0.3)]"
                    : active
                      ? "bg-afcen-gold/20 border-2 border-afcen-gold shadow-[0_0_10px_rgba(211,165,74,0.15)]"
                      : "bg-afcen-navy border border-white/10"
                }`}
              >
                {done ? (
                  <CheckCircle className="w-3.5 h-3.5 text-afcen-navy" />
                ) : (
                  <Icon className={`w-3.5 h-3.5 ${active ? "text-afcen-gold" : "text-afcen-cream/30"}`} />
                )}
              </div>
              <div className="hidden lg:block">
                <p
                  className={`text-[11px] font-semibold leading-tight ${
                    done ? "text-afcen-gold" : active ? "text-afcen-cream" : "text-afcen-cream/30"
                  }`}
                >
                  {s.label}
                </p>
                <p className="text-[9px] leading-tight text-afcen-cream/25">
                  {done ? "Complete" : active ? "In progress" : `Step ${i + 1}`}
                </p>
              </div>
            </div>
            {i < steps.length - 1 && (
              <div className="flex-1 mx-2 h-0.5 rounded-full overflow-hidden min-w-[16px]">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    done ? "bg-afcen-gold" : "bg-white/5"
                  }`}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function SiteSelectPanel({
  latitude,
  longitude,
  onLatChange,
  onLngChange,
  onSubmit,
  error,
  isLoading,
  hasSelection,
  inputMode,
  onInputModeChange,
  parsedSites,
  onSitesParsed,
  onFileSelect,
  onError,
}: {
  latitude: string;
  longitude: string;
  onLatChange: (v: string) => void;
  onLngChange: (v: string) => void;
  onSubmit: () => void;
  error: string | null;
  isLoading: boolean;
  hasSelection: boolean;
  inputMode: InputMode;
  onInputModeChange: (m: InputMode) => void;
  parsedSites: ParsedSite[];
  onSitesParsed: (sites: ParsedSite[]) => void;
  onFileSelect: (site: ParsedSite) => void;
  onError: (msg: string | null) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [selectedFileIdx, setSelectedFileIdx] = useState<number | null>(null);

  const LAT_NAMES = ["latitude", "lat", "y", "lat_dd", "latitude_dd"];
  const LNG_NAMES = ["longitude", "lon", "lng", "long", "x", "lon_dd", "longitude_dd"];
  const NAME_NAMES = ["name", "site", "site_name", "village", "settlement", "location"];

  function findColumn(headers: string[], candidates: string[]): string | null {
    const lower = headers.map((h) => h.toLowerCase().trim());
    for (const c of candidates) {
      const idx = lower.indexOf(c);
      if (idx >= 0) return headers[idx];
    }
    return null;
  }

  function parseFile(file: File) {
    onError(null);
    setFileName(file.name);
    setSelectedFileIdx(null);

    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        if (!results.data || results.data.length === 0) {
          onError("File is empty or could not be parsed");
          return;
        }

        const headers = results.meta.fields || [];
        const latCol = findColumn(headers, LAT_NAMES);
        const lngCol = findColumn(headers, LNG_NAMES);

        if (!latCol || !lngCol) {
          onError(
            `Could not find latitude/longitude columns. Found: ${headers.join(", ")}. Expected columns like: latitude, longitude (or lat, lon, y, x)`
          );
          return;
        }

        const nameCol = findColumn(headers, NAME_NAMES);
        const sites: ParsedSite[] = [];

        for (let i = 0; i < results.data.length; i++) {
          const row = results.data[i] as Record<string, string>;
          const lat = parseFloat(row[latCol]);
          const lng = parseFloat(row[lngCol]);
          if (isNaN(lat) || isNaN(lng)) continue;
          if (lat < -90 || lat > 90 || lng < -180 || lng > 180) continue;

          sites.push({
            latitude: lat,
            longitude: lng,
            name: nameCol ? row[nameCol] || undefined : undefined,
            row: i + 2,
          });
        }

        if (sites.length === 0) {
          onError("No valid coordinates found in file");
          return;
        }

        onSitesParsed(sites);

        if (sites.length === 1) {
          setSelectedFileIdx(0);
          onFileSelect(sites[0]);
        }
      },
      error: () => {
        onError("Failed to parse file. Please use a CSV file with headers.");
      },
    });
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) parseFile(file);
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) parseFile(file);
  }

  function clearFile() {
    setFileName(null);
    onSitesParsed([]);
    setSelectedFileIdx(null);
    onError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-afcen-cream flex items-center gap-2">
          <MapPin className="h-5 w-5 text-afcen-gold" />
          Select Site
        </h2>
        <p className="mt-1 text-sm text-afcen-cream/50">
          Click the map, enter coordinates, upload a file, or pick a priority site.
        </p>
      </div>

      <div className="flex rounded-lg bg-white/[0.03] p-0.5">
        <button
          onClick={() => onInputModeChange("coordinates")}
          className={`flex-1 flex items-center justify-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium transition ${
            inputMode === "coordinates"
              ? "bg-afcen-gold/20 text-afcen-cream"
              : "text-afcen-cream/40 hover:text-afcen-cream/70"
          }`}
        >
          <MapPin className="h-3.5 w-3.5" />
          Coordinates
        </button>
        <button
          onClick={() => onInputModeChange("upload")}
          className={`flex-1 flex items-center justify-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium transition ${
            inputMode === "upload"
              ? "bg-afcen-gold/20 text-afcen-cream"
              : "text-afcen-cream/40 hover:text-afcen-cream/70"
          }`}
        >
          <Upload className="h-3.5 w-3.5" />
          Upload File
        </button>
        <button
          onClick={() => onInputModeChange("priority")}
          className={`flex-1 flex items-center justify-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium transition ${
            inputMode === "priority"
              ? "bg-afcen-gold/20 text-afcen-cream"
              : "text-afcen-cream/40 hover:text-afcen-cream/70"
          }`}
        >
          <Star className="h-3.5 w-3.5" />
          Priority Sites
        </button>
      </div>

      {inputMode === "coordinates" && (
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-afcen-cream/50 mb-1">
              Latitude
            </label>
            <input
              type="text"
              value={latitude}
              onChange={(e) => onLatChange(e.target.value)}
              placeholder="-15.4347"
              className="w-full rounded-md bg-white/[0.05] border border-white/[0.08] px-3 py-2 text-sm text-afcen-cream placeholder:text-afcen-cream/30 focus:outline-none focus:ring-1 focus:ring-afcen-gold/50"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-afcen-cream/50 mb-1">
              Longitude
            </label>
            <input
              type="text"
              value={longitude}
              onChange={(e) => onLngChange(e.target.value)}
              placeholder="40.6734"
              className="w-full rounded-md bg-white/[0.05] border border-white/[0.08] px-3 py-2 text-sm text-afcen-cream placeholder:text-afcen-cream/30 focus:outline-none focus:ring-1 focus:ring-afcen-gold/50"
            />
          </div>
        </div>
      )}

      {inputMode === "upload" && (
        <div className="space-y-4">
          {!fileName ? (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`cursor-pointer rounded-lg border-2 border-dashed p-6 text-center transition ${
                dragActive
                  ? "border-afcen-gold bg-afcen-gold/10"
                  : "border-white/[0.1] bg-white/[0.03] hover:border-white/[0.15]"
              }`}
            >
              <FileSpreadsheet className="h-8 w-8 mx-auto text-afcen-cream/40 mb-2" />
              <p className="text-sm text-afcen-cream/60">
                Drop a CSV file here or{" "}
                <span className="text-afcen-gold font-medium">browse</span>
              </p>
              <p className="text-xs text-afcen-cream/40 mt-1">
                CSV with latitude & longitude columns
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.txt"
                onChange={handleFileInput}
                className="hidden"
              />
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-md bg-white/[0.03] px-3 py-2">
                <div className="flex items-center gap-2 text-sm text-white min-w-0">
                  <FileSpreadsheet className="h-4 w-4 text-afcen-gold shrink-0" />
                  <span className="truncate">{fileName}</span>
                  <span className="text-xs text-afcen-cream/50 shrink-0">
                    ({parsedSites.length} site{parsedSites.length !== 1 ? "s" : ""})
                  </span>
                </div>
                <button
                  onClick={clearFile}
                  className="text-afcen-cream/40 hover:text-afcen-cream transition p-1"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {parsedSites.length > 1 && (
                <div>
                  <label className="block text-xs font-medium text-afcen-cream/50 mb-2">
                    Select a site to analyze
                  </label>
                  <div className="space-y-1 max-h-64 overflow-y-auto rounded-md">
                    {parsedSites.map((site, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setSelectedFileIdx(idx);
                          onFileSelect(site);
                        }}
                        className={`w-full flex items-center justify-between rounded-md px-3 py-2 text-left text-sm transition ${
                          selectedFileIdx === idx
                            ? "bg-afcen-gold/20 border border-afcen-gold/30 text-afcen-cream"
                            : "bg-white/[0.03] text-afcen-cream/60 hover:bg-white/[0.06]"
                        }`}
                      >
                        <span className="truncate">
                          {site.name || `Site (row ${site.row})`}
                        </span>
                        <span className="text-xs text-afcen-cream/50 shrink-0 ml-2">
                          {site.latitude.toFixed(4)}, {site.longitude.toFixed(4)}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {inputMode === "priority" && (
        <PrioritySitesPanel
          onSelectSite={(site) => {
            onLatChange(site.latitude.toFixed(6));
            onLngChange(site.longitude.toFixed(6));
            onError(null);
          }}
          onError={onError}
        />
      )}

      {error && (
        <div className="flex items-start gap-2 rounded-md bg-red-500/10 border border-red-500/20 p-3">
          <AlertTriangle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      <button
        onClick={onSubmit}
        disabled={!latitude || !longitude || isLoading}
        className="w-full flex items-center justify-center gap-2 rounded-lg bg-afcen-gold px-4 py-2.5 text-sm font-semibold text-afcen-navy hover:bg-afcen-gold-light disabled:opacity-50 disabled:cursor-not-allowed transition"
      >
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Looking up cluster...
          </>
        ) : (
          <>
            Continue
            <ArrowRight className="h-4 w-4" />
          </>
        )}
      </button>

      {hasSelection && !isLoading && (
        <div className="rounded-md bg-afcen-gold/10 border border-afcen-gold/20 p-3">
          <p className="text-sm text-afcen-gold">
            Site selected at {latitude}, {longitude}
          </p>
        </div>
      )}
    </div>
  );
}

function ReviewPanel({
  site,
  cluster,
  onBack,
  onProceed,
  isAnalyzing,
}: {
  site: { lat: number; lng: number };
  cluster: ClusterInfo | null;
  onBack: () => void;
  onProceed: () => void;
  isAnalyzing?: boolean;
}) {
  const urbanLabel = cluster
    ? cluster.is_urban === 2
      ? "Urban"
      : cluster.is_urban === 1
        ? "Peri-urban"
        : "Rural"
    : "...";

  return (
    <div className="p-6 space-y-5 overflow-y-auto">
      <div>
        <h2 className="text-lg font-semibold text-afcen-cream">Review Site Data</h2>
        <p className="mt-1 text-sm text-afcen-cream/50">
          World Bank DRE Atlas settlement data.
        </p>
      </div>

      {cluster ? (
        <div className="space-y-4">
          <div className="space-y-2">
            <SectionHeader label="Location" />
            {cluster.village_name && <DataRow label="Settlement" value={cluster.village_name} />}
            <DataRow label="Coordinates" value={`${site.lat.toFixed(4)}, ${site.lng.toFixed(4)}`} />
            {cluster.admin_region && <DataRow label="Province" value={cluster.admin_region} />}
            {cluster.admin_district && <DataRow label="District" value={cluster.admin_district} />}
            <DataRow label="Classification" value={urbanLabel} />
          </div>

          <div className="space-y-2">
            <SectionHeader label="Population & Buildings" />
            <DataRow label="Population" value={cluster.population.toLocaleString()} tip="WorldPop 2020 constrained estimate, disaggregated to settlement footprint." />
            {cluster.num_buildings != null && <DataRow label="Buildings" value={cluster.num_buildings.toLocaleString()} tip="Satellite-detected structures (Google Open Buildings). Includes non-residential structures such as storage, workshops, and community buildings — not a direct household count." />}
            {cluster.dre_num_connections != null && <DataRow label="Est. connections" value={cluster.dre_num_connections.toLocaleString()} tip="Estimated metering points from the DRE Atlas demand model. Used as the basis for Round 1 coverage sizing." />}
            <DataRow label="Area" value={`${cluster.area_km2.toFixed(3)} km²`} />
            {cluster.building_density_pct != null && <DataRow label="Building density" value={`${cluster.building_density_pct.toFixed(1)}%`} />}
          </div>

          <div className="space-y-2">
            <SectionHeader label="Energy & Demand" />
            <DataRow label="Solar PV potential" value={`${cluster.ghi_kwh_m2_year.toFixed(0)} kWh/kWp/yr`} tip="Global Horizontal Irradiance from PVGIS/SolarGIS. Converted to specific yield using a performance-ratio model with temperature, soiling, and wiring losses." />
            {cluster.dre_demand_kwh_day != null && <DataRow label="Est. demand" value={`${cluster.dre_demand_kwh_day.toFixed(1)} kWh/day`} tip="DRE Atlas bottom-up estimate: per-connection demand x connections. Validated against MTF survey benchmarks for Mozambique Tier 2–3 settlements." />}
            {cluster.dre_demand_per_conn_kwh_day != null && <DataRow label="Demand/connection" value={`${cluster.dre_demand_per_conn_kwh_day.toFixed(3)} kWh/day`} />}
            <DataRow label="Nightlight" value={cluster.has_nightlight ? `Yes (${cluster.nightlight_overlap_pct?.toFixed(0) ?? 0}% coverage)` : "No"} tip="VIIRS nighttime lights overlap. Indicates possible existing electricity access (grid, diesel genset, or solar home systems)." />
          </div>

          <div className="space-y-2">
            <SectionHeader label="Grid & Infrastructure" />
            <DataRow label="Existing MV grid" value={`${cluster.dist_grid_mv_km.toFixed(1)} km`} tip="Straight-line distance to nearest existing medium-voltage (33 kV) line from EDM network GIS data. Actual route distance may be 20–40% longer." />
            {cluster.dist_grid_planned_km != null && <DataRow label="Planned grid" value={`${cluster.dist_grid_planned_km.toFixed(1)} km`} tip="Distance to nearest planned grid extension from EDM/FUNAE master plan. Planned ≠ committed — verify implementation status with ARENE before relying on this for grid-arrival assumptions." />}
            <DataRow label="Main road" value={cluster.main_road_access ? `${cluster.dist_road_km.toFixed(1)} km (access)` : `${cluster.dist_road_km.toFixed(1)} km`} tip="Distance to nearest classified road (OSM). Road access affects logistics cost, construction timeline, and ongoing O&M." />
            {cluster.nearest_hub_name && <DataRow label="Nearest hub" value={`${cluster.nearest_hub_name} (${cluster.dist_nearest_hub_km?.toFixed(0) ?? "?"} km)`} />}
          </div>

          <div className="space-y-2">
            <SectionHeader label="Social & Economic" />
            {cluster.mean_rwi != null && <DataRow label="Wealth index (RWI)" value={cluster.mean_rwi.toFixed(2)} tip="Relative Wealth Index from Meta Data for Good. Scale is centered at 0 (national median): positive = above median, negative = below. Based on satellite imagery, mobile connectivity, and survey calibration. Used to estimate willingness-to-pay and tariff affordability." />}
            <DataRow label="Education" value={cluster.has_education_facility ? `Yes (${cluster.num_education_facilities ?? 0})` : "None nearby"} />
            <DataRow label="Healthcare" value={cluster.has_health_facility ? `Yes (${cluster.num_health_facilities ?? 0})` : "None nearby"} />
            {cluster.crop_types && <DataRow label="Crops" value={cluster.crop_types} />}
            {cluster.security_risk && (
              <DataRow
                label="Security"
                value={cluster.security_risk.charAt(0).toUpperCase() + cluster.security_risk.slice(1)}
                tip="Based on ACLED conflict data: incidents and fatalities within 25 km and 50 km radii over the past 3 years."
              />
            )}
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-sm text-afcen-cream/50 py-4">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading settlement data...
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-white/[0.06] px-4 py-2.5 text-sm font-medium text-afcen-cream/70 hover:bg-white/[0.10] transition"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <button
          onClick={onProceed}
          disabled={!cluster || isAnalyzing}
          className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-afcen-gold px-4 py-2.5 text-sm font-semibold text-afcen-navy hover:bg-afcen-gold-light disabled:opacity-50 transition"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              Design System
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}

function SectionHeader({ label }: { label: string }) {
  return <h3 className="text-xs font-semibold uppercase tracking-[0.15em] text-afcen-gold/70 pt-1">{label}</h3>;
}

/* ── DesignPanel ──────────────────────────────────────────── */

function DesignPanel({
  result,
  onBack,
  onNext,
}: {
  result: AnalysisResult;
  onBack: () => void;
  onNext: () => void;
}) {
  const s = result.sizing;
  const d = result.demand;
  const sol = result.solar_resource;
  const dist = result.distribution;
  const gr = result.grid_risk;

  const riskColor = gr.risk_level === "critical" ? "text-red-400" : gr.risk_level === "high" ? "text-orange-400" : gr.risk_level === "medium" ? "text-yellow-400" : "text-afcen-gold";

  return (
    <div className="p-6 space-y-6 text-afcen-cream overflow-y-auto">
      <div>
        <h2 className="text-lg font-semibold">System Design</h2>
        <p className="mt-1 text-sm text-afcen-cream/50">
          Mini-grid and distribution network design for {d.households} households.
        </p>
      </div>

      {/* Demand Summary */}
      <div className="grid grid-cols-2 gap-3">
        <MetricCard label="Round 1 HH" value={`${d.households} of ${d.total_settlement_households}`} />
        <MetricCard label="Coverage" value={`${(d.coverage_pct * 100).toFixed(0)}%`} />
        <MetricCard label="Demand Tier" value={`Tier ${d.demand_tier}`} />
        <MetricCard label="Peak Load" value={`${d.peak_demand_kw.toFixed(1)} kW`} />
        <MetricCard label="Residential" value={`${(d.daily_energy_kwh - d.productive_use_kwh_day).toFixed(0)} kWh/d`} />
        <MetricCard label="Productive Use" value={`${d.productive_use_kwh_day.toFixed(0)} kWh/d`} />
      </div>

      {/* Solar Resource */}
      {sol && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-afcen-cream/70 flex items-center gap-1.5">
            <Sun className="h-4 w-4 text-yellow-400" />
            Solar Resource
          </h3>
          <DataRow label="Annual GHI" value={`${sol.annual_ghi_kwh_m2.toFixed(0)} kWh/m²/yr`} />
          <DataRow label="Specific Yield" value={`${sol.specific_yield_kwh_per_kwp.toFixed(0)} kWh/kWp`} />
          <DataRow label="Performance Ratio" value={`${(sol.performance_ratio * 100).toFixed(1)}%`} />
          <DataRow label="Data Source" value={sol.data_source} />
        </div>
      )}

      {/* System Sizing */}
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-afcen-cream/70 flex items-center gap-1.5">
          <Battery className="h-4 w-4 text-blue-400" />
          Generation System
        </h3>
        <DataRow label="PV Array" value={`${s.pv_kwp.toFixed(1)} kWp`} />
        <DataRow label="Battery" value={`${s.battery_kwh_nominal.toFixed(0)} kWh (${s.battery_kwh_usable.toFixed(0)} usable)`} />
        <DataRow label="Inverter" value={`${s.inverter_kva.toFixed(1)} kVA`} />
        {s.dc_ac_ratio != null && <DataRow label="DC/AC Ratio" value={s.dc_ac_ratio.toFixed(2)} />}
      </div>

      {/* Dispatch */}
      {s.annual_generation_kwh != null && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-afcen-cream/70 flex items-center gap-1.5">
            <Zap className="h-4 w-4 text-amber-400" />
            Dispatch Simulation
          </h3>
          <DataRow label="Annual Generation" value={`${(s.annual_generation_kwh / 1000).toFixed(1)} MWh`} />
          {s.annual_energy_served_kwh != null && <DataRow label="Energy Served" value={`${(s.annual_energy_served_kwh / 1000).toFixed(1)} MWh`} />}
          {s.unmet_energy_pct != null && <DataRow label="Unmet Energy" value={`${s.unmet_energy_pct.toFixed(1)}%`} />}
          {s.curtailment_pct != null && <DataRow label="Curtailment" value={`${s.curtailment_pct.toFixed(1)}%`} />}
          {s.capacity_factor_pct != null && <DataRow label="Capacity Factor" value={`${s.capacity_factor_pct.toFixed(1)}%`} />}
          {s.battery_cycles_per_year != null && <DataRow label="Battery Cycles/yr" value={`${s.battery_cycles_per_year.toFixed(0)}`} />}
        </div>
      )}

      {/* Distribution */}
      {dist && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-afcen-cream/70 flex items-center gap-1.5">
            <Network className="h-4 w-4 text-cyan-400" />
            Distribution Network
          </h3>
          <DataRow label="Line Length" value={`${dist.total_line_length_m.toFixed(0)} m`} />
          <DataRow label="Poles" value={`${dist.pole_count}`} />
          <DataRow label="Customers" value={`${dist.customers_connected}`} />
          <DataRow label="Network Cost" value={`$${(dist.total_network_cost_usd / 1000).toFixed(1)}k`} />
          <DataRow label="Cost/Connection" value={`$${dist.cost_per_connection_usd.toFixed(0)}`} tip="Distribution network cost per metered connection (poles, wire, meters, labour). ESMAP benchmark: $250–500/connection for rural Mozambique." />
          <DataRow label="Voltage Drop" value={`${dist.voltage_drop_max_pct.toFixed(1)}%`} />
          <DataRow label="Technical Losses" value={`${dist.technical_losses_pct.toFixed(1)}%`} />
        </div>
      )}

      {/* Grid Risk */}
      <div className="space-y-2">
        <h3 className={`text-sm font-medium flex items-center gap-1.5 ${riskColor}`}>
          <ShieldAlert className="h-4 w-4" />
          Grid Risk: {gr.risk_level.charAt(0).toUpperCase() + gr.risk_level.slice(1)}
        </h3>
        <DataRow label="Nearest MV" value={`${gr.dist_mv_km.toFixed(1)} km`} />
        <DataRow label="Nearest HV" value={`${gr.dist_hv_km.toFixed(1)} km`} />
        <DataRow label="Assessment" value={gr.risk_label} />
        {gr.esmap_recommended && <DataRow label="ESMAP Strategy" value={gr.esmap_recommended} />}
      </div>

      {/* Nav */}
      <div className="flex gap-3">
        <button onClick={onBack} className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-white/[0.06] px-4 py-2.5 text-sm font-medium text-afcen-cream/70 hover:bg-white/[0.10] transition">
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        <button onClick={onNext} className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-afcen-gold px-4 py-2.5 text-sm font-semibold text-afcen-navy hover:bg-afcen-gold-light transition">
          Optimize Costs <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

/* ── OptimizePanel ───────────────────────────────────────── */

const COST_FIELDS: { key: string; label: string; defaultValue: string; group: string }[] = [
  { key: "pv_modules_usd_per_kwp", label: "PV modules ($/kWp)", defaultValue: "580", group: "Equipment" },
  { key: "battery_ems_usd_per_kwh", label: "Battery + EMS ($/kWh)", defaultValue: "285", group: "Equipment" },
  { key: "inverters_usd_per_kwac", label: "Inverters ($/kVA)", defaultValue: "420", group: "Equipment" },
  { key: "mounting_usd_per_kwp", label: "Mounting ($/kWp)", defaultValue: "180", group: "Equipment" },
  { key: "bos_usd_per_kwp", label: "BOS ($/kWp)", defaultValue: "220", group: "Equipment" },
  { key: "civil_works_fixed_usd", label: "Civil works ($)", defaultValue: "18000", group: "Equipment" },
  { key: "discount_rate", label: "Discount rate", defaultValue: "0.10", group: "Financial" },
  { key: "grant_pct", label: "Grant %", defaultValue: "0.40", group: "Financial" },
  { key: "debt_pct", label: "Debt %", defaultValue: "0.35", group: "Financial" },
  { key: "affordable_tariff", label: "Target tariff ($/kWh)", defaultValue: "0.45", group: "Financial" },
];

function OptimizePanel({
  result,
  site,
  overrides,
  onOverrideChange,
  onRecalculate,
  isRecalculating,
  onBack,
  onNext,
}: {
  result: AnalysisResult;
  site: { lat: number; lng: number };
  overrides: Record<string, string>;
  onOverrideChange: (key: string, value: string) => void;
  onRecalculate: () => void;
  isRecalculating: boolean;
  onBack: () => void;
  onNext: () => void;
}) {
  const f = result.financial;

  const groups = ["Equipment", "Financial"];

  return (
    <div className="p-6 space-y-6 text-afcen-cream overflow-y-auto">
      <div>
        <h2 className="text-lg font-semibold">Optimize Costs</h2>
        <p className="mt-1 text-sm text-afcen-cream/50">
          Adjust equipment prices and financial parameters, then recalculate.
        </p>
      </div>

      {/* Key financial metrics */}
      <div className="grid grid-cols-2 gap-3">
        <MetricCard label="Total CAPEX" value={`$${(f.total_capex_usd / 1000).toFixed(0)}k`} />
        <MetricCard label="LCOE" value={`$${f.lcoe_usd_kwh.toFixed(2)}/kWh`} />
        <MetricCard label="Project IRR" value={`${f.irr_pct.toFixed(1)}%`} />
        <MetricCard label="NPV" value={`$${(f.npv_usd / 1000).toFixed(0)}k`} />
        <MetricCard label="Payback" value={`${f.payback_years.toFixed(1)} yrs`} />
        <MetricCard label="Min DSCR" value={f.dscr.toFixed(2)} />
        {f.equity_irr_pct != null && <MetricCard label="Equity IRR" value={`${f.equity_irr_pct.toFixed(1)}%`} />}
        {f.capex_per_wp != null && <MetricCard label="CAPEX/Wp" value={`$${f.capex_per_wp.toFixed(2)}`} />}
      </div>

      {/* CAPEX breakdown bar */}
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-afcen-cream/70">CAPEX Breakdown</h3>
        <CapexBar breakdown={f.capex_breakdown} total={f.total_capex_usd} />
      </div>

      {/* Financial Structure */}
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-afcen-cream/70 flex items-center gap-1.5">
          <DollarSign className="h-4 w-4 text-afcen-gold" />
          Financial Structure
        </h3>
        <DataRow label="Cost-reflective tariff" value={`$${f.cost_reflective_tariff_usd.toFixed(3)}/kWh`} />
        <DataRow label="Affordable tariff" value={`$${f.affordable_tariff_usd.toFixed(3)}/kWh`} />
        {f.grant_amount_usd != null && <DataRow label="Grant / Subsidy" value={`$${(f.grant_amount_usd / 1000).toFixed(0)}k`} />}
        {f.debt_amount_usd != null && <DataRow label="Concessional Debt" value={`$${(f.debt_amount_usd / 1000).toFixed(0)}k`} />}
        {f.equity_amount_usd != null && <DataRow label="Developer Equity" value={`$${(f.equity_amount_usd / 1000).toFixed(0)}k`} />}
        {f.annual_opex_usd != null && <DataRow label="Annual OPEX" value={`$${(f.annual_opex_usd / 1000).toFixed(1)}k`} />}
        <DataRow label="Subsidy gap" value={`$${f.subsidy_gap_per_connection_usd.toFixed(0)}/conn (${f.subsidy_gap_pct_capex.toFixed(0)}% CAPEX)`} tip="The additional funding needed per connection beyond what tariff revenue and carbon credits can recover. Different from cost/connection (total CAPEX ÷ connections): subsidy gap accounts for revenue the project can earn over its lifetime." />
      </div>

      {/* Editable cost inputs grouped */}
      {groups.map((group) => (
        <div key={group} className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-afcen-cream/40">{group} Inputs</h3>
          {COST_FIELDS.filter((cf) => cf.group === group).map((p) => (
            <div key={p.key} className="flex items-center gap-2">
              <label className="text-xs text-afcen-cream/50 w-[55%] shrink-0">{p.label}</label>
              <input
                type="text"
                value={overrides[p.key] ?? p.defaultValue}
                onChange={(e) => onOverrideChange(p.key, e.target.value)}
                className="flex-1 rounded-md bg-white/[0.05] border border-white/[0.08] px-2 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-afcen-gold/50"
              />
            </div>
          ))}
        </div>
      ))}

      {/* Recalculate button */}
      <button
        onClick={onRecalculate}
        disabled={isRecalculating}
        className="w-full flex items-center justify-center gap-2 rounded-lg bg-amber-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-amber-400 disabled:opacity-50 transition"
      >
        {isRecalculating ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Recalculating...
          </>
        ) : (
          <>
            <Zap className="h-4 w-4" />
            Recalculate
          </>
        )}
      </button>

      {/* Nav */}
      <div className="flex gap-3">
        <button onClick={onBack} className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-white/[0.06] px-4 py-2.5 text-sm font-medium text-afcen-cream/70 hover:bg-white/[0.10] transition">
          <ArrowLeft className="h-4 w-4" /> Design
        </button>
        <button onClick={onNext} className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-afcen-gold px-4 py-2.5 text-sm font-semibold text-afcen-navy hover:bg-afcen-gold-light transition">
          Generate Report <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

/* ── ReportPanel ──────────────────────────────────────────── */

function ReportPanel({
  result,
  site,
  onBack,
}: {
  result: AnalysisResult;
  site: { lat: number; lng: number };
  onBack: () => void;
}) {
  const [downloading, setDownloading] = useState<"pdf" | "excel" | "pfs" | "pfs-summary" | "concession" | null>(null);

  const handleDownload = async (format: "pdf" | "excel" | "pfs" | "pfs-summary" | "concession") => {
    setDownloading(format);
    try {
      const blob = await downloadReport(
        { latitude: site.lat, longitude: site.lng, name: result.site.name },
        format
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download =
        format === "excel"
          ? "moz-financial-model.xlsx"
          : format === "pfs"
            ? `${result.site.name || "site"}-PFS.docx`
            : format === "pfs-summary"
              ? `${result.site.name || "site"}-Summary.docx`
              : format === "concession"
                ? `${result.site.name || "site"}-ARENE-concession.json`
                : "moz-report.html";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      console.error("Download failed:", e);
    } finally {
      setDownloading(null);
    }
  };

  const f = result.financial;
  const s = result.sizing;
  const d = result.demand;
  const carb = result.carbon;
  const pue = result.productive_use;
  const ess = result.ess;
  const climate = result.climate;
  const riskAn = result.risk_analysis;
  const conf = result.confidence;

  return (
    <div className="p-6 space-y-6 text-afcen-cream overflow-y-auto">
      <div>
        <h2 className="text-lg font-semibold">Pre-Feasibility Report</h2>
        <p className="mt-1 text-sm text-afcen-cream/50">
          {result.site.name || "Site"} — {d.households} HH, {s.pv_kwp.toFixed(0)} kWp PV, ${(f.total_capex_usd / 1000).toFixed(0)}k CAPEX
        </p>
      </div>

      {/* Screening warnings */}
      {result.screening.warnings.length > 0 && (
        <div className="space-y-2">
          {result.screening.warnings.map((w, i) => (
            <div
              key={i}
              className={`flex items-start gap-2 rounded-md p-3 text-sm ${
                w.severity === "error"
                  ? "bg-red-500/10 border border-red-500/20 text-red-300"
                  : w.severity === "warning"
                    ? "bg-yellow-500/10 border border-yellow-500/20 text-yellow-300"
                    : "bg-blue-500/10 border border-blue-500/20 text-blue-300"
              }`}
            >
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
              {w.message}
            </div>
          ))}
        </div>
      )}

      {/* Key metrics summary */}
      <div className="grid grid-cols-3 gap-2">
        <MetricCard label="LCOE" value={`$${f.lcoe_usd_kwh.toFixed(2)}`} />
        <MetricCard label="IRR" value={`${f.irr_pct.toFixed(1)}%`} />
        <MetricCard label="CAPEX" value={`$${(f.total_capex_usd / 1000).toFixed(0)}k`} />
      </div>

      {/* Carbon Credits */}
      {carb && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-afcen-cream/70 flex items-center gap-1.5">
            <Leaf className="h-4 w-4 text-green-400" />
            Carbon Credits
          </h3>
          <DataRow label="Emission Reductions" value={`${carb.annual_emission_reductions_tco2e.toFixed(1)} tCO2e/yr`} />
          <DataRow label="Diesel Displaced" value={`${(carb.diesel_displaced_litres_yr / 1000).toFixed(1)}k litres/yr`} />
          <DataRow label="Methodology" value={carb.recommended_methodology} />
          {carb.revenue_by_scenario.market != null && (
            <DataRow label="Market Revenue" value={`$${carb.revenue_by_scenario.market.toFixed(0)}/yr`} />
          )}
        </div>
      )}

      {/* Productive Use */}
      {pue && pue.sectors.filter((sec) => sec.relevance === "high" || sec.relevance === "medium").length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-afcen-cream/70 flex items-center gap-1.5">
            <Factory className="h-4 w-4 text-amber-400" />
            Productive Use
          </h3>
          <div className="rounded-md bg-white/[0.03] p-3 space-y-2">
            <p className="text-xs text-afcen-cream/50">
              {pue.sectors.filter((sec) => sec.relevance === "high").length} high-relevance,{" "}
              {pue.sectors.filter((sec) => sec.relevance === "medium").length} medium-relevance sectors
            </p>
            {pue.sectors
              .filter((sec) => sec.relevance === "high" || sec.relevance === "medium")
              .slice(0, 5)
              .map((sec) => (
                <div key={sec.sector} className="flex items-center justify-between text-xs">
                  <span className="text-afcen-cream/60">{sec.sector}</span>
                  <span className={sec.relevance === "high" ? "text-afcen-gold font-medium" : "text-yellow-400"}>
                    {sec.relevance} — {sec.estimated_demand_kwh_day.toFixed(0)} kWh/day
                  </span>
                </div>
              ))}
          </div>
          <DataRow label="Productive Demand" value={`${pue.total_productive_demand_kwh_day.toFixed(1)} kWh/day (${pue.productive_demand_pct.toFixed(0)}%)`} />
          {pue.anchors.length > 0 && (
            <DataRow label="Anchor Loads" value={`${pue.anchors.length} identified (${pue.anchors.map((a) => a.type).slice(0, 3).join(", ")})`} />
          )}
          {pue.jobs.total != null && <DataRow label="Estimated Jobs" value={`${pue.jobs.direct || 0} direct + ${pue.jobs.indirect || 0} indirect`} />}
          {pue.complementary_investment_usd.total != null && (
            <DataRow label="Complementary Investment" value={`$${(pue.complementary_investment_usd.total / 1000).toFixed(0)}k`} />
          )}
        </div>
      )}

      {/* Climate */}
      {climate && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-afcen-cream/70 flex items-center gap-1.5">
            <ThermometerSun className="h-4 w-4 text-orange-400" />
            Climate Rationale
          </h3>
          <DataRow label="Lifetime Avoided" value={`${climate.lifetime_avoided_tco2e.toFixed(0)} tCO2e`} />
          <DataRow label="Overall Hazard" value={climate.overall_hazard_level.replace("_", " ")} />
          {climate.climate_finance_score && (
            <DataRow label="Climate Finance" value={`${climate.climate_finance_score} potential ($${(climate.total_climate_finance_potential_usd / 1000).toFixed(0)}k)`} />
          )}
        </div>
      )}

      {/* ESS */}
      {ess && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-afcen-cream/70 flex items-center gap-1.5">
            <TreePine className="h-4 w-4 text-green-400" />
            Environmental & Social
          </h3>
          <DataRow label="ESIA Category" value={`Category ${ess.esia_category}`} />
          <DataRow label="Biodiversity" value={ess.biodiversity_sensitivity} />
          <DataRow label="Resettlement Risk" value={ess.resettlement_risk} />
          <DataRow label="Overall ESS Risk" value={ess.overall_ess_risk} />
        </div>
      )}

      {/* Risk */}
      {riskAn && (
        <div className="space-y-2">
          <h3 className={`text-sm font-medium flex items-center gap-1.5 ${
            riskAn.overall_risk_level === "critical" ? "text-red-400" :
            riskAn.overall_risk_level === "high" ? "text-orange-400" :
            riskAn.overall_risk_level === "medium" ? "text-yellow-400" : "text-afcen-gold"
          }`}>
            <AlertOctagon className="h-4 w-4" />
            Risk: {riskAn.overall_risk_level.charAt(0).toUpperCase() + riskAn.overall_risk_level.slice(1)}
          </h3>
          <DataRow label="Risk Score" value={`${riskAn.overall_risk_score.toFixed(1)} / 25`} />
          {riskAn.top_risks.slice(0, 3).map((risk, i) => (
            <div key={i} className="rounded-md bg-white/[0.03] px-3 py-2">
              <span className="text-xs text-afcen-cream/60">{i + 1}. {risk}</span>
            </div>
          ))}
        </div>
      )}

      {/* Confidence */}
      {conf && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-afcen-cream/70 flex items-center gap-1.5">
            <BarChart3 className="h-4 w-4 text-indigo-400" />
            Data Confidence
          </h3>
          <div className="rounded-md bg-white/[0.03] p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-afcen-cream/50">Overall Confidence</span>
              <span className={`text-sm font-bold ${
                conf.overall_confidence_level === "high" ? "text-afcen-gold" :
                conf.overall_confidence_level === "medium" ? "text-yellow-400" : "text-red-400"
              }`}>
                {conf.overall_confidence_score}%
              </span>
            </div>
            <div className="w-full bg-white/[0.1] rounded-full h-2">
              <div
                className={`h-2 rounded-full ${
                  conf.overall_confidence_score >= 75 ? "bg-afcen-gold" :
                  conf.overall_confidence_score >= 50 ? "bg-yellow-400" : "bg-red-400"
                }`}
                style={{ width: `${conf.overall_confidence_score}%` }}
              />
            </div>
          </div>
          <DataRow label="Data Completeness" value={`${conf.data_completeness_pct.toFixed(0)}%`} />
        </div>
      )}

      {/* Download buttons */}
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-afcen-cream/70 flex items-center gap-1.5">
          <Briefcase className="h-4 w-4 text-afcen-cream/60" />
          Generate Reports
        </h3>
        <div className="flex gap-3">
          <button onClick={() => handleDownload("pdf")} disabled={downloading === "pdf"} className="flex-1 rounded-lg bg-afcen-gold px-4 py-2.5 text-sm font-semibold text-afcen-navy hover:bg-afcen-gold-light disabled:opacity-50 transition">
            {downloading === "pdf" ? "Generating..." : "HTML Report"}
          </button>
          <button onClick={() => handleDownload("pfs")} disabled={downloading === "pfs"} className="flex-1 rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-400 disabled:opacity-50 transition">
            {downloading === "pfs" ? "Generating..." : "Full PFS (.docx)"}
          </button>
          <button onClick={() => handleDownload("pfs-summary")} disabled={downloading === "pfs-summary"} className="flex-1 rounded-lg bg-violet-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-400 disabled:opacity-50 transition">
            {downloading === "pfs-summary" ? "Generating..." : "5-Page Summary"}
          </button>
        </div>
        <div className="flex gap-3">
          <button onClick={() => handleDownload("excel")} disabled={downloading === "excel"} className="flex-1 rounded-lg bg-blue-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-400 disabled:opacity-50 transition">
            {downloading === "excel" ? "Generating..." : "Excel"}
          </button>
          <button onClick={() => handleDownload("concession")} disabled={downloading === "concession"} className="flex-1 rounded-lg bg-amber-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-amber-400 disabled:opacity-50 transition">
            {downloading === "concession" ? "Generating..." : "ARENE Concession"}
          </button>
        </div>
      </div>

      <button onClick={onBack} className="w-full flex items-center justify-center gap-2 rounded-lg bg-white/[0.06] px-4 py-2.5 text-sm font-medium text-afcen-cream/70 hover:bg-white/[0.10] transition">
        <ArrowLeft className="h-4 w-4" /> Back to Optimize
      </button>
    </div>
  );
}

function CapexBar({
  breakdown,
  total,
}: {
  breakdown: AnalysisResult["financial"]["capex_breakdown"];
  total: number;
}) {
  const items = [
    { label: "PV", value: breakdown.pv, color: "bg-yellow-400" },
    { label: "Battery", value: breakdown.battery, color: "bg-blue-400" },
    { label: "Inverter", value: breakdown.inverter, color: "bg-purple-400" },
    { label: "Distribution", value: breakdown.distribution, color: "bg-afcen-gold" },
    { label: "Meters", value: breakdown.meters, color: "bg-cyan-400" },
    { label: "Install", value: breakdown.installation, color: "bg-orange-400" },
    { label: "Soft", value: breakdown.soft_costs, color: "bg-pink-400" },
  ];

  return (
    <div className="space-y-2">
      <div className="flex h-3 rounded-full overflow-hidden">
        {items.map((item) => (
          <div
            key={item.label}
            className={`${item.color}`}
            style={{ width: `${(item.value / total) * 100}%` }}
            title={`${item.label}: $${(item.value / 1000).toFixed(0)}k`}
          />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-1.5 text-xs">
            <span className={`w-2 h-2 rounded-full ${item.color}`} />
            <span className="text-afcen-cream/50">{item.label}</span>
            <span className="ml-auto text-afcen-cream/60">
              ${(item.value / 1000).toFixed(0)}k
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DataRow({ label, value, tip }: { label: string; value: string; tip?: string }) {
  const [showTip, setShowTip] = useState(false);
  return (
    <div className="rounded-md bg-white/[0.03] border border-white/[0.04] px-3 py-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-afcen-cream/50 flex items-center gap-1">
          {label}
          {tip && (
            <button
              onClick={() => setShowTip(!showTip)}
              className="text-afcen-cream/25 hover:text-afcen-gold transition"
              title="More info"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <circle cx="12" cy="12" r="10" strokeWidth="2" />
                <path strokeWidth="2" d="M12 16v-4M12 8h.01" />
              </svg>
            </button>
          )}
        </span>
        <span className="text-sm font-medium text-afcen-cream">{value}</span>
      </div>
      {tip && showTip && (
        <p className="mt-1.5 text-[11px] leading-relaxed text-afcen-cream/40 border-t border-white/[0.06] pt-1.5">{tip}</p>
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-white/[0.03] border border-white/[0.06] p-3">
      <p className="text-xs text-afcen-cream/50">{label}</p>
      <p className="text-lg font-bold text-afcen-gold">{value}</p>
    </div>
  );
}

function PrioritySitesPanel({
  onSelectSite,
  onError,
}: {
  onSelectSite: (site: PrioritySite) => void;
  onError: (msg: string | null) => void;
}) {
  const [sites, setSites] = useState<PrioritySite[]>([]);
  const [provinces, setProvinces] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [province, setProvince] = useState<string>("");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (loaded) return;
    setLoading(true);
    onError(null);
    fetchPrioritySites()
      .then((res) => {
        setSites(res.sites);
        setProvinces(res.provinces);
        setLoaded(true);
      })
      .catch(() => {
        onError("Failed to load priority sites");
      })
      .finally(() => setLoading(false));
  }, [loaded, onError]);

  const filtered = sites.filter((s) => {
    if (province && s.province !== province) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        s.name.toLowerCase().includes(q) ||
        s.district.toLowerCase().includes(q) ||
        s.id.toLowerCase().includes(q)
      );
    }
    return true;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8 gap-2 text-afcen-cream/40 text-sm">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading priority sites...
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-afcen-cream/40" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or district..."
            className="w-full rounded-md bg-white/[0.05] border border-white/[0.08] pl-8 pr-3 py-2 text-sm text-afcen-cream placeholder:text-afcen-cream/30 focus:outline-none focus:ring-1 focus:ring-afcen-gold/50"
          />
        </div>
        <select
          value={province}
          onChange={(e) => setProvince(e.target.value)}
          className="rounded-md bg-white/[0.05] border border-white/[0.08] px-2 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-afcen-gold/50"
        >
          <option value="">All provinces</option>
          {provinces.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>

      <p className="text-xs text-afcen-cream/40">
        {filtered.length} site{filtered.length !== 1 ? "s" : ""} found
        {province ? ` in ${province}` : ""}
      </p>

      <div className="space-y-1 max-h-72 overflow-y-auto rounded-md">
        {filtered.map((site) => (
          <button
            key={site.id}
            onClick={() => {
              setSelectedId(site.id);
              onSelectSite(site);
            }}
            className={`w-full rounded-md px-3 py-2.5 text-left transition ${
              selectedId === site.id
                ? "bg-afcen-gold/20 border border-afcen-gold/30"
                : "bg-white/[0.03] hover:bg-white/[0.06] border border-transparent"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-white truncate">
                {site.name}
              </span>
              <span className="flex items-center gap-1 text-xs font-semibold text-amber-400 shrink-0 ml-2">
                <Star className="h-3 w-3" />
                {site.score.toFixed(1)}
              </span>
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-afcen-cream/50">
              <span>{site.province}, {site.district}</span>
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-afcen-cream/40">
              <span className="flex items-center gap-1">
                <Users className="h-3 w-3" />
                {site.population.toLocaleString()}
              </span>
              <span>{site.demand_kwh_day.toFixed(0)} kWh/day</span>
              <span>{site.dist_grid_km.toFixed(1)} km to grid</span>
              {site.has_health && <span className="text-afcen-gold">Health</span>}
              {site.has_education && <span className="text-blue-400">Edu</span>}
            </div>
          </button>
        ))}
        {filtered.length === 0 && (
          <div className="text-center py-6 text-sm text-afcen-cream/40">
            No sites match your filters
          </div>
        )}
      </div>
    </div>
  );
}
