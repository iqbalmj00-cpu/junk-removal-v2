'use client';

import { useEffect, useRef } from 'react';

const SERVICE_AREAS = [
    { name: 'Houston', lat: 29.7604, lng: -95.3698 },
    { name: 'Sugar Land', lat: 29.6197, lng: -95.6349 },
    { name: 'Katy', lat: 29.7858, lng: -95.8245 },
    { name: 'The Woodlands', lat: 30.1658, lng: -95.4613 },
    { name: 'Pearland', lat: 29.5635, lng: -95.2860 },
    { name: 'Missouri City', lat: 29.6186, lng: -95.5377 },
    { name: 'Cypress', lat: 29.9691, lng: -95.6972 },
    { name: 'Spring', lat: 30.0799, lng: -95.4172 },
    { name: 'League City', lat: 29.5075, lng: -95.0949 },
    { name: 'Pasadena', lat: 29.6911, lng: -95.2091 },
];

export default function CoverageMap() {
    const mapRef = useRef<HTMLDivElement>(null);
    const mapInstanceRef = useRef<any>(null);

    useEffect(() => {
        if (mapInstanceRef.current) return; // Already initialized

        // Load Leaflet CSS
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(link);

        // Load Leaflet JS
        const script = document.createElement('script');
        script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
        script.onload = () => {
            if (!mapRef.current || mapInstanceRef.current) return;

            const L = (window as any).L;

            // Create map centered on Houston metro
            const map = L.map(mapRef.current, {
                scrollWheelZoom: false,
            }).setView([29.82, -95.40], 9);

            mapInstanceRef.current = map;

            // Add tile layer (OpenStreetMap)
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors',
                maxZoom: 18,
            }).addTo(map);

            // Custom orange marker icon
            const orangeIcon = L.divIcon({
                className: 'custom-marker',
                html: `<div style="
                    width: 32px;
                    height: 32px;
                    background: #f97316;
                    border: 3px solid #fff;
                    border-radius: 50% 50% 50% 0;
                    transform: rotate(-45deg);
                    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                "><div style="
                    width: 10px;
                    height: 10px;
                    background: #fff;
                    border-radius: 50%;
                    transform: rotate(45deg);
                "></div></div>`,
                iconSize: [32, 32],
                iconAnchor: [16, 32],
                popupAnchor: [0, -32],
            });

            // Add markers for each service area
            SERVICE_AREAS.forEach((area) => {
                L.marker([area.lat, area.lng], { icon: orangeIcon })
                    .addTo(map)
                    .bindPopup(
                        `<div style="text-align:center;font-family:system-ui,sans-serif;">
                            <strong style="font-size:14px;color:#0f172a;">${area.name}</strong>
                            <br/>
                            <span style="font-size:12px;color:#64748b;">Service Area</span>
                        </div>`
                    );
            });

            // Draw a subtle coverage circle around Houston center
            L.circle([29.76, -95.38], {
                radius: 65000, // ~40 miles
                color: '#f97316',
                fillColor: '#f97316',
                fillOpacity: 0.06,
                weight: 2,
                opacity: 0.3,
                dashArray: '8, 8',
            }).addTo(map);
        };
        document.head.appendChild(script);

        return () => {
            if (mapInstanceRef.current) {
                mapInstanceRef.current.remove();
                mapInstanceRef.current = null;
            }
        };
    }, []);

    return (
        <div
            ref={mapRef}
            className="w-full h-full"
            style={{ minHeight: '400px' }}
        />
    );
}
