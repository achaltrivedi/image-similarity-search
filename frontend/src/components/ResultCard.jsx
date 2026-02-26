import {
  Eye,
  Download,
  Ruler,
  Palette,
  Layers,
  Folder,
  HardDrive,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardFooter } from '@/components/ui/card';

const SCORE_CONFIG = [
  {
    key: 'design',
    label: 'Design',
    icon: <Ruler className='w-3.5 h-3.5 md:w-4 md:h-4' />,
    color: 'emerald',
  },
  {
    key: 'color',
    label: 'Color',
    icon: <Palette className='w-3.5 h-3.5 md:w-4 md:h-4' />,
    color: 'blue',
  },
  {
    key: 'texture',
    label: 'Texture',
    icon: <Layers className='w-3.5 h-3.5 md:w-4 md:h-4' />,
    color: 'purple',
  },
];

const BAR_COLORS = {
  emerald: 'bg-emerald-500',
  blue: 'bg-blue-500',
  purple: 'bg-purple-500',
};

const LABEL_COLORS = {
  emerald: 'text-emerald-600 dark:text-emerald-400',
  blue: 'text-blue-600 dark:text-blue-400',
  purple: 'text-purple-600 dark:text-purple-400',
};

export default function ResultCard({ result, rank }) {
  const filename = result.image_key?.split('/').pop() || 'Unknown';
  const similarity = (result.similarity * 100).toFixed(1);
  const scores = result.similarity_scores || {};

  const formatBytes = (bytes) => {
    if (!bytes) return 'Unknown Size';
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <Card className='overflow-hidden p-0'>
      {/* Image Container */}
      <div className='relative aspect-square bg-muted'>
        <img
          src={result.thumbnail_url || result.image_url}
          alt={filename}
          className='w-full h-full object-cover'
          onError={(e) => {
            e.target.style.display = 'none';
            e.target.parentElement.classList.add(
              'flex',
              'items-center',
              'justify-center',
            );
            const placeholder = document.createElement('span');
            placeholder.className = 'text-gray-400 text-sm';
            placeholder.textContent = 'No Preview';
            e.target.parentElement.appendChild(placeholder);
          }}
        />

        {/* Rank Badge */}
        <Badge
          variant='secondary'
          className='absolute top-2 left-2 bg-white/90 backdrop-blur text-gray-900 font-semibold'
        >
          #{rank}
        </Badge>

        {/* Overall Similarity Badge */}
        <Badge className='absolute top-2 right-2 bg-blue-600 text-white font-semibold'>
          {similarity}% Match
        </Badge>
      </div>

      <CardContent className='p-4'>
        {/* Filename */}
        <h3
          className='font-medium text-foreground text-sm mb-1 truncate'
          title={filename}
        >
          {filename}
        </h3>

        {/* S3 Path & File Size */}
        <div className='flex flex-col gap-1 mb-3'>
          <p
            className='flex items-center gap-1.5 text-xs text-muted-foreground truncate'
            title={result.image_key}
          >
            <Folder className='shrink-0 w-3.5 h-3.5' /> {result.image_key}
          </p>
          <p className='flex items-center gap-1.5 text-xs text-muted-foreground'>
            <HardDrive className='shrink-0 w-3.5 h-3.5' />{' '}
            {formatBytes(result.file_size)}
          </p>
        </div>

        {/* Individual Similarity Scores */}
        <div className='space-y-1.5 mb-3'>
          {SCORE_CONFIG.map(({ key, label, icon, color }) => {
            const score = scores[key];
            if (score == null) return null;
            const pct = (score * 100).toFixed(0);
            return (
              <div key={key} className='flex items-center gap-2'>
                <span
                  className={`flex items-center gap-1.5 text-xs w-18 ${LABEL_COLORS[color]} font-medium`}
                >
                  {icon}
                  <span>{label}</span>
                </span>
                <div className='flex-1 bg-muted rounded-full h-1.5'>
                  <div
                    className={`h-1.5 rounded-full ${BAR_COLORS[color]} transition-all duration-300`}
                    style={{ width: `${Math.min(100, pct)}%` }}
                  />
                </div>
                <span className='text-xs text-muted-foreground w-8 text-right font-mono'>
                  {pct}%
                </span>
              </div>
            );
          })}
        </div>
      </CardContent>
      {/* Action Buttons */}
      <CardFooter className='px-4 pb-4 pt-0 flex gap-2'>
        {result.image_url && (
          <Button variant='outline' size='sm' asChild className='flex-1'>
            <a
              href={result.image_url}
              target='_blank'
              rel='noopener noreferrer'
            >
              <Eye className='mr-2 h-4 w-4' />
              View
            </a>
          </Button>
        )}
        {result.download_url && (
          <Button variant='outline' size='sm' asChild className='flex-1'>
            <a href={result.download_url}>
              <Download className='mr-2 h-4 w-4' />
              Download
            </a>
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
