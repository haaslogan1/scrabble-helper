import { Link } from "react-router-dom";
import NotificationBell from "./NotificationBell";
import UserMenu from "./UserMenu";

export default function SiteHeader() {
  return (
    <header className="site-header">
      <Link to="/" className="site-header__brand">
        Scrabble Helper
      </Link>
      <div className="site-header__actions">
        <NotificationBell />
        <UserMenu />
      </div>
    </header>
  );
}
