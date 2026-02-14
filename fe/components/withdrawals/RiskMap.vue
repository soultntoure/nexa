<script setup lang="ts">
import type { Transaction } from '~/composables/useTransactions'

const props = defineProps<{
  transactions: Transaction[]
  selectedId: string | null
}>()

const emit = defineEmits<{
  'select-marker': [tx: Transaction]
}>()

const mapContainer = ref<HTMLElement | null>(null)
let L: any = null
let map: any = null
let markersLayer: any = null
let selectedMarkerRef: any = null

// Country name / ISO-2 / ISO-3 → approximate [lat, lng]
const countryCoords: Record<string, [number, number]> = {
  // Europe
  'United Kingdom': [51.5, -0.12], 'UK': [51.5, -0.12], 'GB': [51.5, -0.12], 'GBR': [51.5, -0.12],
  'Germany': [51.16, 10.45], 'DE': [51.16, 10.45], 'DEU': [51.16, 10.45],
  'France': [46.6, 2.21], 'FR': [46.6, 2.21], 'FRA': [46.6, 2.21],
  'Netherlands': [52.13, 5.29], 'NL': [52.13, 5.29], 'NLD': [52.13, 5.29],
  'Spain': [40.46, -3.75], 'ES': [40.46, -3.75], 'ESP': [40.46, -3.75],
  'Italy': [41.87, 12.57], 'IT': [41.87, 12.57], 'ITA': [41.87, 12.57],
  'Portugal': [39.4, -8.22], 'PT': [39.4, -8.22], 'PRT': [39.4, -8.22],
  'Belgium': [50.5, 4.47], 'BE': [50.5, 4.47], 'BEL': [50.5, 4.47],
  'Switzerland': [46.82, 8.23], 'CH': [46.82, 8.23], 'CHE': [46.82, 8.23],
  'Austria': [47.52, 14.55], 'AT': [47.52, 14.55], 'AUT': [47.52, 14.55],
  'Sweden': [60.13, 18.64], 'SE': [60.13, 18.64], 'SWE': [60.13, 18.64],
  'Norway': [60.47, 8.47], 'NO': [60.47, 8.47], 'NOR': [60.47, 8.47],
  'Denmark': [56.26, 9.5], 'DK': [56.26, 9.5], 'DNK': [56.26, 9.5],
  'Finland': [61.92, 25.75], 'FI': [61.92, 25.75], 'FIN': [61.92, 25.75],
  'Poland': [51.92, 19.15], 'PL': [51.92, 19.15], 'POL': [51.92, 19.15],
  'Ireland': [53.14, -7.69], 'IE': [53.14, -7.69], 'IRL': [53.14, -7.69],
  'Czech Republic': [49.82, 15.47], 'CZ': [49.82, 15.47], 'CZE': [49.82, 15.47],
  'Romania': [45.94, 24.97], 'RO': [45.94, 24.97], 'ROU': [45.94, 24.97],
  'Hungary': [47.16, 19.5], 'HU': [47.16, 19.5], 'HUN': [47.16, 19.5],
  'Greece': [39.07, 21.82], 'GR': [39.07, 21.82], 'GRC': [39.07, 21.82],
  'Croatia': [45.1, 15.2], 'HR': [45.1, 15.2], 'HRV': [45.1, 15.2],
  'Bulgaria': [42.73, 25.49], 'BG': [42.73, 25.49], 'BGR': [42.73, 25.49],
  'Slovakia': [48.67, 19.7], 'SK': [48.67, 19.7], 'SVK': [48.67, 19.7],
  'Slovenia': [46.15, 14.99], 'SI': [46.15, 14.99], 'SVN': [46.15, 14.99],
  'Lithuania': [55.17, 23.88], 'LT': [55.17, 23.88], 'LTU': [55.17, 23.88],
  'Latvia': [56.88, 24.6], 'LV': [56.88, 24.6], 'LVA': [56.88, 24.6],
  'Estonia': [58.6, 25.01], 'EE': [58.6, 25.01], 'EST': [58.6, 25.01],
  'Luxembourg': [49.82, 6.13], 'LU': [49.82, 6.13], 'LUX': [49.82, 6.13],
  'Malta': [35.94, 14.38], 'MT': [35.94, 14.38], 'MLT': [35.94, 14.38],
  'Cyprus': [35.13, 33.43], 'CY': [35.13, 33.43], 'CYP': [35.13, 33.43],
  'Iceland': [64.96, -19.02], 'IS': [64.96, -19.02], 'ISL': [64.96, -19.02],
  'Serbia': [44.02, 21.01], 'RS': [44.02, 21.01], 'SRB': [44.02, 21.01],
  'Ukraine': [48.38, 31.17], 'UA': [48.38, 31.17], 'UKR': [48.38, 31.17],
  'Russia': [61.52, 105.32], 'RU': [61.52, 105.32], 'RUS': [61.52, 105.32],
  'Turkey': [38.96, 35.24], 'TR': [38.96, 35.24], 'TUR': [38.96, 35.24],
  // Americas
  'United States': [37.09, -95.71], 'US': [37.09, -95.71], 'USA': [37.09, -95.71],
  'Canada': [56.13, -106.35], 'CA': [56.13, -106.35], 'CAN': [56.13, -106.35],
  'Mexico': [23.63, -102.55], 'MX': [23.63, -102.55], 'MEX': [23.63, -102.55],
  'Brazil': [-14.24, -51.93], 'BR': [-14.24, -51.93], 'BRA': [-14.24, -51.93],
  'Argentina': [-38.42, -63.62], 'AR': [-38.42, -63.62], 'ARG': [-38.42, -63.62],
  'Colombia': [4.57, -74.3], 'CO': [4.57, -74.3], 'COL': [4.57, -74.3],
  'Chile': [-35.68, -71.54], 'CL': [-35.68, -71.54], 'CHL': [-35.68, -71.54],
  'Peru': [-9.19, -75.02], 'PE': [-9.19, -75.02], 'PER': [-9.19, -75.02],
  // Asia Pacific
  'Japan': [36.2, 138.25], 'JP': [36.2, 138.25], 'JPN': [36.2, 138.25],
  'China': [35.86, 104.2], 'CN': [35.86, 104.2], 'CHN': [35.86, 104.2],
  'South Korea': [35.91, 127.77], 'KR': [35.91, 127.77], 'KOR': [35.91, 127.77],
  'India': [20.59, 78.96], 'IN': [20.59, 78.96], 'IND': [20.59, 78.96],
  'Australia': [-25.27, 133.78], 'AU': [-25.27, 133.78], 'AUS': [-25.27, 133.78],
  'New Zealand': [-40.9, 174.89], 'NZ': [-40.9, 174.89], 'NZL': [-40.9, 174.89],
  'Singapore': [1.35, 103.82], 'SG': [1.35, 103.82], 'SGP': [1.35, 103.82],
  'Malaysia': [4.21, 101.98], 'MY': [4.21, 101.98], 'MYS': [4.21, 101.98],
  'Indonesia': [-0.79, 113.92], 'ID': [-0.79, 113.92], 'IDN': [-0.79, 113.92],
  'Thailand': [15.87, 100.99], 'TH': [15.87, 100.99], 'THA': [15.87, 100.99],
  'Philippines': [12.88, 121.77], 'PH': [12.88, 121.77], 'PHL': [12.88, 121.77],
  'Vietnam': [14.06, 108.28], 'VN': [14.06, 108.28], 'VNM': [14.06, 108.28],
  'Taiwan': [23.7, 120.96], 'TW': [23.7, 120.96], 'TWN': [23.7, 120.96],
  'Hong Kong': [22.4, 114.11], 'HK': [22.4, 114.11], 'HKG': [22.4, 114.11],
  'Pakistan': [30.38, 69.35], 'PK': [30.38, 69.35], 'PAK': [30.38, 69.35],
  'Bangladesh': [23.68, 90.36], 'BD': [23.68, 90.36], 'BGD': [23.68, 90.36],
  // Middle East & Africa
  'UAE': [23.42, 53.85], 'United Arab Emirates': [23.42, 53.85], 'AE': [23.42, 53.85], 'ARE': [23.42, 53.85],
  'Saudi Arabia': [23.89, 45.08], 'SA': [23.89, 45.08], 'SAU': [23.89, 45.08],
  'Israel': [31.05, 34.85], 'IL': [31.05, 34.85], 'ISR': [31.05, 34.85],
  'South Africa': [-30.56, 22.94], 'ZA': [-30.56, 22.94], 'ZAF': [-30.56, 22.94],
  'Nigeria': [9.08, 8.68], 'NG': [9.08, 8.68], 'NGA': [9.08, 8.68],
  'Kenya': [-0.02, 37.91], 'KE': [-0.02, 37.91], 'KEN': [-0.02, 37.91],
  'Egypt': [26.82, 30.8], 'EG': [26.82, 30.8], 'EGY': [26.82, 30.8],
  'Morocco': [31.79, -7.09], 'MA': [31.79, -7.09], 'MAR': [31.79, -7.09],
  'Ghana': [7.95, -1.02], 'GH': [7.95, -1.02], 'GHA': [7.95, -1.02],
}

