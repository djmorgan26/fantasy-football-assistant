# Fantasy Hub product refinement — discovery backlog

Status: discovery in progress. Yahoo account-selection plus read-only roster, matchup, and FAAB retrieval are implemented locally; live-provider verification remains pending deployment with configured Yahoo OAuth credentials.

## Delivery rule

After each backlog item is implemented and verified, update this file to reflect its status, commit the complete change, and push it to `main`.

## Decisions made

- Yahoo and ESPN are expected to use the same email address. Current symptom: clicking the Yahoo connection button identifies a different email from the Gmail account associated with the user's leagues. Investigate provider-account/session identity and OAuth account selection before changing the UI.
- Clarification: Fantasy Hub is signed in with Gmail, while the desired Yahoo Fantasy account uses a different email. The Yahoo connector must authorize that independent Yahoo account and persist its token against the signed-in Fantasy Hub user.
- Implemented locally: Yahoo authorization now includes `prompt=login`, which makes Yahoo authenticate instead of silently reusing the browser session; the connected-league step includes a “Use another Yahoo account” action. Tokens continue to be encrypted and stored on the signed-in Fantasy Hub user.
- Implemented locally: the Yahoo connector now plainly states that the next step is a Yahoo sign-in to attach a Yahoo league to the current Fantasy Hub account, rather than a second Fantasy Hub login.
- Implemented locally: Yahoo OAuth now returns to the exact Fantasy Hub browser origin that launched it, rather than relying solely on a deployment-wide `FRONTEND_URL`. This preserves the signed-in session when the app is accessed from a different deployment URL.
- Implemented locally: the Yahoo empty state now identifies the successful connection/no-leagues condition and directs the user to reauthorize with the Yahoo account that owns their Fantasy Football league.
- Implemented locally: automated Yahoo connector tests now cover the signed return origin, explicit Yahoo-sign-in explanation, empty-league account-switching path, and league selection path so CI protects this flow.
- Implemented locally: CI's stale frontend function-coverage gate was aligned to the verified full-suite baseline (56%). The full frontend suite has 286 passing tests, including the Yahoo connection flow tests.
- Implemented locally: mock-mode CORS accepts the localhost URL served to users (`127.0.0.1:3000`) as well as `localhost:3000`, so the demo sign-in and all local API routes work from the provided URL.
- Implemented locally and deployed: production testing reproduced a Yahoo-only authentication regression where opening the Yahoo connector could send an otherwise valid Fantasy Hub session to `/login`. Every Yahoo request now explicitly reads the saved Fantasy Hub token when it runs. The focused tests, lint, and build pass; live verification with the user's Google session and Yahoo handoff remains required before this item is complete.
- Implemented locally: the Yahoo adapter now retrieves team rosters, weekly scoreboards/matchups, and team FAAB balances, normalizing them for the app's existing Yahoo roster, Game Day, and waiver-budget endpoints. The live response shapes and league-specific availability still need verification against the user's Yahoo league.
- Yahoo should have feature parity with ESPN wherever the underlying provider data supports it.
- Game Plan is strictly per league.
- Both leagues use $100 FAAB. Recommendations should be dollar bids, not percentages.
- Injury recommendations must be a contextual judgment based on expected absence duration and player value; there is no blanket “IR means hold” or “IR means drop” policy.
- Trade Analyzer needs player-name autocomplete.
- Roasts should feel like a hilarious league television show: broad, high-energy 2000s-comedy absurdity with situational references, inspired by *Zoolander*, *Grown Ups*, *Ace Ventura*, *Airplane!*, and *Monty Python*. Keep it fantasy-specific and fact-grounded; do not imitate any individual performer or reproduce source material.

## Desired outcomes captured from the initial brief

- Confirm that Yahoo connection and signed-in league visibility work alongside ESPN, including correct provider-account identity during Yahoo OAuth.
- Keep League Overview, My Roster, Game Day, and the community/Press Box experience; reduce the rest of the navigation and competing features.
- Make Game Plan the weekly action center: start/sit, drops, waivers, FAAB bid recommendations, and rationale.
- Let Trade Analyzer accept player names rather than provider-specific IDs.
- Make injury-related recommendations sensitive to expected absence length and player value; specifically, do not recommend dropping A.J. Brown merely because he is on IR.
- Improve roast humor and tone.
- Make Across Leagues a high-level action summary, including start/sit and a quick waiver move.
- Remove waiver budget and league-team detail from Overview; show matchup in Game Day and team details/budget from a team page.
- Move Player Search, News, and Draft Room into Overview actions; fold Message Board into Press Box.

## Discovery questions to answer before implementation

### 1. Accounts, Yahoo, and ESPN

- Yahoo symptom confirmed: the account identity selected/displayed when clicking the Yahoo connection button is not the Gmail address associated with the user's Yahoo and ESPN leagues. Determine whether this happens before consent, in the consent/account chooser, on callback, or after callback.
- Is the unexpected email an old Yahoo account, another Google/Yahoo account active in the browser, or an email being displayed by Fantasy Hub itself?
- Does the problem reproduce in a private browser session after signing into only the intended Yahoo account?
- Does Yahoo finish consent but connect the wrong/no leagues, or is connection blocked before consent completes?
- Which Yahoo league(s) should appear? Target parity is every supported ESPN experience; document any Yahoo API limitations explicitly rather than silently omitting features.
- Do you want a visible connection health/status indicator, a reconnect prompt when a token expires, or both?
- Are ESPN leagues private and dependent on stored ESPN cookies? If so, do you want the product to clearly distinguish an expired ESPN credential from an unavailable provider?
- Should the signed-in landing experience always show a combined league picker, or automatically open the most recently used league?

