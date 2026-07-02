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
import { getLeaderboard, type Leaderboard, type LeaderboardScope } from "../api";
import { getChartPalette, useTheme } from "../theme/ThemeContext";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const SCOPES: { value: LeaderboardScope; label: string }[] = [
  { value: "all", label: "All players" },
  { value: "friends", label: "Friends" },
  { value: "manual", label: "Manual only" },
];

function ChartCard({ title, labels, values, label }: { title: string; labels: string[]; values: number[]; label: string }) {
  const { resolvedTheme } = useTheme();
  const palette = getChartPalette();

  if (labels.length === 0) {
    return (
      <div className="card chart-card">
        <h3>{title}</h3>
        <p className="muted">No data for this filter.</p>
      </div>
    );
  }

  return (
    <div className="card chart-card">
      <h3>{title}</h3>
      <Bar
        key={resolvedTheme}
        data={{
          labels,
          datasets: [{
            label,
            data: values,
            backgroundColor: labels.map((_, i) => palette[i % palette.length]),
            borderRadius: 8,
          }],
        }}
        options={{
          responsive: true,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true } },
        }}
      />
    </div>
  );
}

export default function LeaderboardPage() {
  const [scope, setScope] = useState<LeaderboardScope>("all");
  const [stats, setStats] = useState<Leaderboard | null>(null);

  useEffect(() => {
    getLeaderboard(scope).then(setStats).catch(() => {});
  }, [scope]);

  if (!stats) return <p className="loading-state">Loading...</p>;

  const wins = stats.win_leaderboard as Array<{ player: string; wins: number }>;
  const totals = stats.total_points as Array<{ player: string; total_points: number }>;
  const lost = stats.lost_challenges_or_skipped_turns as Array<{ player: string; count: number }>;

  return (
    <div>
      <div className="card">
        <h1 className="page-title">Scrabble Leaderboard</h1>
        <Link to="/" className="back-link muted">← Home</Link>
        <div className="segmented" role="tablist" aria-label="Leaderboard scope">
          {SCOPES.map((s) => (
            <button
              key={s.value}
              type="button"
              className={`segmented__btn${scope === s.value ? " segmented__btn--active" : ""}`}
              onClick={() => setScope(s.value)}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>
      <div className="grid-2">
        <ChartCard title="Wins" labels={wins.map((r) => r.player)} values={wins.map((r) => r.wins)} label="Wins" />
        <ChartCard title="Total points" labels={totals.map((r) => r.player)} values={totals.map((r) => Number(r.total_points))} label="Points" />
      </div>
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
