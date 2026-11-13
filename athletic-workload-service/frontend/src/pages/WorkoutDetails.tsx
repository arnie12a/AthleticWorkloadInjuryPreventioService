
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Box,
  Heading,
  Text,
  SimpleGrid,
  Stack,
  HStack,
} from "@chakra-ui/react";
import { ArrowLeft, HeartPulse, Mountain, Clock3, MapPinned } from "lucide-react";

import { apiRequest } from "../lib/api";
import RouteMap from "../components/RouteMap";

type Workout = {
  id: string;
  filename: string;
  sport: string | null;
  start_time: string | null;
  duration_seconds: number | null;
  distance_meters: number | null;
  avg_heart_rate: number | null;
  max_heart_rate: number | null;
  total_ascent: number | null;
  training_load: number | null;
};

type RecordPoint = {
  timestamp: string | null;
  heart_rate: number | null;
  altitude: number | null;
  speed: number | null;
  latitude: number | null;
  longitude: number | null;
};

export default function WorkoutDetails() {
  const { workoutId } = useParams<{ workoutId: string }>();
  const [workout, setWorkout] = useState<Workout | null>(null);
  const [records, setRecords] = useState<RecordPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!workoutId) return;

    let active = true;

    Promise.all([
      apiRequest(`/workouts/${workoutId}`),
      apiRequest(`/workouts/${workoutId}/records`),
    ])
      .then(([w, r]) => {
        if (active) {
          setWorkout(w);
          setRecords(r.records);
        }
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
  }, [workoutId]);

  if (loading) return <Text>Loading workout...</Text>;
  if (error) return <Text color="red.400">{error}</Text>;
  if (!workout) return <Text>Workout not found.</Text>;

  const stats = [
    {
      label: "Distance",
      value: workout.distance_meters != null
        ? `${(workout.distance_meters / 1000).toFixed(2)} km`
        : "N/A",
      icon: MapPinned,
    },
    {
      label: "Duration",
      value: workout.duration_seconds != null
        ? `${Math.round(workout.duration_seconds / 60)} min`
        : "N/A",
      icon: Clock3,
    },
    {
      label: "Average HR",
      value: workout.avg_heart_rate != null
        ? `${workout.avg_heart_rate} BPM`
        : "N/A",
      icon: HeartPulse,
    },
    {
      label: "Training Load",
      value: workout.training_load != null
        ? `${workout.training_load.toFixed(1)} AU`
        : "N/A",
      icon: Mountain,
    },
  ];

  return (
    <Stack gap={7}>
      <Link to="/statistics">
        <HStack color="#38bdf8" gap={2}>
          <ArrowLeft size={17} />
          <Text fontSize="sm">Back to workouts</Text>
        </HStack>
      </Link>

      <Box>
        <Heading size="2xl" textTransform="capitalize">
          {workout.sport ?? "Activity"}
        </Heading>
        <Text color="#94a3b8" mt={2}>{workout.filename}</Text>
      </Box>

      <SimpleGrid columns={{ base: 1, md: 4 }} gap={4}>
        {stats.map(({ label, value, icon: Icon }) => (
          <Box
            key={label}
            bg="#152033"
            border="1px solid #29394f"
            borderRadius="xl"
            p={5}
          >
            <HStack color="#94a3b8" mb={3}>
              <Icon size={17} />
              <Text fontSize="sm">{label}</Text>
            </HStack>
            <Heading size="lg">{value}</Heading>
          </Box>
        ))}
      </SimpleGrid>

      <Box
        bg="#152033"
        border="1px solid #29394f"
        borderRadius="2xl"
        overflow="hidden"
      >
        <Box p={5}>
          <Heading size="md">GPS Activity Route</Heading>
          <Text fontSize="sm" color="#94a3b8" mt={1}>
            Recorded route from your Garmin FIT file
          </Text>
        </Box>
        <RouteMap records={records} />
      </Box>

      <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
        <Box bg="#152033" p={6} borderRadius="xl">
          <Heading size="md" mb={3}>Heart Rate</Heading>
          <Text>Average: {workout.avg_heart_rate ?? "N/A"} BPM</Text>
          <Text mt={2}>Maximum: {workout.max_heart_rate ?? "N/A"} BPM</Text>
        </Box>

        <Box bg="#152033" p={6} borderRadius="xl">
          <Heading size="md" mb={3}>Elevation Gain</Heading>
          <Heading size="xl">
            {workout.total_ascent != null
              ? `${workout.total_ascent} m`
              : "N/A"}
          </Heading>
        </Box>
      </SimpleGrid>
    </Stack>
  );
}
