import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { getLeaderboard, type Leaderboard } from "../api";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

function ChartCard({ title, labels, values, label }: { title: string; labels: string[]; values: number[]; label: string }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      <Bar
        data={{ labels, datasets: [{ label, data: values, backgroundColor: "#0f6b4d" }] }}
        options={{ responsive: true, plugins: { legend: { display: false } } }}
      />
    </div>
  );
}

export default function LeaderboardPage() {
  const [stats, setStats] = useState<Leaderboard | null>(null);

  useEffect(() => {
    getLeaderboard().then(setStats).catch(() => {});
  }, []);

  if (!stats) return <p>Loading...</p>;

  const wins = stats.win_leaderboard as Array<{ player: string; wins: number }>;
  const totals = stats.total_points as Array<{ player: string; total_points: number }>;
  const lost = stats.lost_challenges_or_skipped_turns as Array<{ player: string; count: number }>;

  return (
    <div>
      <div className="card">
        <h1>Scrabble Leaderboard</h1>
        <Link to="/">← Home</Link>
      </div>
      <ChartCard title="Wins" labels={wins.map((r) => r.player)} values={wins.map((r) => r.wins)} label="Wins" />
      <ChartCard title="Total points" labels={totals.map((r) => r.player)} values={totals.map((r) => Number(r.total_points))} label="Points" />
      <ChartCard title="Lost challenges or skipped turns" labels={lost.map((r) => r.player)} values={lost.map((r) => r.count)} label="Count" />
      <div className="card">
        <h3>Games played</h3>
        <table>
          <thead><tr><th>Player</th><th>Games</th></tr></thead>
          <tbody>
            {(stats.games_played as Array<{ player: string; games_played: number }>).map((r) => (
              <tr key={r.player}><td>{r.player}</td><td>{r.games_played}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
