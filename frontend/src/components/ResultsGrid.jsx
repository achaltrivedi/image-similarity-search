import ResultCard from './ResultCard';

export default function ResultsGrid({ results }) {
  return (
    <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'>
      {results.map((result, index) => (
        <ResultCard
          key={result.image_key ?? index}
          result={result}
          rank={index + 1}
        />
      ))}
    </div>
  );
}
