import { Link } from "react-router-dom";

import { useGameReturnTo } from "../hooks/useGameReturnTo";

type Props = {
  title: string;
  children: React.ReactNode;
};

export default function GameReferenceLayout({ title, children }: Props) {
  const returnTo = useGameReturnTo();

  return (
    <div className="game-ref-page">
      <div className="game-ref-page__sticky-bar">
        <Link to={returnTo} className="btn">
          ← Back to game
        </Link>
      </div>
      <div className="card">
        <h1 className="page-title">{title}</h1>
        {children}
      </div>
    </div>
  );
}
