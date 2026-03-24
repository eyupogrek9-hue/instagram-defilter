import { useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL

interface Result {
  original_url: string
  processed_image: string
  claude_pass_applied: boolean
  is_carousel: boolean
}

export default function App() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Result | null>(null)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    setError('')

    try {
      const res = await fetch(`${API_URL}/defilter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail ?? 'Something went wrong')
      } else {
        setResult(data)
      }
    } catch {
      setError('Could not reach the server')
    } finally {
      setLoading(false)
    }
  }

  function handleDownload() {
    if (!result) return
    const link = document.createElement('a')
    link.href = `data:image/png;base64,${result.processed_image}`
    link.download = 'defiltered.png'
    link.click()
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-start p-8">
      <div className="w-full max-w-2xl">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Instagram De-Filter</h1>
        <p className="text-gray-500 mb-6 text-sm">Paste an Instagram post URL to remove the filter.</p>

        <form onSubmit={handleSubmit} className="flex gap-2 mb-4">
          <input
            type="url"
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="https://www.instagram.com/p/..."
            required
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Processing…' : 'De-filter'}
          </button>
        </form>

        {error && (
          <p className="text-red-600 text-sm mb-4">{error}</p>
        )}

        {result && (
          <div>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Original</p>
                <img src={result.original_url} alt="Original" className="w-full rounded-lg" />
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase mb-1">De-filtered</p>
                <img
                  src={`data:image/png;base64,${result.processed_image}`}
                  alt="De-filtered"
                  className="w-full rounded-lg"
                />
              </div>
            </div>
            {result.is_carousel && (
              <p className="text-xs text-amber-600 mb-2">Only the first image was processed (carousel post)</p>
            )}
            <div className="flex items-center justify-between">
              <p className="text-xs text-gray-400">
                {result.claude_pass_applied ? '✓ Claude corrections applied' : 'Classical corrections only'}
              </p>
              <button
                onClick={handleDownload}
                className="text-sm text-blue-600 hover:underline font-medium"
              >
                Download de-filtered image
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
