import { useState } from 'react'
import { useMutation, useQueryClient, useQuery } from 'react-query'
import { api } from '../api/client'
import type { SearchRequest } from '../types'
import ResultsGrid from './ResultsGrid'
import SearchStatus from './SearchStatus'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [confidenceThreshold, setConfidenceThreshold] = useState(25)
  const [maxResults, setMaxResults] = useState(50)
  const [jobId, setJobId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  // Check if database has data
  const { data: stats } = useQuery('stats', () => api.getStats(), {
    refetchOnWindowFocus: false,
  })

  const searchMutation = useMutation({
    mutationFn: (request: SearchRequest) => api.createSearch(request),
    onSuccess: (data) => {
      setJobId(data.job_id)
    },
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    searchMutation.mutate({
      query: query.trim(),
      max_results: maxResults,
      confidence_threshold: confidenceThreshold,
    })
  }

  const handleNewSearch = () => {
    setJobId(null)
    setQuery('')
  }

  // Show empty state if no data
  if (stats && !stats.has_data) {
    return (
      <div className="px-4 py-6 sm:px-0">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-white mb-2">Semantic Search</h1>
          <p className="text-gray-400">
            Search your autonomous vehicle dataset using natural language queries powered by CLIP.
          </p>
        </div>

        <div className="bg-yellow-900/20 border border-yellow-500 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-yellow-400 mb-2">No Data Found</h3>
          <p className="text-gray-300 mb-4">
            Your database doesn't have any frames indexed yet. You need to ingest a dataset first.
          </p>
          <div className="bg-gray-800 rounded-lg p-4 mb-4">
            <p className="text-sm text-gray-300 font-medium mb-2">To get started:</p>
            <ol className="list-decimal list-inside space-y-2 text-sm text-gray-400">
              <li>Download the nuScenes mini dataset (see <a href="https://www.nuscenes.org/download" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">nuScenes website</a>)</li>
              <li>Extract it to <code className="bg-gray-700 px-1 rounded">data/nuscenes/</code></li>
              <li>Run: <code className="bg-gray-700 px-1 rounded">python -m cli.main ingest --path data/nuscenes</code></li>
            </ol>
          </div>
          <p className="text-xs text-gray-500">
            See <a href="/QUICKSTART.md" className="text-blue-400 hover:underline">QUICKSTART.md</a> for detailed instructions.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">Semantic Search</h1>
        <p className="text-gray-400">
          Search your autonomous vehicle dataset using natural language queries powered by CLIP.
        </p>
        {stats && stats.has_data && (
          <p className="text-sm text-gray-500 mt-2">
            {stats.total_frames} frames indexed • {stats.total_collections} collections
          </p>
        )}
      </div>

      {!jobId ? (
        <form onSubmit={handleSearch} className="bg-gray-800 rounded-lg p-6 mb-6">
          <div className="mb-4">
            <label htmlFor="query" className="block text-sm font-medium text-gray-300 mb-2">
              Search Query
            </label>
            <input
              type="text"
              id="query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., pedestrians at night, construction vehicles, emergency vehicles"
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label htmlFor="confidence" className="block text-sm font-medium text-gray-300 mb-2">
                Minimum Confidence: {confidenceThreshold}%
              </label>
              <input
                type="range"
                id="confidence"
                min="0"
                max="100"
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                className="w-full"
              />
            </div>

            <div>
              <label htmlFor="maxResults" className="block text-sm font-medium text-gray-300 mb-2">
                Max Results
              </label>
              <input
                type="number"
                id="maxResults"
                min="1"
                max="200"
                value={maxResults}
                onChange={(e) => setMaxResults(Number(e.target.value))}
                className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={searchMutation.isLoading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-medium py-2 px-4 rounded-md transition-colors"
          >
            {searchMutation.isLoading ? 'Starting Search...' : 'Search'}
          </button>
        </form>
      ) : (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-white">Search Results</h2>
              <p className="text-sm text-gray-400">Query: "{query}"</p>
            </div>
            <button
              onClick={handleNewSearch}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md transition-colors"
            >
              New Search
            </button>
          </div>

          <SearchStatus jobId={jobId} searchQuery={query} />
        </div>
      )}
    </div>
  )
}

