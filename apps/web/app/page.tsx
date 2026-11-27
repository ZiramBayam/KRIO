"use client";

import { useEffect } from "react";
import { session } from "@/lib/api";

export default function Home() {
  useEffect(() => {
    window.location.replace(session() ? "/dashboard/" : "/login/");
  }, []);
  return null;
}
