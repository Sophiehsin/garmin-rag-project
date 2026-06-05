import QuerySection from "./components/QuerySection";

export default function Home() {
  return (
    <main className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold mb-2">Garmin Insight</h1>
      <p className="text-gray-500 mb-8">
        Ask anything about your fitness data — training trends, sleep quality, personal records.
      </p>
      <QuerySection />
    </main>
  );
}
