import React, { useState } from 'react'

export default function LocationPicker({
  locationValue,
  latitudeValue,
  longitudeValue,
  onChange,
  placeholder = 'Enter address, sector, or locality...',
  required = false,
}) {
  const [geoLoading, setGeoLoading] = useState(false)
  const [geoError, setGeoError] = useState(null)

  const handleUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      setGeoError('Geolocation is not supported by your browser.')
      return
    }

    setGeoLoading(true)
    setGeoError(null)

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = parseFloat(position.coords.latitude.toFixed(6))
        const lng = parseFloat(position.coords.longitude.toFixed(6))

        onChange({
          location: locationValue || `Current Location (${lat}, ${lng})`,
          latitude: lat,
          longitude: lng,
        })
        setGeoLoading(false)
      },
      (error) => {
        console.warn('Geolocation permission denied or unavailable:', error.message)
        setGeoError('Location permission denied. Please type your location manually.')
        setGeoLoading(false)
      },
      { timeout: 10000, enableHighAccuracy: true }
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="block text-xs font-bold text-slate-700">
          Service Location / Address {required && <span className="text-rose-600">*</span>}
        </label>
        <button
          type="button"
          onClick={handleUseCurrentLocation}
          disabled={geoLoading}
          className="text-xs font-semibold text-blue-700 hover:text-blue-800 flex items-center gap-1 bg-blue-50 hover:bg-blue-100 px-2.5 py-1 rounded border border-blue-200 transition disabled:opacity-50"
        >
          {geoLoading ? (
            <span className="inline-block animate-spin">⌛</span>
          ) : (
            <span>📍 Use My Current Location</span>
          )}
        </button>
      </div>

      <input
        type="text"
        required={required}
        value={locationValue || ''}
        onChange={(e) =>
          onChange({
            location: e.target.value,
            latitude: latitudeValue,
            longitude: longitudeValue,
          })
        }
        placeholder={placeholder}
        className="w-full px-3.5 py-2 bg-white border border-slate-300 rounded text-slate-900 text-sm focus:ring-2 focus:ring-blue-600 focus:border-blue-600 outline-none transition"
      />

      {latitudeValue !== null && latitudeValue !== undefined && longitudeValue !== null && longitudeValue !== undefined && (
        <div className="text-[11px] text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded border border-emerald-200 flex items-center gap-1.5">
          <span>✓ Geographic coordinates attached:</span>
          <span className="font-mono font-medium">({latitudeValue}, {longitudeValue})</span>
          <button
            type="button"
            onClick={() => onChange({ location: locationValue, latitude: null, longitude: null })}
            className="ml-auto text-slate-400 hover:text-slate-600"
            title="Clear coordinates"
          >
            ✕
          </button>
        </div>
      )}

      {geoError && (
        <p className="text-[11px] text-amber-700 bg-amber-50 px-2.5 py-1 rounded border border-amber-200">
          ⚠️ {geoError}
        </p>
      )}
    </div>
  )
}
