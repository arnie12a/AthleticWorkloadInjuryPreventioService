
import { useEffect, useState } from "react";
import { supabase } from "../lib/supabase";
import { apiRequest } from "../lib/api";
import Upload from "./Upload";
import TrainingLoadChart from "../components/TrainingLoadChart";

type Workout = {
  id: string;
  filename: string;
  sport: string | null;
  start_time: string | null;
  duration_seconds: number | null;
  distance_meters: number | null;
  avg_heart_rate: number | null;
  training_load: number | null;
};

export default function Dashboard() {
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  // Refresh workouts after a FIT file finishes processing
  async function refreshWorkouts() {
    setRefreshing(true);
    setError("");

    try {
      const result = await apiRequest("/workouts");
      setWorkouts(result.workouts);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to refresh workouts"
      );
    } finally {
      setRefreshing(false);
    }
  }

  // Load existing workouts when the dashboard opens
  useEffect(() => {
    let active = true;

    async function loadWorkouts() {
      try {
        const result = await apiRequest("/workouts");

        if (active) {
          setWorkouts(result.workouts);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load workouts"
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadWorkouts();

    return () => {
      active = false;
    };
  }, []);

  async function logout() {
    const { error } = await supabase.auth.signOut();

    if (error) {
      setError(error.message);
    }
  }

  // Calculate summary statistics
  const totalWorkouts = workouts.length;

  const totalDistance = workouts.reduce(
    (sum, workout) =>
      sum + (workout.distance_meters ?? 0),
    0
  ) / 1000;

  const totalDuration = workouts.reduce(
    (sum, workout) =>
      sum + (workout.duration_seconds ?? 0),
    0
  ) / 3600;

  const totalTrainingLoad = workouts.reduce(
    (sum, workout) =>
      sum + (workout.training_load ?? 0),
    0
  );

  return (
    <div className="dashboard">

      {/* Header */}
      <header className="dashboard-header">
        <div>
          <h1>Athletic Workload</h1>
          <p>Your training history and workload analytics</p>
        </div>

        <button onClick={logout}>
          Log out
        </button>
      </header>

      <main>

        {/* Summary Statistics */}
        <section className="summary-grid">

          <div className="summary-card">
            <h3>Total Workouts</h3>
            <div className="metric">
              {totalWorkouts}
            </div>
          </div>

          <div className="summary-card">
            <h3>Total Distance</h3>
            <div className="metric">
              {totalDistance.toFixed(1)} km
            </div>
          </div>

          <div className="summary-card">
            <h3>Total Duration</h3>
            <div className="metric">
              {totalDuration.toFixed(1)} hrs
            </div>
          </div>

          <div className="summary-card">
            <h3>Total Training Load</h3>
            <div className="metric">
              {totalTrainingLoad.toFixed(1)}
            </div>
          </div>

        </section>

        <TrainingLoadChart workouts={workouts} />

        <Upload onComplete={refreshWorkouts} />

        

        {/* Workout History */}
        <section className="workouts-section">

          <div className="section-header">
            <h2>Recent Activities</h2>

            <button
              onClick={refreshWorkouts}
              disabled={refreshing}
            >
              {refreshing ? "Refreshing..." : "Refresh"}
            </button>
          </div>

          {loading && (
            <p>Loading workouts...</p>
          )}

          {error && (
            <p role="alert">{error}</p>
          )}

          {!loading && !error && workouts.length === 0 && (
            <p>
              No workouts yet. Upload a Garmin FIT file to begin.
            </p>
          )}

          <div className="workout-grid">

            {workouts.map((workout) => (
              <article
                className="workout-card"
                key={workout.id}
              >

                <h3>
                  {workout.sport ?? "Activity"}
                </h3>

                <p className="workout-filename">
                  {workout.filename}
                </p>

                <p>
                  Date:{" "}
                  {workout.start_time
                    ? new Date(
                        workout.start_time
                      ).toLocaleDateString()
                    : "N/A"}
                </p>

                <p>
                  Duration:{" "}
                  {workout.duration_seconds != null
                    ? `${Math.round(
                        workout.duration_seconds / 60
                      )} min`
                    : "N/A"}
                </p>

                <p>
                  Distance:{" "}
                  {workout.distance_meters != null
                    ? `${(
                        workout.distance_meters / 1000
                      ).toFixed(2)} km`
                    : "N/A"}
                </p>

                <p>
                  Average HR:{" "}
                  {workout.avg_heart_rate != null
                    ? `${workout.avg_heart_rate} BPM`
                    : "N/A"}
                </p>

                <p>
                  Training Load:{" "}
                  {workout.training_load != null
                    ? `${workout.training_load.toFixed(1)} AU`
                    : "Not calculated"}
                </p>

              </article>
            ))}

          </div>
        </section>

      </main>
    </div>
  );
}
