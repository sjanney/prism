import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import ResultsGrid from './ResultsGrid'
import type { SearchStatusResponse } from '../types'

interface SearchStatusProps {
  jobId: string
  searchQuery: string
}

export default function SearchStatus({ jobId, searchQuery }: SearchStatusProps) {
  const [polling, setPolling] = useState(true)
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [collectionName, setCollectionName] = useState('')
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const saveCollectionMutation = useMutation({
    mutationFn: (name: string) => {
      if (!data?.results) throw new Error('No results to save')
      const resultIds = data.results
        .map(r => r.frame_id)
        .filter((id): id is number => id !== undefined)
      
      const avgConfidence = data.results.reduce((sum, r) => sum + r.confidence, 0) / data.results.length
      
      return api.createCollection({
        name,
        query: searchQuery,
        result_ids: resultIds,
        metadata: {
          avg_confidence: avgConfidence,
          total_results: data.results.length,
          query: searchQuery,
        },
      })
    },
    onSuccess: (collection) => {
      queryClient.invalidateQueries('collections')
      setShowSaveModal(false)
      setCollectionName('')
      navigate(`/collections/${collection.id}`)
    },
  })

  const { data, isLoading, error } = useQuery<SearchStatusResponse>(
    ['searchStatus', jobId],
    () => api.getSearchStatus(jobId),
    {
      enabled: polling,
      refetchInterval: (query) => {
        const data = query.state.data as SearchStatusResponse | undefined
        // Stop polling if job is complete or failed
        if (data?.status === 'complete' || data?.status === 'failed') {
          setPolling(false)
          return false
        }
        return 2000 // Poll every 2 seconds
      },
    }
  )

  useEffect(() => {
    if (data?.status === 'complete' || data?.status === 'failed') {
      setPolling(false)
    }
  }, [data?.status])

  if (isLoading && !data) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
        <p className="mt-4 text-gray-400">Initializing search...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-500 rounded-lg p-6">
        <p className="text-red-400">Error: {error instanceof Error ? error.message : 'Unknown error'}</p>
      </div>
    )
  }

  if (!data) {
    return null
  }

  if (data.status === 'failed') {
    const isNoDataError = data.error?.includes('No frames found in database')
    return (
      <div className="bg-red-900/20 border border-red-500 rounded-lg p-6">
        <p className="text-red-400 font-semibold mb-2">Search Failed</p>
        <p className="text-gray-400 mb-3">{data.error || 'Unknown error occurred'}</p>
        {isNoDataError && (
          <div className="bg-gray-800 rounded-lg p-3 mt-3">
            <p className="text-sm text-gray-300 mb-2">To fix this:</p>
            <ol className="list-decimal list-inside space-y-1 text-sm text-gray-400">
              <li>Download and extract a dataset (e.g., nuScenes mini)</li>
              <li>Run: <code className="bg-gray-700 px-1 rounded">python -m cli.main ingest --path data/nuscenes</code></li>
            </ol>
          </div>
        )}
      </div>
    )
  }

  if (data.status === 'processing') {
    const progress = data.progress
    const percent = progress
      ? Math.round((progress.frames_processed / progress.frames_total) * 100)
      : 0

    return (
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-400 mb-2">
            <span>Processing...</span>
            <span>{percent}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${percent}%` }}
            ></div>
          </div>
        </div>
        {progress && (
          <div className="text-sm text-gray-400">
            <p>Frames processed: {progress.frames_processed} / {progress.frames_total}</p>
            <p>Matches found so far: {progress.matches_found}</p>
          </div>
        )}
      </div>
    )
  }

  if (data.status === 'complete' && data.results) {
    return (
      <div>
        <div className="bg-gray-800 rounded-lg p-4 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <p className="text-lg font-semibold text-white">
                Found {data.results.length} matches
              </p>
              {data.progress && (
                <p className="text-sm text-gray-400">
                  Searched {data.progress.frames_total} frames
                </p>
              )}
            </div>
            <button
              onClick={() => setShowSaveModal(true)}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md transition-colors font-medium"
            >
              Save Collection
            </button>
          </div>
        </div>
        <ResultsGrid results={data.results} />
        
        {showSaveModal && (
          <div className="fixed inset-0 bg-black/75 flex items-center justify-center z-50 p-4" onClick={() => setShowSaveModal(false)}>
            <div
              className="bg-gray-800 rounded-lg p-6 max-w-md w-full"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-xl font-semibold text-white mb-4">Save Collection</h3>
              <div className="mb-4">
                <label htmlFor="collectionName" className="block text-sm font-medium text-gray-300 mb-2">
                  Collection Name
                </label>
                <input
                  type="text"
                  id="collectionName"
                  value={collectionName}
                  onChange={(e) => setCollectionName(e.target.value)}
                  placeholder="e.g., Night Pedestrians, Construction Zones"
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  autoFocus
                />
                <p className="text-xs text-gray-400 mt-2">
                  This will save {data.results.length} results as a collection
                </p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowSaveModal(false)
                    setCollectionName('')
                  }}
                  className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    if (collectionName.trim()) {
                      saveCollectionMutation.mutate(collectionName.trim())
                    }
                  }}
                  disabled={!collectionName.trim() || saveCollectionMutation.isLoading}
                  className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-md transition-colors"
                >
                  {saveCollectionMutation.isLoading ? 'Saving...' : 'Save'}
                </button>
              </div>
              {saveCollectionMutation.isError && (
                <p className="mt-3 text-sm text-red-400">
                  {saveCollectionMutation.error instanceof Error
                    ? saveCollectionMutation.error.message
                    : 'Failed to save collection'}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    )
  }

  return null
}

