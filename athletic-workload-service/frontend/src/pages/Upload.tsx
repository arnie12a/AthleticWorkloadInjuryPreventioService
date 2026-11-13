
import { useEffect, useRef, useState } from "react";
import {
  Box,
  Button,
  Heading,
  Text,
  Stack,
  Input,
  Badge,
  HStack,
} from "@chakra-ui/react";
import { UploadCloud, CheckCircle2 } from "lucide-react";
import { apiRequest } from "../lib/api";

type Job = {
  job_id: string;
  filename: string;
  status: "pending" | "processing" | "completed" | "failed";
  error_message: string | null;
  workout_id: string | null;
};

type Props = {
  onComplete?: () => void;
};

export default function Upload({ onComplete }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, []);

  function stopPolling() {
    if (timer.current) {
      clearInterval(timer.current);
      timer.current = null;
    }
  }

  async function upload() {
    if (!file) return;

    stopPolling();
    setLoading(true);
    setError("");
    setJob(null);

    const form = new FormData();
    form.append("file", file);

    try {
      const response = await apiRequest("/workouts/upload-async", {
        method: "POST",
        body: form,
      });

      setJob({
        job_id: response.job_id,
        filename: file.name,
        status: "pending",
        error_message: null,
        workout_id: null,
      });

      timer.current = setInterval(async () => {
        try {
          const result: Job = await apiRequest(
            `/jobs/${response.job_id}`
          );

          setJob(result);

          if (result.status === "completed" || result.status === "failed") {
            stopPolling();
            setLoading(false);
            if (result.status === "completed") onComplete?.();
          }
        } catch (err) {
          stopPolling();
          setLoading(false);
          setError(err instanceof Error ? err.message : "Status check failed");
        }
      }, 2000);
    } catch (err) {
      setLoading(false);
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  }

  return (
    <Stack gap={6}>
      <Box>
        <Heading size="2xl">Upload Activity</Heading>
        <Text color="#94a3b8" mt={2}>
          Upload Garmin FIT files to analyze your training.
        </Text>
      </Box>

      <Box
        bg="#152033"
        border="1px solid #29394f"
        borderRadius="2xl"
        p={8}
        maxW="750px"
      >
        <Stack gap={5}>
          <HStack gap={3}>
            <UploadCloud color="#38bdf8" size={26} />
            <Heading size="md">Garmin FIT Upload</Heading>
          </HStack>

          <Text color="#94a3b8">
            Your file will be processed asynchronously by the background worker.
          </Text>

          <Input
            type="file"
            accept=".fit"
            p={2}
            disabled={loading}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />

          <Button
            colorPalette="blue"
            alignSelf="flex-start"
            disabled={!file || loading}
            onClick={upload}
          >
            {loading ? "Processing..." : "Upload FIT File"}
          </Button>

          {job && (
            <Box bg="#0b1220" p={5} borderRadius="xl">
              <HStack justify="space-between" mb={3}>
                <Text fontWeight="medium">{job.filename}</Text>
                <Badge
                  colorPalette={
                    job.status === "completed"
                      ? "green"
                      : job.status === "failed"
                      ? "red"
                      : "blue"
                  }
                >
                  {job.status}
                </Badge>
              </HStack>

              {job.status === "completed" && (
                <HStack color="green.400">
                  <CheckCircle2 size={18} />
                  <Text>Workout processed successfully.</Text>
                </HStack>
              )}

              {job.status === "failed" && (
                <Text color="red.400">
                  {job.error_message ?? "Processing failed"}
                </Text>
              )}
            </Box>
          )}

          {error && <Text color="red.400">{error}</Text>}
        </Stack>
      </Box>
    </Stack>
  );
}
