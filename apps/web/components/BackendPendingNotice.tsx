export interface BackendPendingNoticeProps {
  issues: string[];
  owner: string;
  className?: string;
}

export function BackendPendingNotice({
  issues,
  owner,
  className = "",
}: BackendPendingNoticeProps) {
  const issueList = issues.join(", ");
  return (
    <div className={`note note-info ${className}`.trim()} role="status">
      <div>
        Operasi ini memakai data sementara menunggu backend {issueList} (@{owner}). Tidak memengaruhi data asli.
      </div>
    </div>
  );
}
