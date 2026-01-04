import { useQuery } from 'react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

export default function CollectionList() {
  const { data: collections, isLoading, error } = useQuery(
    'collections',
    () => api.listCollections(),
    {
      refetchOnWindowFocus: false,
    }
  )

  if (isLoading) {
    return (
      <div className="px-4 py-6 sm:px-0">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-400">Loading collections...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-4 py-6 sm:px-0">
        <div className="bg-red-900/20 border border-red-500 rounded-lg p-6">
          <p className="text-red-400">
            Error loading collections: {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">Collections</h1>
        <p className="text-gray-400">
          View and manage your saved search result collections.
        </p>
      </div>

      {!collections || collections.length === 0 ? (
        <div className="bg-gray-800 rounded-lg p-6 text-center">
          <p className="text-gray-400">No collections yet. Save search results to create a collection.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {collections.map((collection) => (
            <Link
              key={collection.id}
              to={`/collections/${collection.id}`}
              className="bg-gray-800 rounded-lg p-6 hover:ring-2 hover:ring-blue-500 transition-all"
            >
              <h3 className="text-lg font-semibold text-white mb-2">{collection.name}</h3>
              <p className="text-sm text-gray-400 mb-4 line-clamp-2">Query: "{collection.query}"</p>
              <div className="flex justify-between items-center text-sm">
                <span className="text-gray-400">{collection.total_results} results</span>
                <span className="text-gray-500">
                  {new Date(collection.created_at).toLocaleDateString()}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

