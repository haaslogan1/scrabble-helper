import { useLocation, useSearchParams } from "react-router-dom";

export function useGameReturnTo(): string {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const stateReturn = (location.state as { returnTo?: string } | null)?.returnTo;
  if (stateReturn) return stateReturn;
  const gameId = searchParams.get("gameId");
  if (gameId) return `/game/${gameId}/play`;
  return "/";
}
