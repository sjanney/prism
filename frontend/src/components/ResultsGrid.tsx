import { useState } from 'react'
import { api } from '../api/client'
import type { SearchResultItem } from '../types'

interface ResultsGridProps {
  results: SearchResultItem[]
  onSaveCollection?: (name: string, resultIds: number[]) => void
}

export default function ResultsGrid({ results, onSaveCollection }: ResultsGridProps) {
  const [selectedFrame, setSelectedFrame] = useState<SearchResultItem | null>(null)

  if (results.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 text-center">
        <p className="text-gray-400">No results found. Try adjusting your search query or confidence threshold.</p>
      </div>
    )
  }

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {results.map((result, idx) => (
          <div
            key={result.frame_id || idx}
            className="bg-gray-800 rounded-lg overflow-hidden cursor-pointer hover:ring-2 hover:ring-blue-500 transition-all"
            onClick={() => setSelectedFrame(result)}
          >
            <div className="relative">
              {result.thumbnail_url ? (
                <img
                  src={result.thumbnail_url}
                  alt={`Frame ${result.frame_id}`}
                  className="w-full h-48 object-cover"
                  loading="lazy"
                />
              ) : result.frame_id ? (
                <img
                  src={api.getThumbnail(result.frame_id)}
                  alt={`Frame ${result.frame_id}`}
                  className="w-full h-48 object-cover"
                  loading="lazy"
                />
              ) : (
                <div className="w-full h-48 bg-gray-700 flex items-center justify-center">
                  <span className="text-gray-500">No image</span>
                </div>
              )}
              <div className="absolute top-2 right-2 bg-black/70 px-2 py-1 rounded text-xs font-semibold text-white">
                {result.confidence.toFixed(1)}%
              </div>
            </div>
            <div className="p-3">
              <p className="text-xs text-gray-400 truncate">
                Frame {result.frame_id || 'N/A'}
              </p>
              {result.metadata.camera_angle && (
                <p className="text-xs text-gray-500">{result.metadata.camera_angle}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {selectedFrame && (
        <FrameModal
          frame={selectedFrame}
          onClose={() => setSelectedFrame(null)}
          onSaveCollection={onSaveCollection}
        />
      )}
    </div>
  )
}

interface FrameModalProps {
  frame: SearchResultItem
  onClose: () => void
  onSaveCollection?: (name: string, resultIds: number[]) => void
}

function FrameModal({ frame, onClose, onSaveCollection }: FrameModalProps) {
  return (
    <div className="fixed inset-0 bg-black/75 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-xl font-semibold text-white">Frame Details</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white"
            >
              ✕
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              {frame.thumbnail_url ? (
                <img
                  src={frame.thumbnail_url}
                  alt={`Frame ${frame.frame_id}`}
                  className="w-full rounded-lg"
                />
              ) : frame.frame_id ? (
                <img
                  src={api.getThumbnail(frame.frame_id)}
                  alt={`Frame ${frame.frame_id}`}
                  className="w-full rounded-lg"
                />
              ) : null}
            </div>

            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-1">Confidence</h4>
                <p className="text-2xl font-bold text-white">{frame.confidence.toFixed(1)}%</p>
              </div>

              {frame.frame_id && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-1">Frame ID</h4>
                  <p className="text-white">{frame.frame_id}</p>
                </div>
              )}

              {frame.timestamp && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-1">Timestamp</h4>
                  <p className="text-white">{new Date(frame.timestamp).toLocaleString()}</p>
                </div>
              )}

              {frame.metadata.weather && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-1">Weather</h4>
                  <p className="text-white capitalize">{frame.metadata.weather}</p>
                </div>
              )}

              {frame.metadata.camera_angle && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-1">Camera</h4>
                  <p className="text-white">{frame.metadata.camera_angle}</p>
                </div>
              )}

              {frame.metadata.gps && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-1">GPS</h4>
                  <p className="text-white">
                    {frame.metadata.gps[0].toFixed(6)}, {frame.metadata.gps[1].toFixed(6)}
                  </p>
                </div>
              )}

              {frame.metadata.reasoning && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-1">Reasoning</h4>
                  <p className="text-white text-sm">{frame.metadata.reasoning}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

