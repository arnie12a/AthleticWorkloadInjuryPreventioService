
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
  } from "recharts";
  
  type Workout = {
    id: string;
    start_time: string | null;
    training_load: number | null;
  };
  
  type Props = {
    workouts: Workout[];
  };
  
  export default function TrainingLoadChart({ workouts }: Props) {
    const dailyLoad = new Map<string, number>();
  
    for (const workout of workouts) {
      if (!workout.start_time || workout.training_load == null) {
        continue;
      }
  
      // Group by calendar date.
      const date = workout.start_time.slice(0, 10);
  
      dailyLoad.set(
        date,
        (dailyLoad.get(date) ?? 0) + workout.training_load
      );
    }
  
    const data = Array.from(dailyLoad.entries())
      .map(([date, load]) => ({
        date,
        load: Number(load.toFixed(2)),
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  
    return (
      <section className="summary-card">
        <h2>Daily Training Load</h2>
        <p>Heart-rate-based workload (AU)</p>
  
        {data.length === 0 ? (
          <p>No training-load data available yet.</p>
        ) : (
          <div style={{ width: "100%", height: 320 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#334155"
                />
                <XAxis
                  dataKey="date"
                  stroke="#94a3b8"
                />
                <YAxis stroke="#94a3b8" />
                <Tooltip
                  contentStyle={{
                    background: "#152033",
                    border: "1px solid #34435a",
                    color: "#e8edf5",
                  }}
                />
                <Bar
                  dataKey="load"
                  fill="#38bdf8"
                  name="Training Load"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>
    );
  }
  