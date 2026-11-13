
import { useEffect, useState } from "react";
import {
  Box,
  Heading,
  Text,
  SimpleGrid,
  Stack,
} from "@chakra-ui/react";
import { apiRequest } from "../lib/api";
import TrainingLoadChart from "../components/TrainingLoadChart";

type Workout = {
  id: string;
  start_time: string | null;
  training_load: number | null;
};

type Trends = {
  acute_7_day_load: number;
  chronic_weekly_average: number;
  acwr: number | null;
};

export default function WorkloadTrends() {
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [trends, setTrends] = useState<Trends | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiRequest("/workouts"),
      apiRequest("/analytics/trends"),
    ])
      .then(([workoutData, trendData]) => {
        setWorkouts(workoutData.workouts);
        setTrends(trendData);
      })
      .catch((err) => setError(err.message));
  }, []);

  return (
    <Stack gap={8}>
      <Box>
        <Heading size="2xl">Workload Trends</Heading>
        <Text color="#94a3b8" mt={2}>
          Understand how your training load changes over time.
        </Text>
      </Box>

      {error && <Text color="red.400">{error}</Text>}

      {trends && (
        <SimpleGrid columns={{ base: 1, md: 3 }} gap={4}>
          {[
            {
              label: "Last 7 Days",
              value: `${trends.acute_7_day_load.toFixed(1)} AU`,
            },
            {
              label: "Previous 28-Day Weekly Average",
              value: `${trends.chronic_weekly_average.toFixed(1)} AU`,
            },
            {
              label: "Workload Ratio",
              value: trends.acwr?.toFixed(2) ?? "N/A",
            },
          ].map((metric) => (
            <Box
              key={metric.label}
              bg="#152033"
              border="1px solid #29394f"
              borderRadius="xl"
              p={6}
            >
              <Text color="#94a3b8" fontSize="sm" mb={3}>
                {metric.label}
              </Text>
              <Heading size="2xl">{metric.value}</Heading>
            </Box>
          ))}
        </SimpleGrid>
      )}

      <Box bg="#152033" borderRadius="2xl" p={6}>
        <TrainingLoadChart workouts={workouts} />
      </Box>

      <Text fontSize="sm" color="#94a3b8">
        Workload metrics describe training patterns and should not
        be interpreted as direct predictions of injury risk.
      </Text>
    </Stack>
  );
}
