"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

interface MozMapProps {
  onSiteSelect?: (lat: number, lng: number) => void;
  selectedSite?: { lat: number; lng: number } | null;
  clusterBoundary?: GeoJSON.Feature | null;
}

const MOZAMBIQUE_CENTER: [number, number] = [35.5, -18.5];
const MOZAMBIQUE_ZOOM = 5.5;

export default function MozMap({
  onSiteSelect,
  selectedSite,
  clusterBoundary,
}: MozMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const marker = useRef<maplibregl.Marker | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  const handleClick = useCallback(
    (e: maplibregl.MapMouseEvent) => {
      const { lng, lat } = e.lngLat;
      onSiteSelect?.(lat, lng);
    },
    [onSiteSelect]
  );

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          satellite: {
            type: "raster",
            tiles: [
              "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            ],
            tileSize: 256,
            attribution: "&copy; Esri, Maxar, Earthstar Geographics",
            maxzoom: 18,
          },
          labels: {
            type: "raster",
            tiles: [
              "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
            ],
            tileSize: 256,
            maxzoom: 18,
          },
        },
        layers: [
          {
            id: "satellite-tiles",
            type: "raster",
            source: "satellite",
            minzoom: 0,
            maxzoom: 18,
          },
          {
            id: "label-tiles",
            type: "raster",
            source: "labels",
            minzoom: 0,
            maxzoom: 18,
          },
        ],
      },
      center: MOZAMBIQUE_CENTER,
      zoom: MOZAMBIQUE_ZOOM,
      maxBounds: [
        [29, -27],
        [42, -10],
      ],
    });

    map.current.addControl(new maplibregl.NavigationControl(), "top-right");
    map.current.addControl(new maplibregl.ScaleControl(), "bottom-left");

    map.current.on("load", () => setIsLoaded(true));
    map.current.on("click", handleClick);

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, [handleClick]);

  useEffect(() => {
    if (!map.current || !selectedSite) return;

    if (marker.current) marker.current.remove();

    marker.current = new maplibregl.Marker({ color: "#10b981" })
      .setLngLat([selectedSite.lng, selectedSite.lat])
      .addTo(map.current);

    map.current.flyTo({
      center: [selectedSite.lng, selectedSite.lat],
      zoom: 12,
      duration: 1500,
    });
  }, [selectedSite]);

  useEffect(() => {
    if (!map.current || !isLoaded) return;

    if (map.current.getSource("cluster-boundary")) {
      map.current.removeLayer("cluster-fill");
      map.current.removeLayer("cluster-outline");
      map.current.removeSource("cluster-boundary");
    }

    if (!clusterBoundary) return;

    map.current.addSource("cluster-boundary", {
      type: "geojson",
      data: clusterBoundary,
    });

    map.current.addLayer({
      id: "cluster-fill",
      type: "fill",
      source: "cluster-boundary",
      paint: {
        "fill-color": "#10b981",
        "fill-opacity": 0.15,
      },
    });

    map.current.addLayer({
      id: "cluster-outline",
      type: "line",
      source: "cluster-boundary",
      paint: {
        "line-color": "#10b981",
        "line-width": 2,
      },
    });
  }, [clusterBoundary, isLoaded]);

  return (
    <div className="relative w-full h-full rounded-lg overflow-hidden">
      <div ref={mapContainer} className="w-full h-full" />
      {!isLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-800/80">
          <div className="text-white text-sm">Loading map...</div>
        </div>
      )}
    </div>
  );
}
