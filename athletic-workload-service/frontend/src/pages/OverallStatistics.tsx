
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Box,
  Heading,
  Text,
  SimpleGrid,
  Stack,
  HStack,
} from "@chakra-ui/react";
import { Activity, MapPinned, Clock3, ChevronRight } from "lucide-react";
import { apiRequest } from "../lib/api";

type Workout = {
  id: string;
  filename: string;
  sport: string | null;
  start_time: string | null;
  duration_seconds: number | null;
  distance_meters: number | null;
  training_load: number | null;
};

export default function OverallStatistics() {
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    apiRequest("/workouts")
      .then((result) => {
        if (active) setWorkouts(result.workouts);
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const distance = workouts.reduce(
    (sum, w) => sum + (w.distance_meters ?? 0), 0
  ) / 1000;

  const duration = workouts.reduce(
    (sum, w) => sum + (w.duration_seconds ?? 0), 0
  ) / 3600;

  const stats = [
    { label: "Total Workouts", value: workouts.length, icon: Activity },
    { label: "Total Distance", value: `${distance.toFixed(1)} km`, icon: MapPinned },
    { label: "Total Duration", value: `${duration.toFixed(1)} hrs`, icon: Clock3 },
  ];

  return (
    <Stack gap={8}>
      <Box>
        <Heading size="2xl">Overall Statistics</Heading>
        <Text color="#94a3b8" mt={2}>
          Your Garmin activity history and training statistics.
        </Text>
      </Box>

      <SimpleGrid columns={{ base: 1, md: 3 }} gap={4}>
        {stats.map(({ label, value, icon: Icon }) => (
          <Box
            key={label}
            bg="#152033"
            border="1px solid #29394f"
            borderRadius="2xl"
            p={6}
          >
            <HStack color="#94a3b8" gap={2} mb={4}>
              <Icon size={18} />
              <Text fontSize="sm">{label}</Text>
            </HStack>
            <Heading size="2xl">{value}</Heading>
          </Box>
        ))}
      </SimpleGrid>

      <Heading size="lg">All Workouts</Heading>

      {loading && <Text>Loading workouts...</Text>}
      {error && <Text color="red.400">{error}</Text>}

      <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={4}>
        {workouts.map((workout) => (
          <Link key={workout.id} to={`/workouts/${workout.id}`}>
            <Box
              bg="#152033"
              border="1px solid #29394f"
              borderRadius="xl"
              p={5}
              height="100%"
              transition="all 0.2s"
              _hover={{
                borderColor: "#38bdf8",
                transform: "translateY(-3px)",
              }}
            >
              <HStack justify="space-between" mb={3}>
                <Heading size="md" textTransform="capitalize">
                  {workout.sport ?? "Activity"}
                </Heading>
                <ChevronRight size={18} color="#94a3b8" />
              </HStack>

              <Text fontSize="sm" color="#94a3b8" mb={4}>
                {workout.filename}
              </Text>

              <Stack gap={2} fontSize="sm">
                <Text>
                  Date: {workout.start_time?.slice(0, 10) ?? "N/A"}
                </Text>
                <Text>
                  Distance:{" "}
                  {workout.distance_meters != null
                    ? `${(workout.distance_meters / 1000).toFixed(2)} km`
                    : "N/A"}
                </Text>
                <Text>
                  Training Load:{" "}
                  {workout.training_load != null
                    ? `${workout.training_load.toFixed(1)} AU`
                    : "Not calculated"}
                </Text>
              </Stack>
            </Box>
          </Link>
        ))}
      </SimpleGrid>
    </Stack>
  );
}
