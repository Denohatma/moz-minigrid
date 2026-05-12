"use client";

import { useState, useCallback, useRef } from "react";
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
} from "lucide-react";
import Papa from "papaparse";
import MozMap from "@/components/MozMap";
import { analyzeSite, lookupCluster, downloadReport } from "@/lib/api";
import type { AnalysisResult, ClusterInfo } from "@/lib/api";

interface ParsedSite {
  name?: string;
  latitude: number;
  longitude: number;
  row: number;
}

type InputMode = "coordinates" | "upload";

type WizardStep = "select" | "review" | "parameters" | "results";

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
      setStep("results");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      <header className="border-b border-white/10 bg-slate-900/95 backdrop-blur sticky top-0 z-50">
        <div className="mx-auto max-w-7xl px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <Zap className="h-6 w-6 text-emerald-400" />
              <span className="font-bold text-white">Moz</span>
            </Link>
            <span className="text-slate-500">/</span>
            <span className="text-sm text-slate-300">New Analysis</span>
          </div>
          <StepIndicator current={step} />
        </div>
      </header>

      <div className="flex-1 flex">
        <div className="flex-1 relative">
          <MozMap onSiteSelect={handleMapClick} selectedSite={selectedSite} />
        </div>

        <div className="w-[420px] border-l border-white/10 bg-slate-800/50 overflow-y-auto">
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
              onProceed={() => setStep("parameters")}
            />
          )}

          {step === "parameters" && (
            <ParametersPanel
              overrides={overrides}
              onOverrideChange={(key, val) =>
                setOverrides((prev) => ({ ...prev, [key]: val }))
              }
              onBack={() => setStep("review")}
              onAnalyze={handleAnalyze}
              isAnalyzing={isAnalyzing}
              error={error}
            />
          )}

          {step === "results" && result && selectedSite && (
            <ResultsPanel result={result} site={selectedSite} onBack={() => setStep("parameters")} />
          )}
        </div>
      </div>
    </div>
  );
}

