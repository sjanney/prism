import { useParams } from 'react-router-dom'
import { useQuery } from 'react-query'
import { api } from '../api/client'
import ResultsGrid from './ResultsGrid'

export default function CollectionDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: collection, isLoading, error } = useQuery(
    ['collection', id],
    () => api.getCollection(id!),
    {
      enabled: !!id,
    }
  )

  const handleExport = async (format: 'csv' | 'json') => {
    if (!id) return

    try {
      const blob = await api.exportCollection(id, format)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${collection?.name || 'collection'}_export.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      alert(`Export failed: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  if (isLoading) {
    return (
      <div className="px-4 py-6 sm:px-0">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-400">Loading collection...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-4 py-6 sm:px-0">
        <div className="bg-red-900/20 border border-red-500 rounded-lg p-6">
          <p className="text-red-400">
            Error loading collection: {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      </div>
    )
  }

  if (!collection) {
    return (
      <div className="px-4 py-6 sm:px-0">
        <div className="bg-gray-800 rounded-lg p-6 text-center">
          <p className="text-gray-400">Collection not found</p>
        </div>
      </div>
    )
  }

  // Convert collection to results format for ResultsGrid
  // Note: This is a simplified version - in production, you'd fetch full frame data
  const results = collection.result_ids.map((frameId) => ({
    frame_id: frameId,
    confidence: collection.metadata?.avg_confidence || 0,
    metadata: {},
  }))

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">{collection.name}</h1>
        <p className="text-gray-400 mb-4">Query: "{collection.query}"</p>

        <div className="bg-gray-800 rounded-lg p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <p className="text-sm text-gray-400">Total Results</p>
              <p className="text-2xl font-semibold text-white">{collection.result_ids.length}</p>
            </div>
            {collection.metadata?.avg_confidence && (
              <div>
                <p className="text-sm text-gray-400">Avg Confidence</p>
                <p className="text-2xl font-semibold text-white">
                  {collection.metadata.avg_confidence.toFixed(1)}%
                </p>
              </div>
            )}
            <div>
              <p className="text-sm text-gray-400">Created</p>
              <p className="text-lg text-white">
                {new Date(collection.created_at).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Statistics */}
          {(collection.metadata?.weather_distribution || 
            collection.metadata?.camera_distribution || 
            collection.metadata?.date_range) && (
            <div className="border-t border-gray-700 pt-4 mt-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Statistics</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {collection.metadata?.weather_distribution && (
                  <div>
                    <p className="text-xs text-gray-400 mb-2">Weather Distribution</p>
                    <div className="space-y-1">
                      {Object.entries(collection.metadata.weather_distribution as Record<string, number>).map(([weather, count]) => (
                        <div key={weather} className="flex justify-between text-sm">
                          <span className="text-gray-300 capitalize">{weather}</span>
                          <span className="text-gray-400">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {collection.metadata?.camera_distribution && (
                  <div>
                    <p className="text-xs text-gray-400 mb-2">Camera Distribution</p>
                    <div className="space-y-1">
                      {Object.entries(collection.metadata.camera_distribution as Record<string, number>).map(([camera, count]) => (
                        <div key={camera} className="flex justify-between text-sm">
                          <span className="text-gray-300">{camera}</span>
                          <span className="text-gray-400">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {collection.metadata?.date_range && (
                  <div>
                    <p className="text-xs text-gray-400 mb-2">Date Range</p>
                    <div className="space-y-1 text-sm text-gray-300">
                      <div>
                        <span className="text-gray-400">Start: </span>
                        {new Date((collection.metadata.date_range as { start: string }).start).toLocaleString()}
                      </div>
                      <div>
                        <span className="text-gray-400">End: </span>
                        {new Date((collection.metadata.date_range as { end: string }).end).toLocaleString()}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-4 mb-6">
          <button
            onClick={() => handleExport('csv')}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
          >
            Export CSV
          </button>
          <button
            onClick={() => handleExport('json')}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
          >
            Export JSON
          </button>
        </div>
      </div>

      <ResultsGrid results={results as any} />
    </div>
  )
}

