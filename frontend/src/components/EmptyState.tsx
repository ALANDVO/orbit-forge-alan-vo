import React from "react";

export function EmptyState({
  title = "No items yet",
  description = "Create your first item to get started.",
  actionLabel,
  onAction,
}: {
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}): React.ReactElement {
  return (
    <div className="empty-state">
      <div className="empty-icon">○</div>
      <h3 className="empty-title">{title}</h3>
      <p className="empty-description">{description}</p>
      {actionLabel && onAction && (
        <button className="btn btn-primary" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}

export default EmptyState;