import { useId } from 'react';
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

function buildScannerGeometry(points) {
  if (!Array.isArray(points) || points.length < 3) {
    return null;
  }

  const normalizedPoints = points
    .map((point) => ({
      x: Number(point?.x),
      y: Number(point?.y),
    }))
    .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y))
    .map((point) => ({
      x: Math.min(1, Math.max(0, point.x)),
      y: Math.min(1, Math.max(0, point.y)),
    }));

  if (normalizedPoints.length < 3) {
    return null;
  }

  const svgPoints = normalizedPoints.map((point) => ({
    x: point.x * 100,
    y: point.y * 100,
  }));

  const pointString = svgPoints
    .map((point) => `${point.x.toFixed(2)},${point.y.toFixed(2)}`)
    .join(' ');
  const polygonPath =
    svgPoints
      .map((point, index) =>
        `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`,
      )
      .join(' ') + ' Z';

  const xs = svgPoints.map((point) => point.x);
  const ys = svgPoints.map((point) => point.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const width = Math.max(6, maxX - minX);
  const height = Math.max(6, maxY - minY);
  const perimeter = svgPoints.reduce((total, point, index) => {
    const nextPoint = svgPoints[(index + 1) % svgPoints.length];
    return total + Math.hypot(nextPoint.x - point.x, nextPoint.y - point.y);
  }, 0);

  return {
    pointString,
    polygonPath,
    overlayPath: `M 0 0 H 100 V 100 H 0 Z ${polygonPath}`,
    minX,
    maxX,
    minY,
    maxY,
    width,
    height,
    perimeter,
    svgPoints,
  };
}

