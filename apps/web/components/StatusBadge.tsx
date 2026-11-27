import { STATUS, type Status } from "@/lib/format";

export function StatusBadge({ status }: { status: Status }) {
  const s = STATUS[status];
  return (
    <span className={`badge badge-${status}`} title={s.hint}>
      <span aria-hidden="true">{s.icon}</span> {s.label}
    </span>
  );
}
