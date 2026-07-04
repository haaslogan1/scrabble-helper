import GameReferenceLayout from "../components/GameReferenceLayout";
import { OFFICIAL_RULES_URL, SCRABBLE_RULES } from "../content/rulesContent";

export default function RulesPage() {
  return (
    <GameReferenceLayout title="Scrabble basics">
      {SCRABBLE_RULES.map((section) => (
        <section key={section.id} className="rules-section">
          <h2>{section.title}</h2>
          {section.body.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </section>
      ))}
      <p className="muted">
        <a href={OFFICIAL_RULES_URL} target="_blank" rel="noopener noreferrer">
          Official rules (Hasbro)
        </a>
      </p>
    </GameReferenceLayout>
  );
}