### 2. Navigation and simpler layout

- Which existing top-level destinations should remain visible: Overview, My Roster, Game Day, Game Plan, Press Box, Across Leagues, Trade Analyzer, Profile?
- When Player Search, News, and Draft Room move into Overview actions, should they remain as full pages accessible only from those action cards, or become drawers/modals inside Overview?
- Should Trade Analyzer remain top-level or move under an Overview/Game Plan action as well?
- Does “League Overview is good to stay” mean it is the default post-login page?
- Should Press Box contain only News + Message Board + Roasts, or should it also contain other editorial/community content?
- Do you prefer desktop-style left navigation, a compact top bar, or an overview-first dashboard with minimal navigation?

### 3. Game Plan and weekly actions

- Game Plan is per league. What starts the “following week” plan: after the current matchup completes, a configurable deadline, or a manual “plan for Week N” selector?
- What actions are actionable versus advisory: can the user mark complete/dismiss/snooze, export them, or only read them?
- For each action type, what minimum explanation earns trust (projection gap, matchup, role change, injury news, roster need, schedule, etc.)?
- Should Game Plan rank a fixed number of recommendations, or show all that meet a confidence threshold?
- How should conflicting advice be handled (for example, a player appears in start/sit and a trade opportunity)?

### 4. Start/sit, drops, waivers, and FAAB

- What scoring and roster settings matter for recommendations: PPR/half/standard, superflex, TE premium, bench size, IR slots, and keeper/dynasty rules?
- Should start/sit compare only players already on the user’s roster, and should it account for locked Thursday players?
- What qualifies a player as droppable: replacement value, bench role, injury timeline, bye, projected rest-of-season value, or your own protected-player list?
- For IR players, define the contextual factors and their precedence: expected return date, season-ending designation, player tier/rest-of-season value, league format, bench/IR capacity, team record, and playoff timing.
- Should the system use verified injury reports, expected return dates, and season-ending designations before issuing a drop recommendation?
- FAAB recommendations are dollar bids. Both current leagues have a $100 budget. Should the recommendation still be tailored to remaining budget, opponent/team budgets, league size, roster need, and player urgency? What bid style do you prefer: conservative, balanced, or aggressive?
- Do you want primary bid, fallback bid, and contingency drops for each waiver target?
- Is the waiver deadline consistent across your leagues, and should the app show the time remaining?

### 5. Trade Analyzer names instead of IDs

- Use free-text player-name autocomplete. Should it also support paste-friendly lists of names?
- Must it resolve players from the active league only, or also handle free agents and players from other platforms?
- How should ambiguous names be disambiguated: team, position, headshot, provider, or all of these?
- Should the analyzer support multi-player and draft-pick packages, future picks, or just players for now?
- What should the result prioritize: redraft value, dynasty/keeper value, current-week lineup impact, or rest-of-season value?

### 6. Roasts and voice

- Use a league-TV-show voice: exaggerated, visual, fast, absurd, and tied to the week’s actual fantasy events.
- What is too far—profanity, personal/real-life references, insults about intelligence, repeated player clichés?
- Should roasts be opt-in, set to mild/medium/spicy, or have a single default tone?
- Reference palette: 2000s studio comedy and classic absurdist comedy (including *Zoolander*, *Grown Ups*, *Ace Ventura*, *Airplane!*, and *Monty Python*) without direct imitation or quoted material. Should every roast cite an observable fantasy fact so it feels earned rather than random?

### 7. Across Leagues, Game Day, and team detail

- In Across Leagues, do you want one top action per league, or a short ranked list (for example, one start/sit and one waiver move)?
- Should it group repeated player decisions across leagues, such as “Start Player X in 3 of 4 leagues”?
- What is the desired click-through from each summary action: Game Plan, My Roster, Game Day, waiver target, or a team detail?
- On Game Day, should clicking any opponent team open a read-only team profile equivalent to My Roster?
- Which details belong on that team profile: roster, starters, bench, FAAB, record, waiver priority, transactions, needs, trade block, and/or matchup history?
- Is team budget private in any league, or can it always be shown?

## Proposed implementation order (after answers)

1. Reproduce and repair Yahoo/ESPN signed-in connection visibility, with clear error states.
2. Agree the information architecture and remove/de-emphasize destinations accordingly.
3. Define recommendation policy and data requirements for Game Plan, including injury-duration and FAAB logic.
4. Build the Game Plan workflow and Across Leagues action summaries.
5. Replace Trade Analyzer ID input with name resolution and ambiguity handling.
6. Refine Press Box, team-detail routing, and roast voice.
7. Validate with your actual ESPN and Yahoo leagues plus regression tests for the key decision rules.

## Acceptance checks to define with you

- A signed-in user can see and switch between their ESPN and Yahoo leagues without losing the other provider’s leagues.
- Game Plan gives next-week, league-specific actions with clear rationale and appropriate FAAB guidance.
- A temporary IR designation alone cannot trigger a drop recommendation for a high-value player.
- Trade Analyzer can select correct players by name without requiring a provider ID.
- Overview is visibly simpler and links to Search, News, and Draft Room as actions.
- Across Leagues conveys the most important start/sit and waiver move at a glance.
