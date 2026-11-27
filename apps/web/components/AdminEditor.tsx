"use client";

import { useEffect, useRef, type ReactNode } from "react";

/** Native dialog supplies modal focus containment, Escape and focus restoration. */
export function AdminEditor({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { dialog.current?.showModal(); }, []);
  return <dialog ref={dialog} className="editor-panel admin-editor" aria-labelledby="editor-title" onCancel={onClose}>
    <div className="page-head"><h2 id="editor-title">{title}</h2><button className="btn btn-ghost btn-sm" onClick={onClose}>Tutup</button></div>
    <p className="muted">Perubahan sementara untuk sesi halaman ini.</p>
    {children}
  </dialog>;
}
