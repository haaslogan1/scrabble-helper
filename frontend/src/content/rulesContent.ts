export type RulesSection = { id: string; title: string; body: string[] };

export const SCRABBLE_RULES: RulesSection[] = [
  {
    id: "overview",
    title: "Goal",
    body: [
      "Score the most points by forming words on the board using letter tiles.",
      "Each letter has a point value; premium squares multiply letter or word scores.",
    ],
  },
  {
    id: "turns",
    title: "Taking a turn",
    body: [
      "On your turn, place one or more tiles on the board to form a valid word (reading left-to-right or top-to-bottom).",
      "All new words formed in a single play must be valid.",
      "Draw new tiles from the bag to refill your rack to seven tiles, unless the bag is empty.",
      "You may pass or exchange tiles instead of playing (house rules may vary).",
    ],
  },
  {
    id: "bingo",
    title: "Bingo bonus",
    body: [
      "If you use all seven tiles on your rack in one turn, add a 50-point bonus to your score for that play.",
    ],
  },
  {
    id: "challenge",
    title: "Challenges",
    body: [
      "If a player doubts a word, they may challenge it before the next turn begins (house rules may vary).",
      "If the word is not valid, the play is removed and the player loses their turn (or draws a penalty — agree before you start).",
      "If the word is valid, the challenger may lose their next turn or draw a penalty.",
    ],
  },
  {
    id: "dictionary",
    title: "Using the dictionary",
    body: [
      "The in-app dictionary is for resolving challenges only, after a word has been played on the board.",
      "Enter the word exactly as played — same letters, same order. Do not browse or search for words.",
      "Using the dictionary during your own turn to find words is not allowed — same as table Scrabble etiquette.",
      "If a challenged word is not in the dictionary, treat the play as invalid per your agreed challenge rules.",
    ],
  },
  {
    id: "end",
    title: "Ending the game",
    body: [
      "The game ends when one player uses all their tiles and the bag is empty, or when all players pass twice in a row.",
      "Subtract unplayed tiles from each player's final score; the player who went out adds the sum of opponents' unplayed tiles to their score.",
    ],
  },
];

export const OFFICIAL_RULES_URL = "https://scrabble.hasbro.com/en-us/rules";

export const REQUIRED_SECTION_IDS = [
  "overview",
  "turns",
  "bingo",
  "challenge",
  "dictionary",
  "end",
] as const;
