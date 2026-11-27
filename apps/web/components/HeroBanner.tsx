import { StatusBadge } from "./StatusBadge";
import type { Status } from "@/lib/format";

export interface HeroBannerProps {
  status: Status;
  title: string;
  detail: string;
  stat?: {
    label: string;
    value: string;
  };
}

export function HeroBanner({ status, title, detail, stat }: HeroBannerProps) {
  return (
    <section className={`hero-banner hero-banner-${status}`}>
      <div className="hero-banner-main">
        <div className="hero-banner-status">
          <StatusBadge status={status} />
        </div>
        <h2 className="hero-banner-title">{title}</h2>
        <p className="hero-banner-detail">{detail}</p>
      </div>
      {stat && (
        <div className="hero-banner-stat">
          <div className="hero-banner-stat-label">{stat.label}</div>
          <div className="hero-banner-stat-value num">{stat.value}</div>
        </div>
      )}
    </section>
  );
}
