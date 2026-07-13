import type { Metadata } from "next";
import manifest from "../public/review/launch-candidate-666/manifest.json";
import audit from "../public/review/launch-candidate-666/qa/final-audit.json";
import { LaunchGallery } from "./LaunchGallery";

export const metadata: Metadata = {
  title: "Night Shift Society — 666 Launch Review",
  description: "The audited 666-piece Neon Nocturne launch collection with one-to-one metadata.",
};

export default function Home() {
  return <LaunchGallery manifest={manifest} audit={audit} />;
}
