import type { ReactNode } from "react";

export interface FlipCardProps {
  flipped: boolean;
  front: ReactNode;
  back: ReactNode;
  className?: string;
}

export function FlipCard({ flipped, front, back, className = "" }: FlipCardProps) {
  return (
    <div className={`flip-card ${className}`.trim()}>
      <div className={`flip-card-inner ${flipped ? "is-flipped" : ""}`}>
        <div className="flip-card-face flip-card-front">
          {front}
        </div>
        <div className="flip-card-face flip-card-back">
          {back}
        </div>
      </div>
    </div>
  );
}