function getCoords(country: string): [number, number] | null {
  // Try direct match
  const coords = countryCoords[country]
  if (coords) return coords

  // Try case-insensitive match
  const lower = country.toLowerCase()
  for (const [key, val] of Object.entries(countryCoords)) {
    if (key.toLowerCase() === lower) return val
  }

  return null
}

// Add slight jitter so markers from the same country don't overlap
function jitter(coords: [number, number], index: number): [number, number] {
  const angle = (index * 137.508) * (Math.PI / 180) // golden angle
  const radius = 0.5 + (index % 5) * 0.3
  return [
    coords[0] + Math.cos(angle) * radius,
    coords[1] + Math.sin(angle) * radius,
  ]
}

function getMarkerColor(score: number): string {
  if (score >= 0.7) return '#ef4444'
  if (score >= 0.3) return '#f59e0b'
  return '#22c55e'
}

function getMarkerBorderColor(score: number): string {
  if (score >= 0.7) return '#b91c1c'
  if (score >= 0.3) return '#d97706'
  return '#15803d'
}

async function initMap() {
  if (!mapContainer.value) return

  L = (await import('leaflet')).default
  await import('leaflet/dist/leaflet.css')

  map = L.map(mapContainer.value, {
    zoomControl: false,
    attributionControl: false,
  }).setView([30, 10], 3)

  // Zoom control on the right
  L.control.zoom({ position: 'topright' }).addTo(map)

  // Attribution bottom-right
  L.control.attribution({ position: 'bottomright', prefix: false })
    .addAttribution('&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>')
    .addTo(map)

  // Clean, light tile style
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    subdomains: 'abcd',
  }).addTo(map)

  markersLayer = L.layerGroup().addTo(map)

  updateMarkers()
}

