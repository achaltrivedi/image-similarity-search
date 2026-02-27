import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { CheckCircle2, RefreshCw, Clock, AlertCircle } from 'lucide-react';

const dummyData = [
  {
    id: 'IMG-001',
    name: 'Modern Architecture',
    size: '2.4 MB',
    type: 'PNG',
    date: '2024-02-28',
    status: 'Done',
  },
  {
    id: 'IMG-002',
    name: 'Abstract Pattern',
    size: '1.1 MB',
    type: 'JPEG',
    date: '2024-02-27',
    status: 'Processing',
  },
  {
    id: 'IMG-003',
    name: 'Product Catalog v2',
    size: '15.6 MB',
    type: 'PDF',
    date: '2024-02-26',
    status: 'Done',
  },
  {
    id: 'IMG-004',
    name: 'Logo Concepts',
    size: '4.2 MB',
    type: 'AI',
    date: '2024-02-25',
    status: 'Hold',
  },
  {
    id: 'IMG-005',
    name: 'Main Banner',
    size: '8.9 MB',
    type: 'WebP',
    date: '2024-02-24',
    status: 'Done',
  },
  {
    id: 'IMG-006',
    name: 'Texture Pack 01',
    size: '5.3 MB',
    type: 'TIFF',
    date: '2024-02-23',
    status: 'Error',
  },
  {
    id: 'IMG-007',
    name: 'Background Gradient',
    size: '0.8 MB',
    type: 'PNG',
    date: '2024-02-22',
    status: 'Done',
  },
  {
    id: 'IMG-008',
    name: 'User Interface Mockup',
    size: '12.1 MB',
    type: 'PDF',
    date: '2024-02-21',
    status: 'Processing',
  },
  {
    id: 'IMG-009',
    name: 'App Icon set',
    size: '2.2 MB',
    type: 'PNG',
    date: '2024-02-20',
    status: 'Done',
  },
  {
    id: 'IMG-010',
    name: 'Social Media Post',
    size: '3.5 MB',
    type: 'JPEG',
    date: '2024-02-19',
    status: 'Done',
  },
];

const statusConfig = {
  Done: {
    class:
      'bg-green-50 text-green-700 border-green-200 dark:bg-green-950/30 dark:text-green-300 dark:border-green-800',
    icon: CheckCircle2,
  },
  Processing: {
    class:
      'bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950/30 dark:text-sky-300 dark:border-sky-800',
    icon: RefreshCw,
    iconClass: 'animate-spin',
  },
  Hold: {
    class:
      'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/30 dark:text-purple-300 dark:border-purple-800',
    icon: Clock,
  },
  Error: {
    class:
      'bg-red-50 text-red-700 border-red-200 dark:bg-red-950/30 dark:text-red-300 dark:border-red-800',
    icon: AlertCircle,
  },
};

function Data() {
  return (
    <div className="container mx-auto px-4 py-16">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Data Management</h1>
        <p className="text-muted-foreground mt-2">
          Review and manage the indexed assets in your system.
        </p>
      </div>

      <div className="rounded-md border bg-card">
        <Table>
          <TableCaption>A list of recently indexed image assets.</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead className="w-25">ID</TableHead>
              <TableHead>Filename</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Size</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Indexed Date</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {dummyData.map((item) => {
              const config = statusConfig[item.status];
              const Icon = config.icon;

              return (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{item.id}</TableCell>
                  <TableCell>{item.name}</TableCell>
                  <TableCell>{item.type}</TableCell>
                  <TableCell>{item.size}</TableCell>
                  <TableCell>
                    <Badge className={`gap-1 ${config.class}`}>
                      <Icon
                        data-icon="inline-start"
                        className={`w-3 h-3 ${config.iconClass || ''}`}
                      />
                      {item.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">{item.date}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

export default Data;
