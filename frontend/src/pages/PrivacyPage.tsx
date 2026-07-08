import { Link } from "react-router-dom";

export default function PrivacyPage() {
  return (
    <div>
      <div className="card">
        <h1 className="page-title">Privacy</h1>
        <Link to="/settings" className="back-link muted">← Settings</Link>
        <p className="muted">
          This is a minimal privacy summary for signed-in users. A full public policy will be added at launch.
        </p>
      </div>

      <div className="card settings-section">
        <h2>What we collect</h2>
        <ul>
          <li>Account information (email, display name, username)</li>
          <li>Game data (scores, players, settings, turn history)</li>
          <li>Photos you upload to games or your profile</li>
          <li>Feedback you send through the app</li>
        </ul>
      </div>

      <div className="card settings-section">
        <h2>Photos and storage</h2>
        <p>
          Game photos and custom profile pictures are stored in private object storage (Cloudflare R2 or compatible S3).
          Images are resized on the server and served through time-limited signed links — they are not publicly listed.
        </p>
        <p>
          If you sign in with Google, we cache your Google profile picture URL from sign-in. Uploading a custom profile
          photo replaces what others see until you remove it.
        </p>
      </div>

      <div className="card settings-section">
        <h2>Email</h2>
        <p>
          We use your email for account verification, sign-in, and (if you contact us) feedback replies. We do not sell
          your email address.
        </p>
      </div>

      <div className="card settings-section">
        <h2>Contact</h2>
        <p>
          Questions about privacy? Use the feedback button in the app or email the address shown in your account settings
          once a public contact address is published.
        </p>
        <p className="muted">Full marketing, cookie, and analytics policy will be added at public launch.</p>
      </div>
    </div>
  );
}
