import React from "react";

export function LoadingState({ message = "Loading…" }: { message?: string }): React.ReactElement {
  return (
    <div className="loading-state">
      <div className="spinner" />
      <span className="loading-text">{message}</span>
    </div>
  );
}

export default LoadingState;