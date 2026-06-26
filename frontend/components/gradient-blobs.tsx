"use client";

import { motion } from "framer-motion";

export function GradientBlobs({ className = "" }: { className?: string }) {
  return (
    <div
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}
      aria-hidden
    >
      <motion.div
        className="bg-blob"
        style={{
          top: "-10%",
          left: "-5%",
          width: "420px",
          height: "420px",
          background:
            "radial-gradient(circle, hsl(213 94% 62%), transparent 70%)",
        }}
        animate={{ x: [0, 40, 0], y: [0, 30, 0] }}
        transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="bg-blob"
        style={{
          bottom: "-15%",
          right: "-10%",
          width: "520px",
          height: "520px",
          background:
            "radial-gradient(circle, hsl(199 89% 48%), transparent 70%)",
        }}
        animate={{ x: [0, -50, 0], y: [0, -20, 0] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="bg-blob"
        style={{
          top: "40%",
          left: "60%",
          width: "320px",
          height: "320px",
          background:
            "radial-gradient(circle, hsl(217 91% 60%), transparent 70%)",
        }}
        animate={{ x: [0, -30, 0], y: [0, 40, 0] }}
        transition={{ duration: 26, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}
