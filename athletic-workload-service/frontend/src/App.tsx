
import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import {
  BrowserRouter,
  Navigate,
  Outlet,
  Route,
  Routes,
} from "react-router-dom";

import { Box, Spinner, Center } from "@chakra-ui/react";

import { supabase } from "./lib/supabase";
import Navbar from "./components/Navbar";
import Login from "./pages/Login";
import Upload from "./pages/Upload";
import OverallStatistics from "./pages/OverallStatistics";
import WorkoutDetails from "./pages/WorkoutDetails";
import WorkloadTrends from "./pages/WorkloadTrends";

function Layout() {
  return (
    <Box minH="100vh" bg="#0b1220" color="white">
      <Navbar />
      <Box as="main" maxW="1280px" mx="auto" px={{ base: 4, md: 8 }} py={8}>
        <Outlet />
      </Box>
    </Box>
  );
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (mounted) {
        setSession(data.session);
        setLoading(false);
      }
    });

    const { data: { subscription } } =
      supabase.auth.onAuthStateChange((_event, nextSession) => {
        if (mounted) {
          setSession(nextSession);
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  if (loading) {
    return (
      <Center minH="100vh" bg="#0b1220">
        <Spinner color="blue.400" size="xl" />
      </Center>
    );
  }

  return (
    <BrowserRouter>
      {session ? (
        <Routes>
          <Route element={<Layout />}>
            <Route path="/upload" element={<Upload />} />
            <Route path="/statistics" element={<OverallStatistics />} />
            <Route path="/workouts/:workoutId" element={<WorkoutDetails />} />
            <Route path="/trends" element={<WorkloadTrends />} />
          </Route>
          <Route path="*" element={<Navigate to="/statistics" replace />} />
        </Routes>
      ) : (
        <Routes>
          <Route path="*" element={<Login />} />
        </Routes>
      )}
    </BrowserRouter>
  );
}
