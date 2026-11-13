
import { useState } from "react";
import type { FormEvent } from "react";

import {
  Box,
  Button,
  Field,
  Input,
  Stack,
  Text,
  Heading,
  Center,
  HStack,
} from "@chakra-ui/react";

import { Activity, Mail, Lock } from "lucide-react";
import { supabase } from "../lib/supabase";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSignup, setIsSignup] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [isError, setIsError] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();

    setLoading(true);
    setMessage("");
    setIsError(false);

    try {
      if (isSignup) {
        // Create a new Supabase account
        const { data, error } = await supabase.auth.signUp({
          email: email.trim(),
          password,
        });

        if (error) throw error;

        if (!data.session) {
          setMessage(
            "Account created! Check your email to confirm your account before logging in."
          );
        } else {
          setMessage("Account created successfully!");
        }
      } else {
        // Log in with an existing Supabase account
        const { error } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });

        if (error) throw error;
      }
    } catch (err) {
      setIsError(true);
      setMessage(
        err instanceof Error
          ? err.message
          : "Authentication failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  function toggleMode() {
    setIsSignup((previous) => !previous);
    setMessage("");
    setIsError(false);
    setPassword("");
  }

  return (
    <Center
      minH="100vh"
      bg="#0b1220"
      px={4}
      py={10}
    >
      <Box
        w="full"
        maxW="440px"
        bg="#152033"
        border="1px solid"
        borderColor="#29394f"
        borderRadius="2xl"
        p={{ base: 6, md: 8 }}
        boxShadow="0 20px 60px rgba(0,0,0,0.25)"
      >
        <form onSubmit={handleSubmit}>
          <Stack gap={6}>

            {/* Application branding */}
            <Stack align="center" gap={3}>
              <Center
                w="60px"
                h="60px"
                bg="rgba(56,189,248,0.12)"
                borderRadius="2xl"
              >
                <Activity
                  size={32}
                  color="#38bdf8"
                />
              </Center>

              <Heading
                size="2xl"
                color="white"
                textAlign="center"
              >
                Athletic Workload
              </Heading>

              <Text
                color="#94a3b8"
                fontSize="sm"
                textAlign="center"
              >
                Track your training. Understand your workload.
              </Text>
            </Stack>

            {/* Login / Signup heading */}
            <Box>
              <Heading
                size="lg"
                color="white"
                mb={2}
              >
                {isSignup ? "Create an account" : "Welcome back"}
              </Heading>

              <Text
                color="#94a3b8"
                fontSize="sm"
              >
                {isSignup
                  ? "Sign up to start analyzing your Garmin activities."
                  : "Sign in to view your workouts and training analytics."}
              </Text>
            </Box>

            {/* Email */}
            <Field.Root required>
              <Field.Label color="#cbd5e1">
                <HStack gap={2}>
                  <Mail size={15} />
                  <Text>Email address</Text>
                </HStack>
              </Field.Label>

              <Input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
                bg="#0b1220"
                borderColor="#34435a"
                color="white"
                _placeholder={{ color: "#64748b" }}
                _focusVisible={{
                  borderColor: "#38bdf8",
                  boxShadow: "0 0 0 1px #38bdf8",
                }}
              />
            </Field.Root>

            {/* Password */}
            <Field.Root required>
              <Field.Label color="#cbd5e1">
                <HStack gap={2}>
                  <Lock size={15} />
                  <Text>Password</Text>
                </HStack>
              </Field.Label>

              <Input
                type="password"
                placeholder={
                  isSignup
                    ? "Create a password"
                    : "Enter your password"
                }
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={
                  isSignup ? "new-password" : "current-password"
                }
                minLength={6}
                required
                bg="#0b1220"
                borderColor="#34435a"
                color="white"
                _placeholder={{ color: "#64748b" }}
                _focusVisible={{
                  borderColor: "#38bdf8",
                  boxShadow: "0 0 0 1px #38bdf8",
                }}
              />
            </Field.Root>

            {/* Authentication feedback */}
            {message && (
              <Box
                p={3}
                borderRadius="lg"
                bg={
                  isError
                    ? "rgba(239,68,68,0.10)"
                    : "rgba(34,197,94,0.10)"
                }
                border="1px solid"
                borderColor={
                  isError
                    ? "rgba(239,68,68,0.3)"
                    : "rgba(34,197,94,0.3)"
                }
                role={isError ? "alert" : "status"}
              >
                <Text
                  fontSize="sm"
                  color={isError ? "#fca5a5" : "#86efac"}
                >
                  {message}
                </Text>
              </Box>
            )}

            {/* Submit button */}
            <Button
              type="submit"
              w="full"
              size="lg"
              bg="#38bdf8"
              color="#0b1220"
              fontWeight="semibold"
              disabled={loading}
              loading={loading}
              _hover={{
                bg: "#7dd3fc",
              }}
            >
              {isSignup ? "Create Account" : "Log In"}
            </Button>

            {/* Toggle login/signup */}
            <HStack
              justify="center"
              gap={1}
              flexWrap="wrap"
            >
              <Text
                color="#94a3b8"
                fontSize="sm"
              >
                {isSignup
                  ? "Already have an account?"
                  : "Don't have an account?"}
              </Text>

              <Button
                type="button"
                variant="plain"
                size="sm"
                color="#38bdf8"
                disabled={loading}
                onClick={toggleMode}
                p={1}
                _hover={{
                  color: "#7dd3fc",
                }}
              >
                {isSignup ? "Log in" : "Sign up"}
              </Button>
            </HStack>

          </Stack>
        </form>
      </Box>
    </Center>
  );
}
