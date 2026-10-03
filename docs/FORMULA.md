# The episode formula

What the best-loved closed-circle mysteries have in common, written as a checklist every episode must pass.
No formula guarantees a hit. This one removes the usual ways a mystery turns out boring or unfair, so the part that is ours
alone (questioning suspects in free text, with a local model) stands on solid ground.

## Where it comes from

Drawn from well-known works, not from fresh research, so treat the lineage as a map and not as citations.

- **Christie**, *And Then There Were None* and *Murder on the Orient Express*: a closed circle where everyone is hiding something.
- ***Knives Out***: the obvious story is the wrong one, and the helper has a secret.
- ***Gone Girl*, *The Usual Suspects***: the account you were handed was manufactured.
- **Hitchcock's bomb under the table**: suspense is the audience knowing more than the characters. A stopped clock the player has noticed does this.
- **Games.** *Return of the Obra Dinn* and *The Case of the Golden Idol* get their "aha" from combining two clues.
  *Ace Attorney* is the closest ancestor of our mechanic: present the right evidence at the right contradiction.
  *Danganronpa* ends in a confrontation that pays off the evidence. *Her Story* is an interview as the whole game.
  *Disco Elysium* makes the detective a person with stakes.
- **Fair play.** Van Dine's twenty rules (1928) and Knox's ten commandments (1929): the solution must be reachable from clues the player was shown.

## The checklist

"Auto" means the case checker (see `DESIGN.md`) can verify it. "Manual" means a person reads the episode against it.

| # | Rule | Check |
|---|---|---|
| 1 | **Impossible hook in the first two minutes.** A locked room, a stopped clock. "How" arrives before "who". | manual |
| 2 | **Four to six suspects**, each with a want, a surface story, a lie, a **secret unrelated to the crime**, and one useful thing they saw. Fewer, deeper people beat more, shallower ones. Only those worth free-text questioning are model-voiced. | auto |
| 3 | **Closed circle and a clock.** No outside help, and every action costs minutes. | auto |
| 4 | **Nobody is clean.** Every suspect has an unwitnessed gap in the real timeline. | auto |
| 5 | **A false solution** that is satisfying and backed by at least three clues. Better, two layers of them (the obvious one, then the clever one). | auto count |
| 6 | **A proof set written as a deduction sheet**: a few claims, each with at least two alternative evidence routes, so one missed clue cannot make the case unsolvable. Every route is reachable inside the clock and before the twist that explains it. | auto |
| 7 | **Two-clue clicks.** At least three deductions that need two separate clues put together. | auto |
| 8 | **Midpoint reversal.** The prime suspect is removed or changes role, about half way through the action budget. | manual |
| 9 | **A reframe.** What the crime was changes (a staged time, a staged scene). Best when the player finds it out by doing something, not by being told. | manual |
| 10 | **A personal twist.** The detective was chosen, used or implicated. Best done in the interface: the player's own notebook carries the lie. | manual |
| 11 | **A costly ending choice.** Both options lose something, and the choice carries into the next episode. | manual |
| 12 | **A cliffhanger at every chapter end.** An unanswered question, a fired clock event or a new body. | manual |
| 13 | **A bad ending that is a consequence, not a game over.** The wrong verdict is the killer's win, and the series continues from it. | manual |
| 14 | **Every twist is re-readable.** Played again, each reveal turns out to have been on the table. | manual |
| 15 | **Humor.** Every speaking character has a comic register. A light beat within every three scenes, never during a death reveal. | manual |
| 16 | **A slow burn.** At least one optional romance that costs clock minutes, is mechanically useful and risky (trust opens people up), and pays off in the ending choice. | manual |
| 17 | **Warmth.** A recurring ally to talk to and, across a series, a home base to come back to. | manual |
| 18 | **Sound.** Each chapter has a musical mood and every clock event has a sound. Leitmotifs per suspect come later. | manual |
| 19 | **Always a next step.** The player can always see what they still need to know; there is never a blank box. | manual |
| 20 | **A narrow job for the AI.** The model voices what the code lets a person admit; it never decides the plot. | manual |

## What the checklist does not cover

- Whether it is moving. That is writing and playtest, not structure.
- Pacing in real minutes. Clock costs are tuned by playtest; the bible gives the intended shape.
- The hook that makes this game different from other mystery games. That is the interview, so every suspect has to be worth talking to.
