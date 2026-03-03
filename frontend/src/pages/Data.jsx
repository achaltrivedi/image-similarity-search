import { useState, useEffect, useCallback } from 'react';
import { Loader2, Eye, Download, ChevronLeft, ChevronRight, Database } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { fetchGallery } from '@/api/searchService';

const statusVariants = {
  Done: 'default',
  Processing: 'secondary',
  Error: 'destructive',
};

const PAGE_SIZE = 50;

function Data() {
  const [items, setItems] = useState([]);
  const [pending, setPending] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadPage = useCallback(async (pageNum) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchGallery(pageNum, PAGE_SIZE);
      setItems(data.items || []);
      setPending(data.pending || []);
      setTotal(data.total || 0);
      setHasMore(data.has_more || false);
      setPage(pageNum);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadPage(1);
  }, [loadPage]);

  // Connect to WebSocket for real-time updates
  useEffect(() => {
    // Determine standard/secure protocol based on current page
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/gallery`;

    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);

        // Ignore thumbnail-related events
        if (payload.object_key?.startsWith('.thumbnails/')) return;

        if (payload.event_type === 'processing') {
          // Phase 1: New upload detected — show "Processing" spinner immediately
          setPending(prev => {
            // Avoid duplicate entries
            if (prev.some(p => p.object_key === payload.object_key)) return prev;
            return [payload, ...prev];
          });
        }

        if (payload.event_type === 'new_item') {
          // Phase 2: Worker finished — flip from Processing → Done
          // 1. Remove from pending
          setPending(prev => prev.filter(p => p.object_key !== payload.object_key));

          // 2. Prepend to items list only if we are on the first page
          setItems(prev => {
            // Avoid duplicates
            if (prev.some(item => item.object_key === payload.object_key)) {
              return prev;
            }
            if (page === 1) {
              return [payload, ...prev].slice(0, PAGE_SIZE);
            }
            return prev;
          });

          // 3. Increment total count
          setTotal(prev => prev + 1);
        }
      } catch (err) {
        console.error("Failed to parse websocket message", err);
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    return () => {
      ws.close();
    };
  }, [page]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Merge pending (at top) + indexed items for display
  const allRows = [...pending, ...items];

  return (
    <div className="container mx-auto px-4 py-16">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Data Management</h1>
          <p className="text-muted-foreground mt-2">
            Review and manage the indexed assets in your system.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="text-sm px-3 py-1">
            <Database className="w-3.5 h-3.5 mr-1.5" />
            {total} indexed
          </Badge>
          {pending.length > 0 && (
            <Badge variant="secondary" className="text-sm px-3 py-1 animate-pulse">
              <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
              {pending.length} processing
            </Badge>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-md bg-destructive/10 text-destructive text-sm">
          {error}
        </div>
      )}

      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16">ID</TableHead>
              <TableHead className="w-16">Preview</TableHead>
              <TableHead>Filename</TableHead>
              <TableHead className="w-20">Type</TableHead>
              <TableHead className="w-24">Size</TableHead>
              <TableHead className="w-28">Status</TableHead>
              <TableHead className="w-40">Indexed Date</TableHead>
              <TableHead className="text-right w-28">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && allRows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-muted-foreground" />
                  <span className="text-muted-foreground">Loading...</span>
                </TableCell>
              </TableRow>
            ) : allRows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                  No indexed assets found. Upload images to MinIO and run a sync.
                </TableCell>
              </TableRow>
            ) : (
              allRows.map((item, index) => (
                <TableRow
                  key={item.id ?? `pending-${index}`}
                  className={item.status === 'Processing' ? 'bg-muted/30' : ''}
                >
                  <TableCell className="font-medium font-mono text-xs text-muted-foreground">
                    {item.id ?? '—'}
                  </TableCell>
                  <TableCell>
                    <div className="relative w-10 h-10 rounded overflow-hidden bg-muted flex items-center justify-center">
                      {item.status === 'Processing' ? (
                        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                      ) : item.thumbnail_url ? (
                        <img
                          src={item.thumbnail_url}
                          alt={item.filename}
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            e.target.style.display = 'none';
                          }}
                        />
                      ) : (
                        <span className="text-[10px] text-muted-foreground">N/A</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm truncate block max-w-xs" title={item.object_key}>
                      {item.filename}
                    </span>
                    {item.object_key !== item.filename && (
                      <span className="text-xs text-muted-foreground truncate block max-w-xs" title={item.object_key}>
                        {item.object_key}
                      </span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-xs font-mono">
                      {item.type}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm">{item.size}</TableCell>
                  <TableCell>
                    <Badge variant={statusVariants[item.status] || 'outline'}>
                      {item.status === 'Processing' && (
                        <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                      )}
                      {item.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {item.indexed_date}
                  </TableCell>
                  <TableCell className="text-right">
                    {item.status === 'Done' && (
                      <div className="flex items-center justify-end gap-1">
                        {item.image_url && (
                          <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
                            <a href={item.image_url} target="_blank" rel="noopener noreferrer" title="View">
                              <Eye className="h-4 w-4" />
                            </a>
                          </Button>
                        )}
                        {item.download_url && (
                          <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
                            <a href={item.download_url} title="Download">
                              <Download className="h-4 w-4" />
                            </a>
                          </Button>
                        )}
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages} ({total} total)
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1 || loading}
              onClick={() => loadPage(page - 1)}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!hasMore || loading}
              onClick={() => loadPage(page + 1)}
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export default Data;
