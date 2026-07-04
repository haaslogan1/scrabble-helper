import { describe, expect, it } from "vitest";

import {
  OFFICIAL_RULES_URL,
  REQUIRED_SECTION_IDS,
  SCRABBLE_RULES,
} from "./rulesContent";

describe("rulesContent", () => {
  it("includes all required sections", () => {
    const ids = SCRABBLE_RULES.map((s) => s.id);
    for (const id of REQUIRED_SECTION_IDS) {
      expect(ids).toContain(id);
    }
  });

  it("dictionary section describes challenge-only use", () => {
    const dictionary = SCRABBLE_RULES.find((s) => s.id === "dictionary");
    expect(dictionary).toBeDefined();
    const text = dictionary!.body.join(" ").toLowerCase();
    expect(text).toMatch(/challenge/);
    expect(text).toMatch(/exactly as played/);
    expect(text).toMatch(/during your own turn/);
    expect(text).not.toMatch(/prefix/);
  });

  it("official rules URL is HTTPS", () => {
    expect(OFFICIAL_RULES_URL).toMatch(/^https:\/\//);
  });

  it("each section has title and body paragraphs", () => {
    for (const section of SCRABBLE_RULES) {
      expect(section.title.length).toBeGreaterThan(0);
      expect(section.body.length).toBeGreaterThan(0);
      for (const paragraph of section.body) {
        expect(paragraph.length).toBeGreaterThan(0);
      }
    }
  });
});