function buildPopupContent(tx: Transaction): string {
  const color = getMarkerColor(tx.risk_score)
  return `<div style="min-width:180px">
    <div style="font-weight:600;font-size:13px;margin-bottom:2px">${tx.customer.name}</div>
    <div style="color:#6b7280;font-size:11px;margin-bottom:6px">${tx.customer.email}</div>
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
      <span style="font-weight:700;color:${color};font-size:13px">${tx.risk_score.toFixed(2)}</span>
      <span style="background:${color};height:6px;border-radius:3px;flex:1;opacity:0.3"></span>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:11px;color:#6b7280">
      <span style="text-transform:capitalize">${tx.payment_method}</span>
      <span style="font-weight:600;color:#111">$${tx.amount.toLocaleString()}</span>
    </div>
  </div>`
}

function updateMarkers() {
  if (!map || !markersLayer || !L) return

  markersLayer.clearLayers()
  selectedMarkerRef = null
  const countryIndex: Record<string, number> = {}

  props.transactions.forEach((tx) => {
    const baseCoords = getCoords(tx.customer.country)
    if (!baseCoords) return

    // Track index per country for jitter
    const country = tx.customer.country
    countryIndex[country] = (countryIndex[country] || 0) + 1
    const coords = jitter(baseCoords, countryIndex[country])
    const isSelected = tx.id === props.selectedId

    const marker = L.circleMarker(coords, {
      radius: isSelected ? 12 : 7,
      fillColor: getMarkerColor(tx.risk_score),
      color: isSelected ? '#1d4ed8' : getMarkerBorderColor(tx.risk_score),
      weight: isSelected ? 3 : 1.5,
      fillOpacity: isSelected ? 1 : 0.75,
      opacity: 1,
    })

    // Hover tooltip for non-selected markers
    marker.bindTooltip(
      `<div class="text-xs">
        <div class="font-semibold">${tx.customer.name}</div>
        <div class="text-gray-500">${tx.customer.country}</div>
        <div class="font-bold" style="color: ${getMarkerColor(tx.risk_score)}">Risk: ${tx.risk_score.toFixed(2)}</div>
      </div>`,
      { direction: 'top', offset: [0, -8] },
    )

    // Popup for selected marker (stays open)
    marker.bindPopup(buildPopupContent(tx), {
      offset: [0, -6],
      closeButton: false,
      className: 'risk-popup',
    })

    marker.on('click', () => {
      emit('select-marker', tx)
    })

    marker.addTo(markersLayer)

    if (isSelected) {
      selectedMarkerRef = marker
    }
  })
}

function openSelectedPopup() {
  if (selectedMarkerRef && map) {
    selectedMarkerRef.openPopup()
  }
}

function flyToSelected() {
  if (!map || !props.selectedId || !selectedMarkerRef) return

  const tx = props.transactions.find(t => t.id === props.selectedId)
  if (!tx) return

  const baseCoords = getCoords(tx.customer.country)
  if (!baseCoords) return

  map.flyTo(baseCoords, Math.max(map.getZoom(), 5), { duration: 0.8 })

  // Open popup after fly animation — use timeout as reliable fallback
  setTimeout(openSelectedPopup, 900)
}

onMounted(() => {
  initMap()
})

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
  }
})

watch(() => props.transactions, () => {
  updateMarkers()
  // Re-open popup if a marker is selected (poll refresh destroys markers)
  if (props.selectedId && selectedMarkerRef) {
    nextTick(() => openSelectedPopup())
  }
}, { deep: true })

watch(() => props.selectedId, () => {
  if (map) map.closePopup()
  updateMarkers()
  if (props.selectedId) {
    flyToSelected()
  }
})
</script>

<template>
  <div ref="mapContainer" class="w-full h-full" />
</template>

<style>
/* Leaflet tooltip override for cleaner look */
.leaflet-tooltip {
  border: none !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15) !important;
  border-radius: 8px !important;
  padding: 6px 10px !important;
}

.leaflet-tooltip-top::before {
  border-top-color: white !important;
}

/* Popup styling */
.risk-popup .leaflet-popup-content-wrapper {
  border-radius: 12px !important;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15) !important;
  border: none !important;
  padding: 0 !important;
}

.risk-popup .leaflet-popup-content {
  margin: 12px 14px !important;
}

.risk-popup .leaflet-popup-tip {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1) !important;
}
</style>
