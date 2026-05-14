'use client';

import { Hero } from "@/components/ui/Hero";
import BenchmarkGrid from "@/components/features/BenchmarkGrid";
import UploadForm from "@/components/features/UploadForm";

export default function Home() {
  return (
    <main className="flex flex-1 w-full flex-col bg-[#fafafa] min-h-screen pb-20">
      <Hero />
      <div className="w-full -mt-8 relative z-20">
        <UploadForm />
        <BenchmarkGrid />
      </div>
    </main>
  );
}
