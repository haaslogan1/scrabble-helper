import { Link } from "react-router-dom";
import UserMenu from "./UserMenu";

export default function SiteHeader() {
  return (
    <header className="site-header">
      <Link to="/" className="site-header__brand">
        Scrabble Helper
      </Link>
      <UserMenu />
    </header>
  );
}
