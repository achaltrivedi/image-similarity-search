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

const statusVariants = {
  Done: 'default',
  Processing: 'secondary',
  Hold: 'outline',
  Error: 'destructive',
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
            {dummyData.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="font-medium">{item.id}</TableCell>
                <TableCell>{item.name}</TableCell>
                <TableCell>{item.type}</TableCell>
                <TableCell>{item.size}</TableCell>
                <TableCell>
                  <Badge variant={statusVariants[item.status]}>{item.status}</Badge>
                </TableCell>
                <TableCell className="text-right text-muted-foreground">{item.date}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

export default Data;
