# Dota 2 AI Coach

Real-time coaching companion for Dota 2. Reads your game state, watches your screen, and gives you actionable tips via a transparent overlay -- all while you play.

**How it works:** Game State Integration (GSI) feeds live match data, OpenCV reads your minimap/items/cooldowns from the screen, and an LLM turns it all into short coaching tips displayed on top of your game. During **hero selection** (`HERO_SELECTION`), the vision layer switches to **draft mode**: it crops the top portrait bar, segments slots, and template-matches against `assets/templates/portraits/` (created by `download_assets.py`) so the coach can suggest picks (detection quality depends on resolution/UI; re-run `download_assets.py` if portraits are missing).

---

## Quick Start (Windows)

### 1. Install Python

Download Python 3.10+ from [python.org/downloads](https://www.python.org/downloads/).

> **Important:** During install, check the box that says **"Add python.exe to PATH"**.
>
> After install, open a **new** Command Prompt or PowerShell and verify:
> ```
> python --version
> ```

### 2. Download the app

```
git clone <repo-url> gameai
cd gameai
```

Or download the ZIP from the repo page, extract it, and open a terminal in the folder.

### 3. Install dependencies

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

This takes 1-3 minutes and downloads about 250 MB (OpenCV, PyQt6, etc).

### 4. Set up your LLM (pick one)

Copy the example env file:

```
copy .env.example .env
```

Then open `.env` in Notepad and configure **one** of these:

**Option A -- OpenAI (easiest, ~$0.01 per game)**
```
COACH_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...paste-your-key...
```
Get a key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys).

**Option B -- Anthropic**
```
COACH_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...paste-your-key...
```

