import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import SearchPage from './components/SearchPage'
import CollectionList from './components/CollectionList'
import CollectionDetail from './components/CollectionDetail'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-900">
        <nav className="bg-gray-800 border-b border-gray-700">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <Link to="/" className="text-xl font-bold text-white">
                    EdgeVLM
                  </Link>
                </div>
                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                  <Link
                    to="/"
                    className="border-transparent text-gray-300 hover:border-gray-300 hover:text-white inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                  >
                    Search
                  </Link>
                  <Link
                    to="/collections"
                    className="border-transparent text-gray-300 hover:border-gray-300 hover:text-white inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                  >
                    Collections
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<SearchPage />} />
            <Route path="/collections" element={<CollectionList />} />
            <Route path="/collections/:id" element={<CollectionDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App