export default function ResultCard({
  result,
  rank,
  boundingBoxEffect = 'scanner',
}) {
  const svgIdBase = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const filename = result.image_key?.split('/').pop() || 'Unknown';
  const similarity = (result.similarity * 100).toFixed(1);
  const scores = result.similarity_scores || {};
  const scannerGeometry = buildScannerGeometry(result.bounding_box);
  const hasBoundingBox = Boolean(scannerGeometry) && boundingBoxEffect !== 'off';
  const showScanner = hasBoundingBox && boundingBoxEffect === 'scanner';
  const showSimpleHighlight = hasBoundingBox && boundingBoxEffect === 'simple';

  const clipId = `${svgIdBase}-clip`;
  const glowId = `${svgIdBase}-glow`;
  const blurId = `${svgIdBase}-blur`;
  const scanGradientId = `${svgIdBase}-scan`;
  const focusGradientId = `${svgIdBase}-focus`;

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
      <div className='relative aspect-square overflow-hidden bg-muted'>
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

        {/* Sub-Part Bounding Box Overlay */}
        {showSimpleHighlight && (
          <svg
            className='absolute inset-0 h-full w-full pointer-events-none'
            viewBox='0 0 100 100'
            preserveAspectRatio='none'
            style={{ zIndex: 10 }}
          >
            <polygon
              points={scannerGeometry.pointString}
              fill='rgba(56, 189, 248, 0.16)'
              stroke='rgba(125, 211, 252, 0.95)'
              strokeWidth='2.4'
              vectorEffect='non-scaling-stroke'
            />
          </svg>
        )}

        {showScanner && (
          <svg
            className='absolute inset-0 h-full w-full pointer-events-none'
            viewBox='0 0 100 100'
            preserveAspectRatio='none'
            style={{ zIndex: 10 }}
          >
            <defs>
              <clipPath id={clipId}>
                <polygon points={scannerGeometry.pointString} />
              </clipPath>
              <filter id={glowId} x='-40%' y='-40%' width='180%' height='180%'>
                <feGaussianBlur stdDeviation='1.6' result='blur' />
                <feColorMatrix
                  in='blur'
                  type='matrix'
                  values='1 0 0 0 0.22 0 1 0 0 0.58 0 0 1 0 0.98 0 0 0 1 0'
                />
              </filter>
              <filter id={blurId} x='-15%' y='-15%' width='130%' height='130%'>
                <feGaussianBlur stdDeviation='1.1' />
              </filter>
              <linearGradient id={scanGradientId} x1='0' y1='0' x2='0' y2='1'>
                <stop offset='0%' stopColor='rgba(56, 189, 248, 0)' />
                <stop offset='38%' stopColor='rgba(96, 165, 250, 0.18)' />
                <stop offset='70%' stopColor='rgba(125, 211, 252, 0.42)' />
                <stop offset='100%' stopColor='rgba(191, 219, 254, 0)' />
              </linearGradient>
              <radialGradient id={focusGradientId} cx='50%' cy='50%' r='65%'>
                <stop offset='0%' stopColor='rgba(255, 255, 255, 0.16)' />
                <stop offset='55%' stopColor='rgba(96, 165, 250, 0.12)' />
                <stop offset='100%' stopColor='rgba(14, 165, 233, 0.02)' />
              </radialGradient>
            </defs>

            <path
              d={scannerGeometry.overlayPath}
              fill='rgba(2, 8, 23, 0.54)'
              fillRule='evenodd'
            >
              <animate
                attributeName='opacity'
                values='0;0.54'
                dur='380ms'
                fill='freeze'
              />
            </path>

            <path
              d={scannerGeometry.overlayPath}
              fill='rgba(15, 23, 42, 0.22)'
              fillRule='evenodd'
              filter={`url(#${blurId})`}
            >
              <animate
                attributeName='opacity'
                values='0;0.22'
                dur='580ms'
                fill='freeze'
              />
            </path>

            <polygon
              points={scannerGeometry.pointString}
              fill={`url(#${focusGradientId})`}
              opacity='0'
            >
              <animate
                attributeName='opacity'
                values='0;0.9'
                dur='650ms'
                begin='150ms'
                fill='freeze'
              />
            </polygon>

            <polygon
              points={scannerGeometry.pointString}
              fill='none'
              stroke='rgba(125, 211, 252, 0.95)'
              strokeWidth='5'
              filter={`url(#${glowId})`}
              opacity='0'
              vectorEffect="non-scaling-stroke"
            >
              <animate
                attributeName='opacity'
                values='0;0.8;0.55;0.8'
                dur='3.2s'
                begin='350ms'
                repeatCount='indefinite'
              />
            </polygon>

            <polygon
              points={scannerGeometry.pointString}
              fill='rgba(56, 189, 248, 0.08)'
              stroke='rgb(125, 211, 252)'
              strokeWidth='2.25'
              vectorEffect='non-scaling-stroke'
              strokeDasharray={scannerGeometry.perimeter.toFixed(2)}
              strokeDashoffset={scannerGeometry.perimeter.toFixed(2)}
            >
              <animate
                attributeName='stroke-dashoffset'
                from={scannerGeometry.perimeter.toFixed(2)}
                to='0'
                dur='900ms'
                fill='freeze'
              />
              <animate
                attributeName='opacity'
                values='0;1'
                dur='250ms'
                fill='freeze'
              />
            </polygon>

            <g clipPath={`url(#${clipId})`}>
              <rect
                x={(scannerGeometry.minX - scannerGeometry.width * 0.2).toFixed(2)}
                y={(scannerGeometry.minY - Math.max(18, scannerGeometry.height * 0.8)).toFixed(2)}
                width={Math.max(24, scannerGeometry.width * 1.4).toFixed(2)}
                height={Math.max(18, scannerGeometry.height * 0.8).toFixed(2)}
                fill={`url(#${scanGradientId})`}
                opacity='0'
              >
                <animate
                  attributeName='opacity'
                  values='0;0.95;0.95'
                  dur='400ms'
                  begin='350ms'
                  fill='freeze'
                />
                <animate
                  attributeName='y'
                  values={[
                    (scannerGeometry.minY - Math.max(18, scannerGeometry.height * 0.8)).toFixed(2),
                    (scannerGeometry.maxY + 2).toFixed(2),
                    (scannerGeometry.minY - Math.max(18, scannerGeometry.height * 0.8)).toFixed(2),
                  ].join(';')}
                  dur='3s'
                  begin='700ms'
                  repeatCount='indefinite'
                />
              </rect>

              <line
                x1={(scannerGeometry.minX - 2).toFixed(2)}
                x2={(scannerGeometry.maxX + 2).toFixed(2)}
                y1={scannerGeometry.minY.toFixed(2)}
                y2={scannerGeometry.minY.toFixed(2)}
                stroke='rgba(224, 242, 254, 0.95)'
                strokeWidth='1.2'
                opacity='0'
                vectorEffect='non-scaling-stroke'
              >
                <animate
                  attributeName='opacity'
                  values='0;1;1'
                  dur='400ms'
                  begin='500ms'
                  fill='freeze'
                />
                <animate
                  attributeName='y1'
                  values={[
                    scannerGeometry.minY.toFixed(2),
                    scannerGeometry.maxY.toFixed(2),
                    scannerGeometry.minY.toFixed(2),
                  ].join(';')}
                  dur='3s'
                  begin='700ms'
                  repeatCount='indefinite'
                />
                <animate
                  attributeName='y2'
                  values={[
                    scannerGeometry.minY.toFixed(2),
                    scannerGeometry.maxY.toFixed(2),
                    scannerGeometry.minY.toFixed(2),
                  ].join(';')}
                  dur='3s'
                  begin='700ms'
                  repeatCount='indefinite'
                />
              </line>
            </g>

            {scannerGeometry.svgPoints.map((point, index) => (
              <circle
                key={index}
                cx={point.x.toFixed(2)}
                cy={point.y.toFixed(2)}
                r='1.25'
                fill='white'
                opacity='0'
                vectorEffect="non-scaling-stroke"
              >
                <animate
                  attributeName='opacity'
                  values='0;1;0.7;1'
                  dur='2.6s'
                  begin={`${0.15 + index * 0.08}s`}
                  repeatCount='indefinite'
                />
                <animate
                  attributeName='r'
                  values='0.65;1.45;1.1;1.45'
                  dur='2.6s'
                  begin={`${0.15 + index * 0.08}s`}
                  repeatCount='indefinite'
                />
              </circle>
            ))}
          </svg>
        )}

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