**Option C -- Ollama (free, runs on your PC, no key needed)**
1. Install from [ollama.com](https://ollama.com)
2. Open a terminal and run: `ollama pull llama3.2`
3. In `.env` set:
```
COACH_LLM_PROVIDER=ollama
```

### 5. Install the Dota 2 GSI config

This tells Dota to send live game data to the coach app.

```
python scripts/setup_gsi.py
```

The script auto-detects your Dota 2 install and copies the config file. If auto-detection fails, it will ask you to paste your Dota path.

> **Manual alternative:** copy `assets\config\gamestate_integration_coach.cfg` into:
> ```
> C:\Program Files (x86)\Steam\steamapps\common\dota 2 beta\game\dota\cfg\gamestate_integration\
> ```
> Create the `gamestate_integration` folder if it doesn't exist.

### 6. Download vision templates

```
python scripts/download_assets.py
```

Downloads hero and item icons from Steam's CDN for screen matching (~2 min). Hero downloads also write **color draft portraits** (62×35) under `assets/templates/portraits/` for pick-screen matching; minimap templates stay grayscale in `assets/templates/heroes/`.

### 7. Set Dota 2 to Borderless Windowed

In Dota 2: **Settings > Video > Display Mode > Borderless Window**

This is required -- exclusive fullscreen blocks both the overlay and screen capture.

### 8. Run

```
python main.py
```

The app runs startup checks and tells you if anything is missing. Once running, start a Dota 2 match and coaching tips will appear in the top-right corner of your screen.

To launch with the **debug panel** (live GSI state, LLM stats, and logs below the overlay):

```
python main.py --debug
```

---

## Quick Start (Mac)

### 1. Install Python

Mac comes with an older Python. Install 3.10+ via Homebrew (recommended) or from python.org:

```bash
# Option A: Homebrew (if you have it)
brew install python@3.13

# Option B: download from python.org/downloads
```

Verify:
```bash
python3 --version
```

### 2. Download the app

```bash
git clone <repo-url> gameai
cd gameai
```

### 3. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Set up your LLM (pick one)

```bash
cp .env.example .env
open -e .env    # opens in TextEdit
```

Edit `.env` and configure one provider (see the Windows section above for details on each option). The simplest free option:

```
COACH_LLM_PROVIDER=ollama
```

Then install Ollama: download from [ollama.com](https://ollama.com), and run:
```bash
ollama pull llama3.2
```

### 5. Install the Dota 2 GSI config

```bash
python scripts/setup_gsi.py
```

The script checks the standard Mac Steam path (`~/Library/Application Support/Steam/...`). If auto-detect fails, paste your Dota cfg path when prompted.

> **Manual alternative:** copy the GSI config into:
> ```
> ~/Library/Application Support/Steam/steamapps/common/dota 2 beta/game/dota/cfg/gamestate_integration/
> ```

### 6. Download vision templates

```bash
python scripts/download_assets.py
```

### 7. Set Dota 2 to Borderless Windowed

In Dota 2: **Settings > Video > Display Mode > Borderless Window**

### 8. Run

```bash
python main.py
```

For **debug mode** (live GSI state, LLM stats, and logs): `python main.py --debug`

> **Mac permissions note:** The first launch may trigger macOS permission prompts:
> - **Screen Recording** -- required for `mss` screen capture. Go to **System Settings > Privacy & Security > Screen Recording** and enable your Terminal app.
> - Without this, the vision pipeline will capture blank frames. GSI and the LLM coach still work fine without it.

---

## Quick Start (Linux)

Same as the Mac steps above. The GSI setup script checks `~/.steam/steam` and `~/.local/share/Steam`. Use `source .venv/bin/activate` and `cp .env.example .env`. No special permissions needed -- X11/Wayland screen capture works out of the box with `mss`.

---

## Standalone Executable (no Python needed)

For distributing to users who don't want to install Python:

```
python scripts/build_exe.py
```

This uses PyInstaller to create `dist/DotaCoach/DotaCoach.exe`. Zip and share the folder. Users still need to:
1. Create a `.env` file with their LLM key (or use Ollama)
2. Run `scripts/setup_gsi.py` (bundled inside)
3. Set Dota to borderless windowed

---

## Configuration

The app reads settings from `config.yaml` (defaults) with optional overrides in `config.local.yaml` or `.env`.

| Setting | Default | What it does |
|---------|---------|--------------|
| `capture.fps` | `2.0` | Screen captures per second (higher = more CPU) |
| `llm.provider` | `openai` | LLM backend: `openai`, `anthropic`, or `ollama` |
| `llm.throttle_seconds` | `10.0` | Minimum seconds between coaching tips |
| `overlay.position` | `top_right` | Tip location: `top_right` or `right_center` |
| `overlay.tip_duration_seconds` | `8.0` | How long each tip stays on screen |
| `paths.templates_portraits` | `assets/templates/portraits` | Color portrait templates for draft detection |

Launch with `python main.py --debug` to show a debug panel below the overlay with live GSI data, LLM call counts and latency, vision pipeline mode, and a scrollable log viewer.

---

## Architecture

```
GSI (JSON/HTTP) ──> Flask server ──> State Aggregator ──> LLM Coach ──> Overlay
Screen capture  ──> Vision Pipeline ──────┘                              (PyQt6)
                    (OpenCV detectors)

Draft mode (HERO_SELECTION):
  GSI game_state ──> MatchLifecycle ──> set_mode("draft") on VisionPipeline
  Screen capture ──> Draft Detector (top-bar slot segmentation + portrait template match)
                 ──> DraftState ──> draft-specific LLM prompt ──> pick suggestion in Overlay
```

- `src/gsi/` -- Flask GSI receiver, typed parser
- `src/vision/` -- `mss` capture (~2 FPS), template matching detectors (minimap, items, health/mana, cooldowns); **draft detector** segments the top portrait bar and matches slots against `assets/templates/portraits/`
- `src/state/` -- Aggregator merges GSI + vision; match lifecycle auto-detects game start/end and **draft phase** (HERO_SELECTION)
- `src/llm/` -- Pluggable providers (OpenAI, Anthropic, Ollama), throttled prompts, tip deduplication; switches to a **draft-specific prompt** during hero selection
- `src/overlay/` -- Always-on-top coaching sidebar with chat, message history, and in-app settings
- `src/db/` -- SQLite (WAL mode) with tables for matches, events, vision snapshots, and coaching tips

---

## Tests

```
pip install pytest
python -m pytest tests/ -v
```

---

## Performance

The app is designed to run alongside Dota 2 with minimal impact:

- Screen capture: ~2% CPU at 2 FPS
- Vision processing: ~3% CPU (template matching, no GPU)
- LLM calls: network-bound, one call every ~10 seconds
- Overlay: negligible (repaints only on new tips)
- **Total: ~5% CPU, ~200 MB RAM**

---

## TODO

1. On selecting a different hero, take a screenshot and suggest the new strategy.
2. Alert for runes.
3. Item build at certain interval and money.
4. Click through setting.
5. START OF game - based on the hero I clicked, which enemy heroes would I dominate early, mid, and late game.
6. If no enemy heroes selected, tell something random to try.
7. During draft - tell which lane to prefer.
8. Suggest combo skills and powers based on allies.
9. Suggest initial items and must-have items based on enemy heroes (e.g., magic wand vs Bristleback).
10. First skill to pick.
11. Personal combo skills.
12. What to do next to be MVP.
13. Target heroes for next gank fights.
14. Whom to take down first.
15. Whom to keep disabled for longer.
16. Why someone is owning currently.
17. End of game: turning points, insights, etc.

---

## 500 In game Awareness & Strategy Points

1. Identify your win condition before the horn.
2. Identify the enemy win condition before the horn.
3. Decide whether your hero wants long or short fights.
4. Check if your lane is kill lane or sustain lane.
5. Confirm who buys courier and first wards.
6. Plan first observer ward around your lane objective.
7. Plan first sentry based on likely enemy ward.
8. Predict enemy lane matchups and swap risks.
9. Decide if your hero needs a defensive starting item.
10. Decide if your hero can greed for stat items.
11. Note enemy heroes with level-one power spikes.
12. Note allied heroes with level-one setup spells.
13. Plan rune contest path before moving from fountain.
14. Decide whether to smoke for bounty rune fight.
15. Call target priority for level-one skirmish.
16. Keep TP available if early lane collapse happens.
17. Check if lane equilibrium should be blocked hard.
18. Block your wave based on matchup difficulty.
19. If unplayable lane, pre-plan recovery jungle camp.
20. Pick first skill for immediate lane purpose.
21. Track enemy support starting items for lane intent.
22. If enemy has stick-value spells, buy stick early.
23. If enemy has heavy right click, buy armor first.
24. If enemy has spam nukes, buy regen plus wand.
25. Confirm who secures range creep in first wave.
26. Decide if you contest first range creep aggressively.
27. Check if your support can pull at 1:15.
28. Check if enemy support can block your pull camp.
29. Position to avoid giving free harass before creeps meet.
30. Use creep aggro to fix lane positioning.
31. Save mana for guaranteed value, not random poke.
32. Harass when enemy is committed to last hit animation.
33. Count enemy tangos to estimate lane longevity.
34. Watch for support rotations by missing map heroes.
35. Communicate when lane opponent uses key cooldown.
36. Punish enemy after missed spell or creep deny.
37. Secure lotus pool timing if lane can leave.
38. Keep lane warded if enemy has kill rotation hero.
39. Drop sentry when enemy positioning suggests vision.
40. Use fog to break projectile and cast animations.
41. Control lane near your tower if you are weaker.
42. Push lane only when you need rune or pull timing.
43. Stack nearby camp during safe downtime.
44. Deny your range creep whenever possible.
45. Avoid tanking full creep wave for one deny.
46. Decide early if boots timing matters for matchup.
47. Buy wind lace early if movement wins trades.
48. If lane is static, threaten with fake cast movement.
49. Keep enough mana for one defensive spell.
50. Respect level-two power spike timings.
51. Respect level-three dual-spell kill windows.
52. Re-evaluate lane once either core hits level six.
53. Rotate only after pushing lane to avoid losses.
54. If rotating, ping destination and expected target.
55. Carry TP when farming side lane after minute five.
56. Keep one sentry in inventory against invis heroes.
57. If you force enemy regen, lane trade succeeded.
58. Prioritize experience if gold is contested.
59. Do not die for small neutral camp.
60. Convert lane advantage into tower chip damage.
61. Check catapult wave timers before committing.
62. Group for catapult if your lineup pushes early.
63. Defend your catapult with body blocks and spells.
64. Kill enemy catapult quickly on defense.
65. Track power rune spawn every two minutes.
66. Place mid ward to secure one rune side.
67. Bottle refill your mid if support can rotate.
68. Gank with rune carrier when enemy overextends.
69. If no rune control, play safer for two minutes.
70. Scout enemy jungle entrances after first tower falls.
71. Decide which lane to deadlane and which to protect.
72. Farm triangle only if it is warded or safe.
73. Smoke when key enemy ult is on cooldown.
74. Avoid smoke when your own big ult is unavailable.
75. Smoke to place deep vision, not only to gank.
76. Check item spikes before forcing objective.
77. Fight when your core finishes first major item.
78. Disengage if enemy just hit stronger timing.
79. Do not reveal blink dagger before big fight.
80. Break smoke only with intended initiator.
81. Keep buyback status in mind before risky push.
82. Push side waves before Roshan attempt.
83. Force enemy to show on waves before objective.
84. Carry detection if enemy has glimmer or shadow blade.
85. Upgrade wand if fights are frequent and spell-heavy.
86. Buy raindrops against repeated magical burst.
87. Buy infusions or clarities between skirmishes.
88. Keep one slot for dust in mid game.
89. Farm dangerous wave with illusions if available.
90. Use summons to scout high ground ramps.
91. Respect TP responses when diving tier-two.
92. Set ward behind tower before long siege.
93. Use glyph and fortification to stall bad fights.
94. Trade opposite side objective if outnumbered.
95. Save stun for channeling ult or TP cancel.
96. Bait dispel before using your hard disable.
97. Chain stuns with clear count timing.
98. Focus same target when enemy has save heroes.
99. Kill save hero first if reachable.
100. Keep silence for mobile spell-caster cores.
101. Buy anti-heal when enemy has sustain core.
102. Buy break when enemy relies on passives.
103. Buy armor aura versus physical burst lineups.
104. Buy pipe aura versus heavy magical AoE.
105. Buy force staff against slows and area control.
106. Buy lotus orb against single-target disables.
107. Buy BKB before damage item if chain-disabled.
108. Delay greed item if survival is failing.
109. Recognize when damage is enough and survivability needed.
110. Avoid duplicate aura items unless planned.
111. Share scan usage with objective timings.
112. Save scan for smoke prediction near Roshan.
113. Use twin gates when enemy expects normal pathing.
114. Watch minimap every few seconds while farming.
115. If three enemies missing, farm near allies.
116. If enemy shows four heroes, pressure opposite lane.
117. Keep lane shoved before entering jungle.
118. Farm pattern should end near objective, not random.
119. Clear nearest dangerous wave before taking camp stack.
120. Stack while rotating whenever possible.
121. Use smoke to recover map after lost fight.
122. Avoid random high ground without vision.
123. Defend high ground with wave clear and patience.
124. Buyback only if objective is contestable.
125. Do not buyback into no-spell no-item state.
126. Track enemy buybacks after winning fight.
127. End game only if enemy buybacks are low.
128. If not ending, secure Roshan and map control.
129. De-ward before critical objective attempt.
130. Place sentry on common cliff before warding.
131. Move unpredictably after showing on lane.
132. Use smoke to cross warded mid areas.
133. Pre-cast defensive buffs before jumping.
134. Keep one save spell for counter-initiation.
135. Split fights if enemy has big AoE combo.
136. Tighten formation if enemy has pickoff heroes.
137. Do not chase past vision and objective value.
138. Convert kills into tower, Roshan, or map wards.
139. Hit building when key defenders are dead.
140. Reset if fight extends beyond your cooldown window.
141. Consider neutral item timing at 7/17/27/37/60.
142. Distribute neutral items to best role, not greed.
143. Swap neutrals before fight based on matchup.
144. Carry teleport scroll always after minute ten.
145. Use outpost control for TP access and vision.
146. Protect tormentor attempt with lane pressure first.
147. Contest enemy tormentor only with numbers advantage.
148. Save mobility spells for disengage if no kill.
149. Count enemy dispels before committing root.
150. Initiate on hero without defensive cooldown first.
151. In draft, ask who fronts and who follows.
152. In draft, avoid all-greed no-stun compositions.
153. In draft, ensure at least one building hitter.
154. In draft, secure wave clear against zoo heroes.
155. In draft, pick lane sustain if facing harass lanes.
156. In draft, pick disable if facing mobile cores.
157. In draft, pick burst if enemy has weak saves.
158. In draft, pick save if your carry is greedier.
159. In draft, respect last-pick cheese conditions.
160. In draft, ban heroes that punish your comfort pick.
161. In draft, pair stuns with follow-up damage type.
162. In draft, spread damage types physical and magical.
163. In draft, avoid all melee versus heavy kiting.
164. In draft, avoid all squishy versus global burst.
165. In draft, ensure at least one dispel source.
166. In draft, secure initiation from fog.
167. In draft, confirm lane support duo synergy.
168. In draft, pick hero with clear lane plan.
169. In draft, pick hero with fallback farm route.
170. In draft, plan first ten-minute objective.
171. During lane, communicate creep pull timer repeatedly.
172. During lane, body block enemy pull camp if needed.
173. During lane, unblock your own camp quickly.
174. During lane, deny banner creep pressure timing.
175. During lane, commit when enemy misses key nuke.
176. During lane, fake aggression to draw support reaction.
177. During lane, secure wisdom rune rotation timing.
178. During lane, punish support leaving lane for rune.
179. During lane, keep courier path safe from snipes.
180. During lane, avoid fighting under enemy full wave.
181. Skill build should solve immediate lane problem first.
182. Skill build can delay greedy point if kill threat high.
183. Skill build should respect enemy dispel availability.
184. Skill build should include farming point before jungle transition.
185. Skill build should enable one-shot combo by key level.
186. Skill build should maximize range creep secure tool.
187. Skill build should adjust if behind, favor safer spells.
188. Skill build should adjust if ahead, favor pressure spells.
189. Skill build should include one value utility point.
190. Skill build should match your mana pool reality.
191. Item timing target at minute three: lane sustain tools.
192. Item timing target at minute six: boots or wand spike.
193. Item timing target at minute ten: first role-defining item.
194. Item timing target at minute fifteen: fight or farm choice.
195. Item timing target at minute twenty: survivability check.
196. Item timing target at minute twenty-five: objective item.
197. Item timing target at minute thirty: anti-carry adaptation.
198. Item timing target at minute thirty-five: high ground readiness.
199. Item timing target at minute forty: buyback plus item balance.
200. Item timing target late game: slot efficiency and backpack swaps.
201. Individual combo: open with gap-close, then instant disable.
202. Individual combo: bait defensive item before full commit.
203. Individual combo: use slow before skillshot for reliability.
204. Individual combo: animation-cancel to hide spell intent.
205. Individual combo: chain mobility with terrain for escape.
206. Individual combo: save nuke to finish after save triggers.
207. Individual combo: cast silence before long-channel damage.
208. Individual combo: pre-cast damage amp before burst.
209. Individual combo: avoid overkill, split spells if enough.
210. Individual combo: use ultimate only on high-value target.
211. Team combo: start with vision hero or summon scout.
212. Team combo: initiator calls target before blink.
213. Team combo: second stun waits half duration.
214. Team combo: burst hero commits once save is forced.
215. Team combo: save hero stays out of first reveal.
216. Team combo: kite back into cooldown re-engage.
217. Team combo: isolate enemy carry from support saves.
218. Team combo: split angle to dodge AoE control.
219. Team combo: hold one ultimate for second wave.
220. Team combo: post-fight immediately push nearest lane.
221. Movement: path through fog when missing on map.
222. Movement: avoid repeating same jungle route.
223. Movement: mirror enemy strongest hero location.
224. Movement: cut wave then retreat through visioned path.
225. Movement: use smoke to cross river safely.
226. Movement: rotate after shoving lane, not before.
227. Movement: collapse with numbers, leave with objective.
228. Movement: defend opposite side if direct defense impossible.
229. Movement: stay near towers when key spells are down.
230. Movement: shadow strongest ally when weak alone.
231. Ask every minute who can kill you right now.
232. Ask every minute where enemy vision likely is.
233. Ask every minute which lane is most valuable.
234. Ask every minute whether Roshan can be threatened.
235. Ask every minute whose buyback is available.
236. Ask every minute which cooldowns are missing.
237. Ask every minute if your farm pattern is efficient.
238. Ask every minute if you need to show on map.
239. Ask every minute if your wards are expired.
240. Ask every minute if your hero should be grouping.
241. If no enemy heroes selected, suggest comfort lane drill.
242. If no enemy heroes selected, suggest random aggression timing.
243. If no enemy heroes selected, suggest warding mini-challenge.
244. If no enemy heroes selected, suggest denies practice target.
245. If no enemy heroes selected, suggest pull timing practice.
246. If no enemy heroes selected, suggest rune control exercise.
247. If no enemy heroes selected, suggest smoke rotation practice.
248. If no enemy heroes selected, suggest stack efficiency goal.
249. If no enemy heroes selected, suggest deathless ten-minute goal.
250. If no enemy heroes selected, suggest communication callouts focus.
251. Prefer safe lane if hero scales and needs protection.
252. Prefer offlane if hero spikes early with pressure.
253. Prefer mid if hero controls runes and tempo.
254. Prefer lane with reliable support setup.
255. Prefer lane where enemy kill threat is lower.
256. Prefer lane near objective your lineup wants first.
257. Prefer lane where your spell secures range creeps.
258. Prefer lane where your hero can contest pulls.
259. Prefer lane where you can hit early item timing.
260. Prefer lane that preserves your TP reaction impact.
261. Against Bristleback, consider early magic burst itemization.
262. Against illusion heroes, build wave clear and armor.
263. Against summon heroes, prioritize AoE and attack speed.
264. Against evasion heroes, prep true strike timing.
265. Against healing cores, add vessel or anti-heal timing.
266. Against blink initiators, keep sentries and spacing.
267. Against invis supports, carry dust permanently after mid game.
268. Against long stuns, rush status resist or dispel.
269. Against mana burn, buy mana sustain and stats.
270. Against push lineups, defend catapult waves first.
271. Early game target: secure all range creeps possible.
272. Early game target: minimize deaths more than greedy farm.
273. Early game target: hit first power spike on time.
274. Early game target: rotate with first impactful rune.
275. Early game target: pressure weakest enemy lane.
276. Early game target: trade support lives for core XP if needed.
277. Early game target: force enemy support to stay defensive.
278. Early game target: deny enemy stack opportunities.
279. Early game target: ward to protect your transition farm.
280. Early game target: chip first tower with catapult.
281. Mid game target: connect cores around item timings.
282. Mid game target: force enemy reactions on side lanes.
283. Mid game target: control triangle entrances with wards.
284. Mid game target: punish isolated farming core.
285. Mid game target: secure second Roshan vision early.
286. Mid game target: avoid five-man idle grouping.
287. Mid game target: maintain two lanes pushed.
288. Mid game target: convert every smoke into map gain.
289. Mid game target: choke enemy farming area gradually.
290. Mid game target: protect your highest net worth hero.
291. Late game target: save buyback on two cores minimum.
292. Late game target: avoid random deaths without objective.
293. Late game target: pressure lanes before high ground.
294. Late game target: bait enemy glyph intentionally.
295. Late game target: force defensive TPs then reset.
296. Late game target: secure Aegis before final siege.
297. Late game target: keep one hero cutting side wave.
298. Late game target: track enemy refresher and shard powers.
299. Late game target: prioritize throne path over extra kills.
300. Late game target: discipline around buyback re-fights.
301. First skill pick should secure first two creeps.
302. First skill pick should prevent early death scenario.
303. First skill pick should threaten enemy overextension.
304. First skill pick should match bounty rune plan.
305. First skill pick can be flexible until rune clash.
306. First skill pick should account for mana cost.
307. First skill pick should not auto-commit to full build.
308. First skill pick may prioritize scouting utility.
309. First skill pick should sync with support spell.
310. First skill pick should create confidence in lane.
311. Keep disabled longest: enemy save hero in clutch fights.
312. Keep disabled longest: enemy mobile carry with escape.
313. Keep disabled longest: enemy channeling team-fight ult.
314. Keep disabled longest: enemy AoE control initiator.
315. Keep disabled longest: enemy reset healer support.
316. Keep disabled longest: enemy glass-cannon damage dealer.
317. Keep disabled longest: enemy high-ground defender with wave clear.
318. Keep disabled longest: enemy buyback threat core.
319. Keep disabled longest: enemy vision provider during smoke.
320. Keep disabled longest: enemy dispel source for your combos.
321. Take down first: exposed support with save items.
322. Take down first: overfarmed mid lacking defensive cooldown.
323. Take down first: hero holding gem in fights.
324. Take down first: hero enabling aura sustain.
325. Take down first: hero with no buyback and big impact.
326. Take down first: split-push hero before objective.
327. Take down first: lineup anchor with long cooldown ultimate.
328. Take down first: rune-controlling tempo hero.
329. Take down first: enemy who just used BKB.
330. Take down first: hero caught outside formation.
331. Target next gank: hero farming isolated dangerous lane.
332. Target next gank: hero showing without TP.
333. Target next gank: hero with revealed no-ult window.
334. Target next gank: hero finishing critical item soon.
335. Target next gank: hero with poor escape mobility.
336. Target next gank: hero defending deadlane repeatedly.
337. Target next gank: hero with large streak bounty.
338. Target next gank: hero carrying teamfight aura.
339. Target next gank: hero who de-wards alone often.
340. Target next gank: hero rotating greedily through jungle.
341. Why enemy is owning: they hit item timings uncontested.
342. Why enemy is owning: your team fed same lane repeatedly.
343. Why enemy is owning: no vision on their farm routes.
344. Why enemy is owning: no disable chained on them.
345. Why enemy is owning: their supports survive every fight.
346. Why enemy is owning: your damage type is countered.
347. Why enemy is owning: your spells overlap inefficiently.
348. Why enemy is owning: side lanes stay unpushed.
349. Why enemy is owning: objective calls are too late.
350. Why enemy is owning: buyback tracking was ignored.
351. Roshan thought: can we kill pit safely in 20 seconds.
352. Roshan thought: who tanks and who zones.
353. Roshan thought: do we have medallion or minus armor.
354. Roshan thought: are side waves pushed before start.
355. Roshan thought: where to ward before entering pit.
356. Roshan thought: who picks up Aegis and why.
357. Roshan thought: who should take shard.
358. Roshan thought: do we bait fight before finishing.
359. Roshan thought: do we have buyback to contest re-fight.
360. Roshan thought: what's next objective immediately after.
361. High ground thought: force glyph with ranged chip first.
362. High ground thought: keep buyback hero outside commitment.
363. High ground thought: identify enemy wave-clear spell cooldown.
364. High ground thought: avoid clumping on choke points.
365. High ground thought: hit buildings during BKB windows.
366. High ground thought: retreat once major cooldowns used.
367. High ground thought: prepare second lane pressure simultaneously.
368. High ground thought: keep vision behind barracks line.
369. High ground thought: kill towers before chasing fountain.
370. High ground thought: reset for second lane if resources low.
371. Defensive thought: if behind, trade farm for map vision.
372. Defensive thought: prioritize de-pushing lanes over risky fights.
373. Defensive thought: smoke out only with clear target.
374. Defensive thought: defend high ground with cooldown layering.
375. Defensive thought: avoid contesting lost Roshan without tools.
376. Defensive thought: delay game for your scaling core.
377. Defensive thought: kill enemy vision before comeback smoke.
378. Defensive thought: punish overextensions under your wards.
379. Defensive thought: keep gem on survivable hero.
380. Defensive thought: plan one decisive fight location.
381. Support thought: your death is costly before warding.
382. Support thought: carry smokes proactively, not reactively.
383. Support thought: stack whenever core farming pattern allows.
384. Support thought: prioritize ward quality over quantity.
385. Support thought: reveal only if spell cast is impactful.
386. Support thought: hide behind cores during sieges.
387. Support thought: save buyback for high-ground defense.
388. Support thought: identify which core you are enabling now.
389. Support thought: force enemy detection tax with positioning.
390. Support thought: keep dust cooldown synced with smokes.
391. Core thought: farm where next fight will happen.
392. Core thought: protect streak by avoiding unnecessary reveals.
393. Core thought: join fight only near your timing spike.
394. Core thought: push one extra wave before jungle fallback.
395. Core thought: track enemy blink timings versus your positioning.
396. Core thought: stash buyback gold after third item.
397. Core thought: swap backpack for burst or siege before fight.
398. Core thought: avoid full commit without save nearby.
399. Core thought: pressure objective after winning one duel.
400. Core thought: communicate cooldown before team commits.
401. Micro thought: cancel backswing for smoother kiting.
402. Micro thought: orb-walk to maximize distance control.
403. Micro thought: use attack-move in fog checks safely.
404. Micro thought: body block paths after slows.
405. Micro thought: turn for one spell then keep running.
406. Micro thought: fake retreat to bait overchase.
407. Micro thought: pre-place unit for scouting ramp.
408. Micro thought: animation hide cast from tree line.
409. Micro thought: cast from max range to avoid counter.
410. Micro thought: quick-cast consistency beats flashy mechanics.
411. Communication thought: call cooldowns with exact seconds.
412. Communication thought: call target name before jump.
413. Communication thought: call retreat early, not after deaths.
414. Communication thought: call ward spots after de-warding.
415. Communication thought: call missing heroes with direction.
416. Communication thought: call buyback status after each fight.
417. Communication thought: call smoke destination before using.
418. Communication thought: call lane assignments after objective.
419. Communication thought: call rune type and usage plan.
420. Communication thought: keep calls short and actionable.
421. Mental thought: one bad fight does not end game.
422. Mental thought: focus next objective, not blame.
423. Mental thought: keep camera active even while dead.
424. Mental thought: review why each death happened.
425. Mental thought: avoid autopilot farming under pressure.
426. Mental thought: play around cooldowns, not emotions.
427. Mental thought: adapt build without ego attachment.
428. Mental thought: reset breathing before deciding buyback.
429. Mental thought: keep team morale with clear plan.
430. Mental thought: value consistency over highlight plays.
431. Economy thought: spend unreliable gold before risky move.
432. Economy thought: avoid dying with large unused gold.
433. Economy thought: send components while farming route continues.
434. Economy thought: use backpack swap around cooldown fights.
435. Economy thought: buy utility if slot not impactful.
436. Economy thought: avoid duplicate selfish items on team.
437. Economy thought: smoke purchase is team gold investment.
438. Economy thought: observer wards are objective multipliers.
439. Economy thought: keep TP and detection budget reserved.
440. Economy thought: neutral token usage can swing timings.
441. Objective thought: tower before jungle camps when safe.
442. Objective thought: barracks over kills if window is short.
443. Objective thought: tormentor only if map is stable.
444. Objective thought: outposts enable faster map collapse.
445. Objective thought: lane pressure is objective insurance.
446. Objective thought: one pickoff should become structure damage.
447. Objective thought: avoid empty grouping with no objective.
448. Objective thought: fight near your vision and waves.
449. Objective thought: force reaction, then take opposite objective.
450. Objective thought: close game with discipline and buyback plan.
451. End-game review: identify your strongest 5-minute window.
452. End-game review: identify one missed objective conversion.
453. End-game review: identify one poor death position.
454. End-game review: identify one excellent smoke move.
455. End-game review: identify build adaptation that worked.
456. End-game review: identify build adaptation missed.
457. End-game review: note enemy comeback trigger.
458. End-game review: note your comeback trigger.
459. End-game review: evaluate lane choice success.
460. End-game review: evaluate first skill choice impact.
461. End-game review: evaluate first item timing accuracy.
462. End-game review: evaluate warding map for each phase.
463. End-game review: evaluate rune control effectiveness.
464. End-game review: evaluate Roshan call quality.
465. End-game review: evaluate target priority consistency.
466. End-game review: evaluate disable chain discipline.
467. End-game review: evaluate buyback usage quality.
468. End-game review: evaluate communication clarity.
469. End-game review: evaluate objective focus under pressure.
470. End-game review: choose one habit to improve next game.
471. MVP thought: be present in every major objective fight.
472. MVP thought: die less than enemy core counterparts.
473. MVP thought: translate farm into pressure, not scoreboard.
474. MVP thought: make one information call every minute.
475. MVP thought: place or enable decisive vision.
476. MVP thought: secure key runes and wisdom timings.
477. MVP thought: keep lane pushed before every smoke.
478. MVP thought: carry required utility even as core.
479. MVP thought: adapt skill build when game demands.
480. MVP thought: adapt item build before it is too late.
481. MVP thought: start fights on your terms with vision.
482. MVP thought: disengage cleanly when fight turns bad.
483. MVP thought: convert every won fight into map gain.
484. MVP thought: avoid ego chases across unwarded terrain.
485. MVP thought: force enemy to respond to your tempo.
486. MVP thought: preserve buyback before throne attempts.
487. MVP thought: keep teammates informed on your cooldowns.
488. MVP thought: protect your highest-impact teammate.
489. MVP thought: punish enemy greed immediately.
490. MVP thought: close game through objectives, not padding kills.
491. Final reminder: if unsure, play around vision advantage.
492. Final reminder: if unsure, defend waves before fighting.
493. Final reminder: if unsure, choose safer farm route.
494. Final reminder: if unsure, keep TP and detection ready.
495. Final reminder: if unsure, hold high ground discipline.
496. Final reminder: if unsure, prioritize buyback over luxury.
497. Final reminder: if unsure, target enemy save hero first.
498. Final reminder: if unsure, reset and fight with cooldowns.
499. Final reminder: if unsure, call one simple team plan.
500. Final reminder: think objective first, action second.

---

## Troubleshooting

**"No OPENAI_API_KEY found"** -- Create a `.env` file (copy from `.env.example`) and add your key. Or switch to Ollama for free local LLM.

**"Could not find Dota 2 install"** -- Run `python scripts/setup_gsi.py` and paste your Dota cfg path when prompted.

**"Vision templates missing"** -- Run `python scripts/download_assets.py` to fetch hero/item icons.

**Tips not appearing** -- Make sure Dota is in Borderless Windowed mode. Check that `python main.py` is running and Dota's GSI config is installed.

**Draft picks not detected / wrong heroes** -- Detection works best at 1080p or higher with Borderless Windowed. At 720p or below, portraits are very small and accuracy drops. Make sure `assets/templates/portraits/` has PNG files (re-run `python scripts/download_assets.py` if empty). Ultrawide monitors (21:9) may need ROI tuning.

**Overlay covers game UI** -- Drag the title bar to reposition the window, or use the gear icon to adjust width.

**Mac: screen capture is blank** -- Go to **System Settings > Privacy & Security > Screen Recording** and enable your Terminal (or Python). Restart the app after granting permission.

**Mac: `python` command not found** -- Use `python3` instead, or run `brew install python@3.13`.