function StepIndicator({ current }: { current: WizardStep }) {
  const steps: { key: WizardStep; label: string }[] = [
    { key: "select", label: "Select Site" },
    { key: "review", label: "Review Data" },
    { key: "parameters", label: "Parameters" },
    { key: "results", label: "Results" },
  ];
  const currentIdx = steps.findIndex((s) => s.key === current);

  return (
    <div className="flex items-center gap-2">
      {steps.map((s, i) => (
        <div key={s.key} className="flex items-center gap-2">
          <div
            className={`flex items-center gap-1.5 text-xs font-medium ${
              i <= currentIdx ? "text-emerald-400" : "text-slate-500"
            }`}
          >
            <span
              className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                i < currentIdx
                  ? "bg-emerald-500 text-white"
                  : i === currentIdx
                    ? "border border-emerald-400 text-emerald-400"
                    : "border border-slate-600 text-slate-500"
              }`}
            >
              {i < currentIdx ? <CheckCircle className="w-3 h-3" /> : i + 1}
            </span>
            <span className="hidden sm:inline">{s.label}</span>
          </div>
          {i < steps.length - 1 && (
            <div className="w-6 h-px bg-slate-700" />
          )}
        </div>
      ))}
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
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <MapPin className="h-5 w-5 text-emerald-400" />
          Select Site
        </h2>
        <p className="mt-1 text-sm text-slate-400">
          Click the map, enter coordinates, or upload a file with site data.
        </p>
      </div>

      <div className="flex rounded-lg bg-slate-700/50 p-0.5">
        <button
          onClick={() => onInputModeChange("coordinates")}
          className={`flex-1 flex items-center justify-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium transition ${
            inputMode === "coordinates"
              ? "bg-slate-600 text-white"
              : "text-slate-400 hover:text-slate-300"
          }`}
        >
          <MapPin className="h-3.5 w-3.5" />
          Coordinates
        </button>
        <button
          onClick={() => onInputModeChange("upload")}
          className={`flex-1 flex items-center justify-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium transition ${
            inputMode === "upload"
              ? "bg-slate-600 text-white"
              : "text-slate-400 hover:text-slate-300"
          }`}
        >
          <Upload className="h-3.5 w-3.5" />
          Upload File
        </button>
      </div>

      {inputMode === "coordinates" && (
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">
              Latitude
            </label>
            <input
              type="text"
              value={latitude}
              onChange={(e) => onLatChange(e.target.value)}
              placeholder="-15.4347"
              className="w-full rounded-md bg-slate-700 border border-slate-600 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">
              Longitude
            </label>
            <input
              type="text"
              value={longitude}
              onChange={(e) => onLngChange(e.target.value)}
              placeholder="40.6734"
              className="w-full rounded-md bg-slate-700 border border-slate-600 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
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
                  ? "border-emerald-400 bg-emerald-500/10"
                  : "border-slate-600 bg-slate-700/30 hover:border-slate-500"
              }`}
            >
              <FileSpreadsheet className="h-8 w-8 mx-auto text-slate-400 mb-2" />
              <p className="text-sm text-slate-300">
                Drop a CSV file here or{" "}
                <span className="text-emerald-400 font-medium">browse</span>
              </p>
              <p className="text-xs text-slate-500 mt-1">
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
              <div className="flex items-center justify-between rounded-md bg-slate-700/50 px-3 py-2">
                <div className="flex items-center gap-2 text-sm text-white min-w-0">
                  <FileSpreadsheet className="h-4 w-4 text-emerald-400 shrink-0" />
                  <span className="truncate">{fileName}</span>
                  <span className="text-xs text-slate-400 shrink-0">
                    ({parsedSites.length} site{parsedSites.length !== 1 ? "s" : ""})
                  </span>
                </div>
                <button
                  onClick={clearFile}
                  className="text-slate-400 hover:text-white transition p-1"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {parsedSites.length > 1 && (
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-2">
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
                            ? "bg-emerald-500/20 border border-emerald-500/30 text-white"
                            : "bg-slate-700/50 text-slate-300 hover:bg-slate-700"
                        }`}
                      >
                        <span className="truncate">
                          {site.name || `Site (row ${site.row})`}
                        </span>
                        <span className="text-xs text-slate-400 shrink-0 ml-2">
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

      {error && (
        <div className="flex items-start gap-2 rounded-md bg-red-500/10 border border-red-500/20 p-3">
          <AlertTriangle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      <button
        onClick={onSubmit}
        disabled={!latitude || !longitude || isLoading}
        className="w-full flex items-center justify-center gap-2 rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed transition"
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
        <div className="rounded-md bg-emerald-500/10 border border-emerald-500/20 p-3">
          <p className="text-sm text-emerald-300">
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
}: {
  site: { lat: number; lng: number };
  cluster: ClusterInfo | null;
  onBack: () => void;
  onProceed: () => void;
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
        <h2 className="text-lg font-semibold text-white">Review Site Data</h2>
        <p className="mt-1 text-sm text-slate-400">
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
            <DataRow label="Population" value={cluster.population.toLocaleString()} />
            {cluster.num_buildings != null && <DataRow label="Buildings" value={cluster.num_buildings.toLocaleString()} />}
            {cluster.dre_num_connections != null && <DataRow label="Est. connections" value={cluster.dre_num_connections.toLocaleString()} />}
            <DataRow label="Area" value={`${cluster.area_km2.toFixed(3)} km²`} />
            {cluster.building_density_pct != null && <DataRow label="Building density" value={`${cluster.building_density_pct.toFixed(1)}%`} />}
          </div>

          <div className="space-y-2">
            <SectionHeader label="Energy & Demand" />
            <DataRow label="Solar PV potential" value={`${cluster.ghi_kwh_m2_year.toFixed(0)} kWh/kWp/yr`} />
            {cluster.dre_demand_kwh_day != null && <DataRow label="Est. demand" value={`${cluster.dre_demand_kwh_day.toFixed(1)} kWh/day`} />}
            {cluster.dre_demand_per_conn_kwh_day != null && <DataRow label="Demand/connection" value={`${cluster.dre_demand_per_conn_kwh_day.toFixed(3)} kWh/day`} />}
            <DataRow label="Nightlight" value={cluster.has_nightlight ? `Yes (${cluster.nightlight_overlap_pct?.toFixed(0) ?? 0}% coverage)` : "No"} />
          </div>

          <div className="space-y-2">
            <SectionHeader label="Grid & Infrastructure" />
            <DataRow label="Existing grid" value={`${cluster.dist_grid_mv_km.toFixed(1)} km`} />
            {cluster.dist_grid_planned_km != null && <DataRow label="Planned grid" value={`${cluster.dist_grid_planned_km.toFixed(1)} km`} />}
            <DataRow label="Main road" value={cluster.main_road_access ? `${cluster.dist_road_km.toFixed(1)} km (access)` : `${cluster.dist_road_km.toFixed(1)} km`} />
            {cluster.nearest_hub_name && <DataRow label="Nearest hub" value={`${cluster.nearest_hub_name} (${cluster.dist_nearest_hub_km?.toFixed(0) ?? "?"} km)`} />}
          </div>

          <div className="space-y-2">
            <SectionHeader label="Social & Economic" />
            {cluster.mean_rwi != null && <DataRow label="Wealth index" value={cluster.mean_rwi.toFixed(2)} />}
            <DataRow label="Education" value={cluster.has_education_facility ? `Yes (${cluster.num_education_facilities ?? 0})` : "None nearby"} />
            <DataRow label="Healthcare" value={cluster.has_health_facility ? `Yes (${cluster.num_health_facilities ?? 0})` : "None nearby"} />
            {cluster.crop_types && <DataRow label="Crops" value={cluster.crop_types} />}
            {cluster.security_risk && (
              <DataRow
                label="Security"
                value={cluster.security_risk.charAt(0).toUpperCase() + cluster.security_risk.slice(1)}
              />
            )}
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-sm text-slate-400 py-4">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading settlement data...
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-slate-700 px-4 py-2.5 text-sm font-medium text-slate-300 hover:bg-slate-600 transition"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <button
          onClick={onProceed}
          disabled={!cluster}
          className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-400 disabled:opacity-50 transition"
        >
          Continue
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function SectionHeader({ label }: { label: string }) {
  return <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 pt-1">{label}</h3>;
}

const PARAM_FIELDS: { key: string; label: string; defaultValue: string }[] = [
  { key: "discount_rate", label: "Discount rate", defaultValue: "0.10" },
  { key: "cost_pv_per_kwp", label: "PV cost ($/kWp)", defaultValue: "1100" },
  { key: "cost_battery_per_kwh", label: "Battery cost ($/kWh)", defaultValue: "450" },
  { key: "affordable_tariff", label: "Target tariff ($/kWh)", defaultValue: "0.35" },
  { key: "demand_growth_rate", label: "Demand growth (%/yr)", defaultValue: "0.03" },
  { key: "days_of_autonomy", label: "Days of autonomy", defaultValue: "1.5" },
  { key: "om_rate", label: "O&M rate (% CAPEX)", defaultValue: "0.03" },
];

function ParametersPanel({
  overrides,
  onOverrideChange,
  onBack,
  onAnalyze,
  isAnalyzing,
  error,
}: {
  overrides: Record<string, string>;
  onOverrideChange: (key: string, value: string) => void;
  onBack: () => void;
  onAnalyze: () => void;
  isAnalyzing: boolean;
  error: string | null;
}) {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white">Financial Parameters</h2>
        <p className="mt-1 text-sm text-slate-400">
          Adjust assumptions or use Mozambique defaults.
        </p>
      </div>

      <div className="space-y-4">
        {PARAM_FIELDS.map((p) => (
          <div key={p.key}>
            <label className="block text-xs font-medium text-slate-400 mb-1">
              {p.label}
            </label>
            <input
              type="text"
              value={overrides[p.key] ?? p.defaultValue}
              onChange={(e) => onOverrideChange(p.key, e.target.value)}
              className="w-full rounded-md bg-slate-700 border border-slate-600 px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
        ))}
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-md bg-red-500/10 border border-red-500/20 p-3">
          <AlertTriangle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-slate-700 px-4 py-2.5 text-sm font-medium text-slate-300 hover:bg-slate-600 transition"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <button
          onClick={onAnalyze}
          disabled={isAnalyzing}
          className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-400 disabled:opacity-50 transition"
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              Run Analysis
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}

function ResultsPanel({
  result,
  site,
  onBack,
}: {
  result: AnalysisResult;
  site: { lat: number; lng: number };
  onBack: () => void;
}) {
  const [downloading, setDownloading] = useState<"pdf" | "excel" | "pfs" | null>(null);

  const handleDownload = async (format: "pdf" | "excel" | "pfs") => {
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
            : "moz-report.html";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silent fail on download
    } finally {
      setDownloading(null);
    }
  };
  const f = result.financial;
  const s = result.sizing;
  const d = result.demand;
  const gr = result.grid_risk;
  const sol = result.solar_resource;
  const dist = result.distribution;
  const carb = result.carbon;

  const riskColor =
    gr.risk_level === "critical"
      ? "text-red-400"
      : gr.risk_level === "high"
        ? "text-orange-400"
        : gr.risk_level === "medium"
          ? "text-yellow-400"
          : "text-emerald-400";

  return (
    <div className="p-6 space-y-6 text-white">
      <div>
        <h2 className="text-lg font-semibold">Analysis Results</h2>
        <p className="mt-1 text-sm text-slate-400">
          {d.households} households | Tier {d.demand_tier} demand |{" "}
          {d.daily_energy_kwh.toFixed(0)} kWh/day
        </p>
      </div>

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

      <div className="grid grid-cols-2 gap-3">
        <MetricCard label="LCOE" value={`$${f.lcoe_usd_kwh.toFixed(2)}/kWh`} />
        <MetricCard label="Project IRR" value={`${f.irr_pct.toFixed(1)}%`} />
        <MetricCard label="NPV" value={`$${(f.npv_usd / 1000).toFixed(0)}k`} />
        <MetricCard label="Payback" value={`${f.payback_years.toFixed(1)} yrs`} />
        <MetricCard label="CAPEX" value={`$${(f.total_capex_usd / 1000).toFixed(0)}k`} />
        <MetricCard label="Min DSCR" value={f.dscr.toFixed(2)} />
        {f.equity_irr_pct != null && (
          <MetricCard label="Equity IRR" value={`${f.equity_irr_pct.toFixed(1)}%`} />
        )}
        {f.capex_per_wp != null && (
          <MetricCard label="CAPEX/Wp" value={`$${f.capex_per_wp.toFixed(2)}`} />
        )}
      </div>

      {sol && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-slate-300 flex items-center gap-1.5">
            <Sun className="h-4 w-4 text-yellow-400" />
            Solar Resource
          </h3>
          <DataRow label="Annual GHI" value={`${sol.annual_ghi_kwh_m2.toFixed(0)} kWh/m²/yr`} />
          <DataRow label="Specific Yield" value={`${sol.specific_yield_kwh_per_kwp.toFixed(0)} kWh/kWp`} />
          <DataRow label="Performance Ratio" value={`${(sol.performance_ratio * 100).toFixed(1)}%`} />
          <DataRow label="Data Source" value={sol.data_source} />
        </div>
      )}

      <div className="space-y-2">
        <h3 className="text-sm font-medium text-slate-300 flex items-center gap-1.5">
          <Battery className="h-4 w-4 text-blue-400" />
          System Sizing
        </h3>
        <DataRow label="PV Array" value={`${s.pv_kwp.toFixed(1)} kWp`} />
        <DataRow label="Battery" value={`${s.battery_kwh_nominal.toFixed(0)} kWh (${s.battery_kwh_usable.toFixed(0)} usable)`} />
        <DataRow label="Inverter" value={`${s.inverter_kva.toFixed(1)} kVA`} />
        {s.dc_ac_ratio != null && <DataRow label="DC/AC Ratio" value={s.dc_ac_ratio.toFixed(2)} />}
        <DataRow label="LV Network" value={`${s.lv_line_km.toFixed(1)} km`} />
        <DataRow label="Transformers" value={`${s.service_transformers}`} />
      </div>

      {s.annual_generation_kwh != null && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-slate-300 flex items-center gap-1.5">
            <Zap className="h-4 w-4 text-amber-400" />
            Dispatch Simulation
          </h3>
          <DataRow label="Annual Generation" value={`${(s.annual_generation_kwh / 1000).toFixed(1)} MWh`} />
          {s.annual_energy_served_kwh != null && (
            <DataRow label="Energy Served" value={`${(s.annual_energy_served_kwh / 1000).toFixed(1)} MWh`} />
          )}
          {s.unmet_energy_pct != null && <DataRow label="Unmet Energy" value={`${s.unmet_energy_pct.toFixed(1)}%`} />}
          {s.curtailment_pct != null && <DataRow label="Curtailment" value={`${s.curtailment_pct.toFixed(1)}%`} />}
          {s.capacity_factor_pct != null && <DataRow label="Capacity Factor" value={`${s.capacity_factor_pct.toFixed(1)}%`} />}
          {s.battery_cycles_per_year != null && <DataRow label="Battery Cycles/yr" value={`${s.battery_cycles_per_year.toFixed(0)}`} />}
        </div>
      )}

      <div className="space-y-2">
        <h3 className="text-sm font-medium text-slate-300 flex items-center gap-1.5">
          <DollarSign className="h-4 w-4 text-emerald-400" />
          Financial Structure
        </h3>
        <DataRow label="Cost-reflective tariff" value={`$${f.cost_reflective_tariff_usd.toFixed(3)}/kWh`} />
        <DataRow label="Affordable tariff" value={`$${f.affordable_tariff_usd.toFixed(3)}/kWh`} />
        {f.grant_amount_usd != null && <DataRow label="Grant / Subsidy" value={`$${(f.grant_amount_usd / 1000).toFixed(0)}k`} />}
        {f.debt_amount_usd != null && <DataRow label="Concessional Debt" value={`$${(f.debt_amount_usd / 1000).toFixed(0)}k`} />}
        {f.equity_amount_usd != null && <DataRow label="Developer Equity" value={`$${(f.equity_amount_usd / 1000).toFixed(0)}k`} />}
        {f.annual_opex_usd != null && <DataRow label="Annual OPEX" value={`$${(f.annual_opex_usd / 1000).toFixed(1)}k`} />}
        <DataRow label="Subsidy gap" value={`$${f.subsidy_gap_per_connection_usd.toFixed(0)}/conn (${f.subsidy_gap_pct_capex.toFixed(0)}% CAPEX)`} />
      </div>

      {dist && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-slate-300 flex items-center gap-1.5">
            <Network className="h-4 w-4 text-cyan-400" />
            Distribution Network
          </h3>
          <DataRow label="Line Length" value={`${dist.total_line_length_m.toFixed(0)} m`} />
          <DataRow label="Poles" value={`${dist.pole_count}`} />
          <DataRow label="Customers" value={`${dist.customers_connected}`} />
          <DataRow label="Network Cost" value={`$${(dist.total_network_cost_usd / 1000).toFixed(1)}k`} />
          <DataRow label="Cost/Connection" value={`$${dist.cost_per_connection_usd.toFixed(0)}`} />
          <DataRow label="Voltage Drop" value={`${dist.voltage_drop_max_pct.toFixed(1)}%`} />
        </div>
      )}

      <div className="space-y-2">
        <h3 className={`text-sm font-medium flex items-center gap-1.5 ${riskColor}`}>
          <ShieldAlert className="h-4 w-4" />
          Grid Risk: {gr.risk_level.charAt(0).toUpperCase() + gr.risk_level.slice(1)}
        </h3>
        <DataRow label="Nearest MV" value={`${gr.dist_mv_km.toFixed(1)} km`} />
        <DataRow label="Nearest HV" value={`${gr.dist_hv_km.toFixed(1)} km`} />
        <DataRow label="Assessment" value={gr.risk_label} />
        {gr.esmap_recommended && <DataRow label="ESMAP Strategy" value={gr.esmap_recommended} />}
        {gr.scenarios && gr.scenarios.map((sc) => (
          <DataRow
            key={sc.arrival_year}
            label={`Grid at year ${sc.arrival_year}`}
            value={`IRR ${sc.adjusted_irr.toFixed(1)}% | ${sc.investment_recovered_pct.toFixed(0)}% recovered`}
          />
        ))}
      </div>

      {carb && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-slate-300 flex items-center gap-1.5">
            <Leaf className="h-4 w-4 text-green-400" />
            Carbon Credits
          </h3>
          <DataRow label="Emission Reductions" value={`${carb.annual_emission_reductions_tco2e.toFixed(1)} tCO2e/yr`} />
          <DataRow label="Diesel Displaced" value={`${(carb.diesel_displaced_litres_yr / 1000).toFixed(1)}k litres/yr`} />
          <DataRow label="Methodology" value={carb.recommended_methodology} />
          {carb.revenue_by_scenario.market != null && (
            <DataRow label="Market Revenue" value={`$${carb.revenue_by_scenario.market.toFixed(0)}/yr`} />
          )}
          {carb.revenue_by_scenario.high != null && (
            <DataRow label="High Scenario" value={`$${carb.revenue_by_scenario.high.toFixed(0)}/yr`} />
          )}
        </div>
      )}

      <div className="space-y-2">
        <h3 className="text-sm font-medium text-slate-300">CAPEX Breakdown</h3>
        <CapexBar breakdown={f.capex_breakdown} total={f.total_capex_usd} />
      </div>

      <div className="space-y-2">
        <div className="flex gap-3">
          <button
            onClick={() => handleDownload("pdf")}
            disabled={downloading === "pdf"}
            className="flex-1 rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-400 disabled:opacity-50 transition"
          >
            {downloading === "pdf" ? "Generating..." : "Report"}
          </button>
          <button
            onClick={() => handleDownload("pfs")}
            disabled={downloading === "pfs"}
            className="flex-1 rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-400 disabled:opacity-50 transition"
          >
            {downloading === "pfs" ? "Generating..." : "PFS (.docx)"}
          </button>
          <button
            onClick={() => handleDownload("excel")}
            disabled={downloading === "excel"}
            className="flex-1 rounded-lg bg-blue-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-400 disabled:opacity-50 transition"
          >
            {downloading === "excel" ? "Generating..." : "Excel"}
          </button>
        </div>
        <button
          onClick={onBack}
          className="w-full rounded-lg bg-slate-700 px-4 py-2.5 text-sm font-medium text-slate-300 hover:bg-slate-600 transition"
        >
          Adjust Parameters
        </button>
      </div>
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
    { label: "Distribution", value: breakdown.distribution, color: "bg-emerald-400" },
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
            <span className="text-slate-400">{item.label}</span>
            <span className="ml-auto text-slate-300">
              ${(item.value / 1000).toFixed(0)}k
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DataRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-md bg-slate-700/50 px-3 py-2">
      <span className="text-xs text-slate-400">{label}</span>
      <span className="text-sm font-medium text-white">{value}</span>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-700/50 border border-slate-600/50 p-3">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="text-lg font-bold text-emerald-400">{value}</p>
    </div>
  );
}
