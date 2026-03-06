import { useState, useEffect, useCallback } from 'react';
import { Loader2, Eye, Download, ChevronLeft, ChevronRight, Database, Trash2, X, Search } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { fetchGallery, deleteGalleryItems } from '@/api/searchService';
import { toast } from 'sonner';

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

  // Search state
  const [searchInput, setSearchInput] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');

  // Multi-select state
  const [selected, setSelected] = useState(new Set());
  const [deleting, setDeleting] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(searchInput), 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const loadPage = useCallback(async (pageNum, query = debouncedQuery) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchGallery(pageNum, PAGE_SIZE, query);
      setItems(data.items || []);
      setPending(data.pending || []);
      setTotal(data.total || 0);
      setHasMore(data.has_more || false);
      setPage(pageNum);
      setSelected(new Set()); // Clear selection on page change or new search
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [debouncedQuery]);

  // Load new data when debounced search changes or initial load
  useEffect(() => {
    loadPage(1);
  }, [loadPage]);

  // Connect to WebSocket for real-time updates
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/gallery`;

    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);

        // Ignore thumbnail-related events
        if (payload.object_key?.startsWith('.thumbnails/')) return;

        if (payload.event_type === 'processing') {
          setPending(prev => {
            if (prev.some(p => p.object_key === payload.object_key)) return prev;
            return [payload, ...prev];
          });
        }

        if (payload.event_type === 'new_item') {
          setPending(prev => prev.filter(p => p.object_key !== payload.object_key));
          setItems(prev => {
            if (prev.some(item => item.object_key === payload.object_key)) return prev;
            if (page === 1) return [payload, ...prev].slice(0, PAGE_SIZE);
            return prev;
          });
          setTotal(prev => prev + 1);
        }

        if (payload.event_type === 'deleted_item') {
          setItems(prev => prev.filter(item => item.object_key !== payload.object_key));
          setPending(prev => prev.filter(p => p.object_key !== payload.object_key));
          setSelected(prev => {
            const next = new Set(prev);
            next.delete(payload.object_key);
            return next;
          });
          setTotal(prev => Math.max(0, prev - 1));
        }
      } catch (err) {
        console.error("Failed to parse websocket message", err);
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    return () => ws.close();
  }, [page]);

  // Selection helpers
  const toggleSelect = (objectKey) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(objectKey)) next.delete(objectKey);
      else next.add(objectKey);
      return next;
    });
  };

  const selectableDoneItems = items.filter(i => i.status === 'Done');
  const allSelected = selectableDoneItems.length > 0 && selectableDoneItems.every(i => selected.has(i.object_key));

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelected(new Set());
    } else {
      setSelected(new Set(selectableDoneItems.map(i => i.object_key)));
    }
  };

  const handleDelete = async () => {
    setShowConfirm(false);
    setDeleting(true);
    try {
      const keys = Array.from(selected);
      const result = await deleteGalleryItems(keys);
      toast.success(`Deleted ${result.deleted} item${result.deleted !== 1 ? 's' : ''} from bucket`);
      if (result.failed > 0) {
        toast.error(`Failed to delete ${result.failed} item(s)`);
      }
      setSelected(new Set());
      // The WebSocket deleted_item events will handle removing rows from UI
    } catch (err) {
      toast.error(`Deletion failed: ${err.message}`);
    } finally {
      setDeleting(false);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);
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
          <div className="relative border-r border-border pr-3 mr-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search by path or filename (e.g. .ai)"
              className="pl-9 w-[300px] h-9"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
          </div>
          <Badge variant="outline" className="text-sm px-3 py-1">
            <Database className="w-3.5 h-3.5 mr-1.5" />
            {total} matching
          </Badge>
          {pending.length > 0 && (
            <Badge variant="secondary" className="text-sm px-3 py-1 animate-pulse">
              <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
              {pending.length} processing
            </Badge>
          )}
        </div>
      </div>

      {/* Selection Action Bar */}
      {selected.size > 0 && (
        <div className="mb-4 flex items-center justify-between rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3">
          <div className="flex items-center gap-3">
            <Badge variant="destructive" className="text-sm px-3 py-1">
              {selected.size} selected
            </Badge>
            <span className="text-sm text-muted-foreground">
              {selected.size === 1 ? '1 asset' : `${selected.size} assets`} selected for deletion
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelected(new Set())}
            >
              <X className="h-4 w-4 mr-1" />
              Clear
            </Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={deleting}
              onClick={() => setShowConfirm(true)}
            >
              {deleting ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4 mr-1" />
              )}
              Delete Selected
            </Button>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog (inline) */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-lg border bg-card p-6 shadow-lg">
            <h3 className="text-lg font-semibold mb-2">Confirm Deletion</h3>
            <p className="text-sm text-muted-foreground mb-1">
              You are about to permanently delete <strong>{selected.size}</strong> asset{selected.size !== 1 ? 's' : ''} from the MinIO bucket.
            </p>
            <p className="text-sm text-destructive mb-4">
              This action cannot be undone. The files, thumbnails, and database records will be removed.
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowConfirm(false)}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleDelete}>
                <Trash2 className="h-4 w-4 mr-1" />
                Delete {selected.size} asset{selected.size !== 1 ? 's' : ''}
              </Button>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="mb-6 p-4 rounded-md bg-destructive/10 text-destructive text-sm">
          {error}
        </div>
      )}

      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-border accent-primary cursor-pointer"
                  checked={allSelected}
                  onChange={toggleSelectAll}
                  title="Select all"
                />
              </TableHead>
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
                <TableCell colSpan={9} className="text-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-muted-foreground" />
                  <span className="text-muted-foreground">Loading...</span>
                </TableCell>
              </TableRow>
            ) : allRows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-12 text-muted-foreground">
                  No indexed assets found. Upload images to MinIO and run a sync.
                </TableCell>
              </TableRow>
            ) : (
              allRows.map((item, index) => {
                const isSelected = selected.has(item.object_key);
                const isSelectable = item.status === 'Done';
                return (
                  <TableRow
                    key={item.id ?? `pending-${index}`}
                    className={`${item.status === 'Processing' ? 'bg-muted/30' : ''} ${isSelected ? 'bg-destructive/5' : ''}`}
                  >
                    <TableCell>
                      {isSelectable ? (
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-border accent-primary cursor-pointer"
                          checked={isSelected}
                          onChange={() => toggleSelect(item.object_key)}
                        />
                      ) : (
                        <span className="block w-4" />
                      )}
                    </TableCell>
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
                );
              })
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
