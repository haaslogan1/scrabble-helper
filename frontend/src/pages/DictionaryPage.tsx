import { FormEvent, useState } from "react";

import { checkDictionaryWord } from "../api";
import GameReferenceLayout from "../components/GameReferenceLayout";

type CheckState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "result"; word: string; valid: boolean }
  | { status: "error"; message: string };

export default function DictionaryPage() {
  const [input, setInput] = useState("");
  const [check, setCheck] = useState<CheckState>({ status: "idle" });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const word = input.trim();
    if (!word) {
      setCheck({ status: "error", message: "Enter the word exactly as played." });
      return;
    }
    setCheck({ status: "loading" });
    try {
      const result = await checkDictionaryWord(word);
      setCheck({ status: "result", word: result.word, valid: result.valid });
    } catch (err) {
      setCheck({
        status: "error",
        message: err instanceof Error ? err.message : "Could not check word",
      });
    }
  }

  return (
    <GameReferenceLayout title="Check word">
      <div className="dictionary-callout banner banner--info">
        <strong>Challenge lookup only.</strong> Enter the word exactly as it was played on
        the board. Do not use this to find words during your turn.
      </div>

      <form className="dictionary-form" onSubmit={onSubmit}>
        <label htmlFor="dictionary-word">Word as played</label>
        <input
          id="dictionary-word"
          className="input"
          type="text"
          autoComplete="off"
          autoCapitalize="characters"
          placeholder="e.g. QUIZ"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button type="submit" className="btn" disabled={check.status === "loading"}>
          {check.status === "loading" ? "Checking…" : "Check word"}
        </button>
      </form>

      {check.status === "error" && <p className="error-text">{check.message}</p>}

      {check.status === "result" && (
        <p
          className={
            check.valid ? "dictionary-result dictionary-result--valid" : "dictionary-result dictionary-result--invalid"
          }
          role="status"
        >
          {check.valid
            ? `${check.word} is valid.`
            : `${check.word} is not in the dictionary.`}
        </p>
      )}
    </GameReferenceLayout>
  );
}
