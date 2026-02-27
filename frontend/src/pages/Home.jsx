// React
import { useState } from 'react';

// Third-party
import InfiniteScroll from 'react-infinite-scroll-component';
import { AlertCircleIcon, RefreshCw } from 'lucide-react';

// UI components
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';

// App components
import ResultsGrid from '@/components/ResultsGrid';
import SearchBox from '@/components/SearchBox';

// API
import { searchImage, searchNextPage, syncBucket } from '@/api/searchService';

function Home() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [queryId, setQueryId] = useState(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [totalResults, setTotalResults] = useState(0);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState(null);

  const handleSearch = async (file) => {
    setLoading(true);
    setError(null);
    setResults([]);
    setPage(1);
    setQueryId(null);
    setHasMore(false);
    setTotalResults(0);

    try {
      const data = await searchImage(file);
      setResults(data.results || []);
      setQueryId(data.query_id);
      setPage(2); // Next page to load
      setHasMore(data.has_more || false);
      setTotalResults(data.total_results || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadMore = async () => {
    if (!queryId || !hasMore) return;

    try {
      const data = await searchNextPage(queryId, page);
      setResults((prev) => [...prev, ...data.results]);
      setPage((prev) => prev + 1);
      setHasMore(data.has_more || false);
    } catch (err) {
      console.error('Failed to load more results:', err);
      setError(err.message);
    }
  };

  const handleSync = async () => {
    setIsSyncing(true);
    setSyncMessage('Starting sync...');
    try {
      const data = await syncBucket();
      if (data.status === 'already_running') {
        setSyncMessage('A sync is already in progress.');
      } else {
        setSyncMessage('Background sync started successfully! Images will be index momentarily.');
      }
    } catch (err) {
      console.error('Failed to sync bucket:', err);
      setSyncMessage(`Sync failed: ${err.message}`);
    } finally {
      setIsSyncing(false);
      // Clear message after 5 seconds
      setTimeout(() => setSyncMessage(null), 5000);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Action Bar (above Search Box) */}
      <div className="flex justify-end mb-4">
        <div className="flex items-center gap-3">
          {syncMessage && (
            <span className="text-sm text-primary bg-primary/10 px-3 py-1.5 rounded-full animate-in fade-in transition-all shadow-sm border border-primary/20">
              {syncMessage}
            </span>
          )}
          <Button variant="outline" size="sm" onClick={handleSync} disabled={isSyncing}>
            <RefreshCw
              className={`w-4 h-4 ${isSyncing ? 'animate-spin text-primary' : 'text-muted-foreground'}`}
            />
            {isSyncing ? 'Syncing...' : 'Sync Bucket'}
          </Button>
        </div>
      </div>

      {/* Search Box */}
      <div className="mb-8">
        <SearchBox onSearch={handleSearch} loading={loading} />
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-12 gap-3">
          <Spinner className="size-10" />
          <p className="text-sm text-muted-foreground font-medium">Processing...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Results */}
      {!loading && results.length > 0 && (
        <div>
          {/* Results Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-semibold text-foreground">Search Results</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Showing {results.length} of {totalResults} results
              </p>
            </div>
          </div>

          {/* Infinite Scroll Grid */}
          <InfiniteScroll
            dataLength={results.length}
            next={loadMore}
            hasMore={hasMore}
            loader={
              <div className="flex justify-center py-8">
                <Spinner className="size-8" />
              </div>
            }
            endMessage={
              <div className="text-center py-8">
                <p className="text-muted-foreground text-sm">All results displayed</p>
              </div>
            }
          >
            <ResultsGrid results={results} />
          </InfiniteScroll>
        </div>
      )}

      {/* Empty State */}
      {!loading && results.length === 0 && !error && queryId && (
        <div className="text-center py-16 bg-card rounded-xl border border-border shadow-sm">
          <div className="mx-auto w-16 h-16 mb-4 flex items-center justify-center rounded-full bg-muted">
            <svg
              className="w-8 h-8 text-muted-foreground"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-foreground mb-2">No similar images found</h3>
          <p className="text-muted-foreground text-sm">Try uploading a different image</p>
        </div>
      )}
    </div>
  );
}

export default Home;
