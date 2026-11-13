
import { NavLink } from "react-router-dom";
import { Box, Flex, HStack, Text, Button } from "@chakra-ui/react";
import { Activity, Upload, BarChart3, TrendingUp, LogOut } from "lucide-react";
import { supabase } from "../lib/supabase";

const links = [
  { to: "/upload", label: "Upload", icon: Upload },
  { to: "/statistics", label: "Overall Statistics", icon: BarChart3 },
  { to: "/trends", label: "Workload Trends", icon: TrendingUp },
];

export default function Navbar() {
  async function logout() {
    const { error } = await supabase.auth.signOut();
    if (error) console.error(error.message);
  }

  return (
    <Box
      as="header"
      bg="#111c2e"
      borderBottom="1px solid #29394f"
      px={{ base: 4, md: 8 }}
      py={4}
    >
      <Flex
        maxW="1280px"
        mx="auto"
        align="center"
        justify="space-between"
        gap={4}
        wrap="wrap"
      >
        <HStack gap={3}>
          <Activity size={25} color="#38bdf8" />
          <Text fontWeight="bold" fontSize="lg" color="white">
            Athletic Workload
          </Text>
        </HStack>

        <HStack gap={2} wrap="wrap">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to}>
              {({ isActive }) => (
                <HStack
                  px={3}
                  py={2}
                  borderRadius="lg"
                  bg={isActive ? "#1d3855" : "transparent"}
                  color={isActive ? "#38bdf8" : "#94a3b8"}
                  _hover={{ bg: "#1d2b42", color: "white" }}
                  gap={2}
                >
                  <Icon size={17} />
                  <Text fontSize="sm">{label}</Text>
                </HStack>
              )}
            </NavLink>
          ))}
        </HStack>

        <Button
          size="sm"
          variant="outline"
          colorPalette="gray"
          onClick={logout}
        >
          <LogOut size={16} />
          Log out
        </Button>
      </Flex>
    </Box>
  );
}
