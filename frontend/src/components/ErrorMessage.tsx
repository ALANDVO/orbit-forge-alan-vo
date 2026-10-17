import React from "react";

export function ErrorMessage({ error, onRetry }: { error: string; onRetry?: () => void }): React.ReactElement {
  return (
    <div className="error-message">
      <span className="error-icon">⚠</span>
      <span className="error-text">{error}</span>
      {onRetry && (
        <button className="btn btn-sm btn-secondary" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export default ErrorMessage;