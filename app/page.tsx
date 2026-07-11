import type { Metadata } from "next";
import manifest from "../public/characters/manifest.json";
import studioManifest from "../public/characters-one-bit-studio/manifest.json";
import { Gallery } from "./Gallery";

export const metadata: Metadata = {
  title: "Night Shift Society — Preview 100",
  description: "A private working preview of 100 Night Shift Society 8-bit character concepts.",
};

export default function Home() {
  return <Gallery manifest={manifest} traitSources={studioManifest.traitLibrary.categories.Archetype} />;
}
