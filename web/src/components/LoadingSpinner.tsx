export function LoadingSpinner({ message = "Loading..." }: { message?: string }) {
  return <p className="loading">{message}</p>;
}
