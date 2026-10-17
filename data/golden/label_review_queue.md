# Label review queue

Reviews where all 6 runs (pack off and on, three repeats each) produced the *same* labels, and those labels differ from the answer key. 32 category disagreements and 14 severity-only disagreements, out of 178 scored reviews.

**Read this as a list of labels worth re-checking against `docs/LABELING_GUIDE.md`, not as a list of mistakes.** The queue is selected by the system's own output, so it can only point at places where the system differs from you. It cannot show you labels where the system agreed with you and both were wrong. Correcting from it therefore moves the answer key towards the system by construction, which is why the results are reported against both the original and the corrected set.

To change a label, add a line to `data/golden/corrections.jsonl`. Leaving a review out means the original label stands.

## Category disagreements, grouped by your label

### Your label: `content_ux` (7 reviews)

#### `26b506b6-0d7b-4588-a547-ba0465fae46f`

*Candy Crush Saga · 3 stars · jargon*

> Love the game but its programmed to put you in your place just when you get on a win streak. I've noticed after a move, subsequent breaks yield nothing helpful...until you've used your last try, then multiple color bombs appear. There should be ways to earn more lives without paying, the time to regain a life should be shorter and getting lives from friends shouldn’t be capped. If someone wants to play your game for hours on end, why limit the play time?

- **Your label:** `content_ux` · severity `low`
- **All 6 runs said:** `difficulty_balance, monetization` · severity `medium`
- **Its reasoning:**
  - Claims the game is rigged against win streaks and that lives are limited to push payment.
  - Claims randomness is rigged and wants ways to earn lives without paying.
  - Claims rigged randomness and a life economy that pushes players to pay.

#### `c08a6c62-71ef-4445-a52a-9eaa0dbe8c7e`

*Candy Crush Saga · 5 stars*

> let me play easy game give me more life lines n new also please

- **Your label:** `content_ux` · severity `low`
- **All 6 runs said:** `difficulty_balance` · severity `low`
- **Its reasoning:**
  - Asks for an easier game and more lives; a mild suggestion.
  - Asks for easier play and more lives; unclear wording.
  - Asks for easier play and more lives, a mild economy request.

#### `74c78e6c-6986-4952-b9fc-df2aeb9fe2d9`

*Clash of Clans · 4 stars*

> there's a bug where you can't copy the other players base. When you clickcopy, and even though nothing is on the obstacle the buildings isn't place

- **Your label:** `content_ux` · severity `low`
- **All 6 runs said:** `stability_performance` · severity `low`
- **Its reasoning:**
  - Reports a bug where copied bases do not place buildings.
  - Reports a bug where copying a base does not place buildings, a minor functional fault.
  - Reports a bug where copying another player's base does not place buildings.

#### `7bc1375e-f173-406a-8625-634da23f6050`

*Clash of Clans · 1 stars · jargon*

> why use my internet more , i plaed this game before 9 years and i have level 15th townhall base. but today i notice this that use my data so more . why please give me solution .

- **Your label:** `content_ux` · severity `low`
- **All 6 runs said:** `stability_performance` · severity `medium`
- **Its reasoning:**
  - Complains of unusually high mobile data usage.
  - Complains of excessive mobile data usage, a resource complaint.
  - Complains the game suddenly uses much more mobile data.

#### `b5fc7adf-6770-4e35-85b4-dc89afb9b7e6`

*Clash of Clans · 4 stars*

> Although it's good but it's just the upgrade time it's too consuming

- **Your label:** `content_ux` · severity `low`
- **All 6 runs said:** `difficulty_balance` · severity `low, medium`
- **Its reasoning:**
  - Upgrade timers are too long, a progression grind complaint.
  - Upgrade timers feel too long, a mild grind remark.
  - Upgrade times feel too long, mildly stated.

#### `dfc9a6ab-8590-4114-aa28-4867a8242b19`

*Clash of Clans · 5 stars*

> Good game The building and upgrades take a little time but overall its a good game Free from adds!!

- **Your label:** `content_ux` · severity `low`
- **All 6 runs said:** `difficulty_balance` · severity `low`
- **Its reasoning:**
  - Mild remark that building and upgrades take time, otherwise positive.
  - Mild note that build and upgrade timers take a while, otherwise positive.
  - Mild note that builds and upgrades take time, otherwise positive.

#### `f16d89bc-7f39-4a17-8fad-1bb9e0423a4f`

*Clash of Clans · 1 stars · jargon*

> as a avid player of near 12 years, and clan owner for 10 years, it's always been a 5 star game imo. always progressive in updates. recruitment is near on impossible. but for me this last tournament league system update has killed it for myself and many many players. I've already found myself not feeling any enthusiasm to log in now. speaking to many other max account players they have also lost the love for the game, and small clans are struggling even more with people dropping out

- **Your label:** `content_ux` · severity `medium`
- **All 6 runs said:** `difficulty_balance` · severity `medium`
- **Its reasoning:**
  - League system update has driven players and clan members away.
  - The new league system update is said to be driving players and small clans away.
  - New tournament league system has killed enthusiasm for players and small clans.

### Your label: `other_issue` (5 reviews)

#### `1bbcd164-300c-4b0f-9a59-7d9d8bc12f1c`

*Candy Crush Saga · 5 stars*

> Lots of fun,has a few glitches which should be fixed. Especially bonus points!!

- **Your label:** `other_issue` · severity `low`
- **All 6 runs said:** `stability_performance` · severity `low`
- **Its reasoning:**
  - Mentions a few glitches around bonus points, minor and not blocking.
  - Mentions a few glitches with bonus points, minor and non-blocking.
  - Mentions a few glitches with bonus points, minor and not blocking play.

#### `a8aa727f-0b08-444e-8979-429243705659`

*Candy Crush Saga · 1 stars*

> It's a good game, time wasted for no reason sometimes, frustration comes when you've got just one move left but ten more bubbles to pop..

- **Your label:** `other_issue` · severity `low`
- **All 6 runs said:** `difficulty_balance` · severity `low`
- **Its reasoning:**
  - Frustration at running out of moves just short of the goal; mild.
  - Mild frustration at running out of moves just short of the goal.
  - Frustration at running out of moves with too much left to clear.

#### `456890f9-6c42-468f-a1cb-8fbabbf2e864`

*Clash of Clans · 5 stars*

> Its good with the battles but this game needs the mini peka

- **Your label:** `other_issue` · severity `low`
- **All 6 runs said:** `content_ux` · severity `low`
- **Its reasoning:**
  - Requests a new troop.
  - Requests a mini P.E.K.K.A. troop.
  - Requests a specific troop be added.

#### `c4a7b405-4dff-4910-8f70-5d8f369f3745`

*Clash of Clans · 4 stars*

> dear supercell team.. I had requested for my account deletion but I don't have any supercell ID...after the grace period for getting back account,it still shows that account would be deleted soon since more than 5 days...how much time would it take to restart the game?

- **Your label:** `other_issue` · severity `low`
- **All 6 runs said:** `account_progress_loss` · severity `high`
- **Its reasoning:**
  - Account deletion stuck and they cannot get the account back.
  - Account stuck in pending deletion with no way to recover it.
  - Account stuck in deletion with no Supercell ID and no way to restore access.

#### `e13ab2f6-f6eb-442d-b3dc-b95356c860cc`

*Clash of Clans · 5 stars · jargon*

> this is not good game because my account in gone TH 15😑😔

- **Your label:** `other_issue` · severity `low`
- **All 6 runs said:** `account_progress_loss` · severity `high`
- **Its reasoning:**
  - Says their account is gone.
  - Player says their Town Hall 15 account is gone.
  - Player says their account is gone, a loss of the account and progress.

### Your label: `difficulty_balance` (3 reviews)

#### `2f4b6e4b-119d-4e34-8f79-0f39269583f9`

*Candy Crush Saga · 2 stars*

> honestly i enjoyed this game a lot but after some levels it was forcing me to spend money on this game. it is no problem if the game can be won after some trails it deafantly requires some extra moves how many times you try no use it's not possible so i just Uninstalled it and playing clash of clans because it can be played free and the progress not only solely relied on spending money.

- **Your label:** `difficulty_balance` · severity `medium`
- **All 6 runs said:** `difficulty_balance, monetization` · severity `medium`
- **Its reasoning:**
  - Levels unwinnable without extra moves, feels forced to spend money.
  - Levels need spending to pass, so the player quit.
  - Levels cannot be won without extra moves and the game forces spending.

#### `fa74e698-b979-4ab1-8c0a-83b94c3ccbb6`

*Clash of Clans · 1 stars*

> Gameplay getting worst. Stupid rules cannot revenge after 24 hours. At least make it 72 hours. Direct army go east go west except to where you want it to go

- **Your label:** `difficulty_balance` · severity `medium`
- **All 6 runs said:** `content_ux` · severity `low`
- **Its reasoning:**
  - Dislikes the 24-hour revenge limit and wants it longer, plus a complaint about army pathing.
  - Dislikes the 24-hour revenge limit and army pathing; a rule/feature complaint that blocks nothing.
  - Complains about the 24-hour revenge limit and army pathing, a rules/feature preference.

#### `fcfc0c4a-0ddd-4c3e-8bd6-0f70eb1e736a`

*Clash of Clans · 1 stars · jargon*

> As a returning player, I was contemplating purchasing the gold pass next season. NO WAY after the newly announced changes. Upgrade times take so long in this game. I would only purchase the gold pass if I get immediate, tangible benefits.

- **Your label:** `difficulty_balance` · severity `medium`
- **All 6 runs said:** `difficulty_balance, monetization` · severity `medium`
- **Its reasoning:**
  - Refuses Gold Pass after announced changes and complains of long upgrade times.
  - Will not buy the gold pass after announced changes and finds upgrade times too long.
  - Won't buy Gold Pass after changes, and upgrade times are too long.

### Your label: `monetization` (3 reviews)

#### `0a5a4571-6e3a-4d0b-ab69-3cfba6f4cad0`

*Candy Crush Saga · 1 stars*

> not getting adds and extra rewards by watching adds. all other candy crush saga users are having this features.

- **Your label:** `monetization` · severity `high`
- **All 6 runs said:** `ads` · severity `medium`
- **Its reasoning:**
  - Ads and ad rewards are not appearing for this player.
  - Ads and ad rewards are not being offered or granted.
  - Ads and ad rewards are not available to this player.

#### `f2000f93-eeb7-4869-94fb-3214bc07b1e5`

*Candy Crush Saga · 1 stars*

> now we even need to watch a certain amount of ads before being able to unlock the ads that gives you more moves? the type of greed they talk about in the Bible

- **Your label:** `monetization` · severity `medium`
- **All 6 runs said:** `ads` · severity `medium`
- **Its reasoning:**
  - Must watch several ads before unlocking an ad for extra moves, an ad-gating complaint.
  - Must watch several ads before unlocking the extra-moves ad, ad-gating annoyance.
  - Must watch many ads before unlocking the ad that gives more moves.

#### `5457380d-fbaf-42a8-9e14-1887f051159f`

*Clash of Clans · 4 stars*

> great game but it needs to give more freedom to build and upgrade to speed up a players experience without wanting cash for it

- **Your label:** `monetization` · severity `low`
- **All 6 runs said:** `difficulty_balance, monetization` · severity `medium`
- **Its reasoning:**
  - Wants faster build and upgrade progression without having to pay cash.
  - Wants faster build/upgrade progress without having to pay cash.
  - Wants faster build/upgrade progress without needing to pay cash.

### Your label: `stability_performance` (3 reviews)

#### `69b0753c-2c90-4eb9-9f63-66840542efbb`

*Candy Crush Saga · 1 stars · jargon*

> I am so disappointed in this game. It keeps crashing and I have lost 10 gold bars in the process😟

- **Your label:** `stability_performance` · severity `high`
- **All 6 runs said:** `account_progress_loss, stability_performance` · severity `high`
- **Its reasoning:**
  - Crashes repeatedly cost owned gold bars.
  - Crashes repeatedly and cost the player 10 gold bars they owned.
  - Repeated crashes cost the player owned gold bars.

#### `fe607934-362e-4526-be6b-015adf4c676c`

*Candy Crush Saga · 3 stars*

> Great stress reliever All kinds of goodies you get for free yaaaaa thank you fun time the game keeps freezing i keep losing all my goodies grrrr

- **Your label:** `stability_performance` · severity `medium`
- **All 6 runs said:** `account_progress_loss, stability_performance` · severity `high`
- **Its reasoning:**
  - Game keeps freezing and the player repeatedly loses owned items.
  - Game keeps freezing and repeatedly loses owned items.
  - Game keeps freezing and the player repeatedly loses owned goodies.

#### `a2bf4c59-744b-4aba-a1d8-ff8e4bd9c110`

*Clash of Clans · 4 stars · jargon*

> Some problems occurred. When I load village with mail code, I did not received any supercell code in my mail. Plz fix the issue.

- **Your label:** `stability_performance` · severity `high`
- **All 6 runs said:** `account_progress_loss` · severity `high`
- **Its reasoning:**
  - Account recovery code email never arrives, blocking access.
  - Cannot load their village because the verification code email never arrives.
  - Cannot load village because the Supercell code email never arrives.

### Your label: `account_progress_loss` (2 reviews)

#### `7578a5fe-723e-43d8-abd9-11fd15267d2f`

*Clash of Clans · 4 stars · jargon*

> This game is very good and I like this game very much but developers need to fix a thing in builder battles , sometimes I gets 10-20 builder points but still my builder battles points get less and also my rank gets lower in builder battles , why ?

- **Your label:** `account_progress_loss` · severity `high`
- **All 6 runs said:** `difficulty_balance` · severity `medium`
- **Its reasoning:**
  - Builder battles points and rank drop despite earning points, feels unfair.
  - Ranking in builder battles drops despite earning points, which seems unfair or broken.
  - Builder battle points and rank drop despite earning points, seems unfair or buggy.

#### `d07dc0c7-8223-4754-a3eb-423cc1f31a2d`

*Clash of Clans · 1 stars*

> i cant join my clan back since it is not family friendly and in my Google account im already 21 year old

- **Your label:** `account_progress_loss` · severity `high`
- **All 6 runs said:** `content_ux` · severity `high, medium`
- **Its reasoning:**
  - Blocked from rejoining their clan by an apparently wrong age restriction.
  - Wrongly age-restricted, cannot rejoin their clan and no remedy.
  - Blocked from rejoining their clan by an age/family-friendly restriction despite being 21.

### Your label: `content_ux, difficulty_balance` (2 reviews)

#### `ce8bb37b-8362-48f7-82f0-26a3d2f41dda`

*Candy Crush Saga · 1 stars · jargon*

> the game won't let me advance in the next level anymore despite many attemps so i'm unistalling the app. you should just let your players watch ads as many as they want to gain lives, boosters, gold bars etc. you earn money from players watching ads and the players get to finish the game and advance to the next level win-win. 24 to 18 chances vs 90 things to clear is not fun play with tbh.

- **Your label:** `content_ux, difficulty_balance` · severity `low`
- **All 6 runs said:** `difficulty_balance` · severity `high, medium`
- **Its reasoning:**
  - Cannot advance despite many attempts and is uninstalling.
  - Cannot pass a level with too few moves for the goal, uninstalling.
  - Cannot advance past a level despite many attempts and is uninstalling.

#### `4f71693b-c384-4824-beb6-0210166f0817`

*Clash of Clans · 3 stars · jargon*

> The loot on builder base is way too low. At builder base 5 and it takes 4 to 5 battles just to get enough gold to upgrade ONE wall. And you need to upgrade 100. So if we assume 15 minutes per wall, that's 1500 minutes (25 hours) of battles just to max walls from level 4 to 5. It is such a soul destroying grind for nothing. Up the rewards, elixir is so easy to farm, gold is basically impossible. Like it should be 165,000 for 6 star at BH5, and then the star bonus should be 450,000.

- **Your label:** `content_ux, difficulty_balance` · severity `medium`
- **All 6 runs said:** `difficulty_balance` · severity `medium`
- **Its reasoning:**
  - Builder base gold rewards too low, heavy grind.
  - Builder base loot too low, heavy grind to upgrade walls.
  - Builder Base gold rewards too low, making wall upgrades a huge grind.

### Your label: `difficulty_balance, monetization` (2 reviews)

#### `5c57a05f-cae4-4672-9cc8-9d08228dc80c`

*Candy Crush Saga · 5 stars*

> the game is a awesome game but it needs more moves on harder levels and we need more lives and hints that can be for free or like friends that can give hints

- **Your label:** `difficulty_balance, monetization` · severity `low`
- **All 6 runs said:** `difficulty_balance` · severity `low`
- **Its reasoning:**
  - Polite request for more moves on harder levels and more free lives and hints.
  - Polite suggestion for more moves, lives and free hints.
  - Polite suggestion for more moves on harder levels and more free lives and hints.

#### `13a277d5-3408-4c3b-8606-b41dd753feb2`

*Clash of Clans · 1 stars · jargon*

> The gold pass changes that have recently been announced is such an L move from Supercell. Players have been requesting for an ore converter helper for a long time, and when the devs finally add it, they lock it behind a paywall. And what's funnier is that you can only unlock it after 20 days into the gold pass. In addition, now you have to wait for almost 2 week as opposed to just 7 days in order to get the 20% builder and lab bonuses, which are the main reasons why players buy the gold pass. L

- **Your label:** `difficulty_balance, monetization` · severity `medium`
- **All 6 runs said:** `monetization` · severity `medium`
- **Its reasoning:**
  - Complains a helper is paywalled and gold pass bonus wait lengthened.
  - Complains a long-requested helper is paywalled and gold pass bonuses delayed.
  - Helper paywalled behind gold pass and longer wait for bonuses.

### Your label: `no_issue` (2 reviews)

#### `a7835bda-9fab-4790-8a72-fd3157b660d4`

*Clash of Clans · 5 stars · jargon*

> Clash of Clans: The Quick Take ​The Vibe: The ultimate "marathon" strategy game. It’s about patience, precision, and community rather than quick reflexes. ​The Best Part: Competitive Clan Wars and the deep strategy involved in "3-starring" a base. It’s incredibly satisfying when a plan comes together. ​The Grind: Upgrade times at high Town Halls (2 weeks+) can be brutal. It’s a game of years, not days. ​

- **Your label:** `no_issue`
- **All 6 runs said:** `difficulty_balance` · severity `low`
- **Its reasoning:**
  - Mostly praise but notes long upgrade times as brutal grind.
  - Mostly praise but notes brutal multi-week upgrade timers as a grind.
  - Praise with a mild remark that upgrade times are brutally long.

#### `fd82cbde-69b5-4b23-b50d-6d380e0f49f6`

*Clash of Clans · 5 stars · jargon*

> Great. everything running smoothly. what I want is that builder village also have clan wars.

- **Your label:** `no_issue`
- **All 6 runs said:** `content_ux` · severity `low`
- **Its reasoning:**
  - Feature request for clan wars in builder village.
  - Feature request for clan wars in the Builder Base.
  - Feature request for clan wars in the builder village.

### Your label: `ads, content_ux` (1 reviews)

#### `50c061b6-3199-4411-90cf-e3f4629c72f3`

*Candy Crush Saga · 2 stars*

> This game is getting rediculous day ny day. Been playing since 2013,what's up with the latest glitch?? You make us watch tons adds to win in extra moves and boosters and after watch all those lengthy adds there's no booster to collect. Could you please fix it? Thanks

- **Your label:** `ads, content_ux` · severity `medium`
- **All 6 runs said:** `ads` · severity `medium`
- **Its reasoning:**
  - Ad reward (booster) not granted after watching long ads.
  - Many long ads and the booster reward is not granted.
  - Many lengthy ads watched and the booster reward is not granted.

### Your label: `content_ux, monetization` (1 reviews)

#### `07559dec-f267-4a28-bb9b-91c6ff567657`

*Clash of Clans · 1 stars · jargon*

> Ore economy needs to be buffed. What good is having all of these niche equipment if it isn't worth the investment of ores?? Not everyone is a equipment release day 1 player. Update: they changed the paid battle pass to include an ore exchange helper, only available if you pay. They also made it so that the rewards are worse for both the paid and free pass. The writing is on the wall when these are the same developers of Clash Royale lmfao.

- **Your label:** `content_ux, monetization` · severity `medium`
- **All 6 runs said:** `difficulty_balance, monetization` · severity `medium`
- **Its reasoning:**
  - Complains the ore economy is poor and that a helper was put behind the paid pass.
  - Complains the ore economy is poor and that a helper plus better rewards are now behind the paid pass.
  - Complains the ore economy is poor and that a pay-only exchange helper was added while pass rewards got worse.

### Your label: `content_ux, stability_performance` (1 reviews)

#### `9104c395-896f-4086-a639-f5199b7e1b9b`

*Clash of Clans · 4 stars*

> I do enjoy this game more on pc than mobile but there are a lot of optimation issues. There need to be more troop hotkey slots, 10 is simply not enough. The cursor needs an outline, even the large version blends in with the army sometimes. There should be an option for double deployment bar just like on tablet. Also direct links for clash of clans does not work on pc.

- **Your label:** `content_ux, stability_performance` · severity `high`
- **All 6 runs said:** `content_ux` · severity `low`
- **Its reasoning:**
  - PC feature and UI requests, such as more hotkeys and a cursor outline.
  - PC feature and UI requests: more hotkeys, cursor outline, deployment bar, working direct links.
  - Requests PC options: more hotkeys, cursor outline, double deployment bar, working direct links.

## Severity-only disagreements

Categories match; only the severity differs.

### Your severity: `low` (6 reviews)

#### `5b0bb8d8-ed1b-478c-927a-e8f181bc342e`

*Candy Crush Saga · 3 stars · jargon*

> 17/2/2026 one of the disgusting event going on 23 moves and 105 wooden block i stuck from 6 days in 1 level 17810

- **Your label:** `difficulty_balance` · severity `low`
- **All 6 runs said:** `difficulty_balance` · severity `high`
- **Its reasoning:**
  - Stuck on one level for 6 days.
  - Stuck on one level for six days, progression blocked.
  - Stuck six days on one level with too few moves and many blockers.

#### `bc63101c-2b49-4318-9b7c-e6376ddef7a0`

*Candy Crush Saga · 1 stars*

> why does the game mute my podcast player? i don't want to listen to the game music, i want to listen to podcasts. whenever a level starts, podcasts mutes. all gane sounds are muted

- **Your label:** `content_ux` · severity `low`
- **All 6 runs said:** `content_ux` · severity `medium`
- **Its reasoning:**
  - Game mutes the player's podcast app, affecting the device outside the game.
  - Game mutes the player's podcast app, interfering with the device beyond the game.
  - Game mutes the player's podcast app, affecting the device beyond the game.

#### `c7ece634-642a-455d-ad44-1a786e727b50`

*Candy Crush Saga · 1 stars*

> This game is not about reducing traces, but is simply about extorting money from players.

- **Your label:** `monetization` · severity `low`
- **All 6 runs said:** `monetization` · severity `medium`
- **Its reasoning:**
  - Cash-grab accusation.
  - Accuses the game of extorting money from players.
  - Says the game is about extorting money from players.

#### `d48764cc-198a-41f9-b965-e52d3c724600`

*Candy Crush Saga · 4 stars*

> good but is pay to win like golds is bad thing but you can delete the pay to win

- **Your label:** `monetization` · severity `low`
- **All 6 runs said:** `monetization` · severity `medium`
- **Its reasoning:**
  - Calls the game pay to win because of golds.
  - Calls the game pay to win because of gold and wants that removed.
  - Calls the game pay to win because of gold bars and asks for it to be removed.

#### `6b44b8d9-af45-4fd1-b41c-7751d19f5216`

*Clash of Clans · 1 stars · jargon*

> Upcoming changes to the "Gold Pass" signaling the end for free to play players sadly. Stay away unless things change.

- **Your label:** `monetization` · severity `low`
- **All 6 runs said:** `monetization` · severity `medium`
- **Its reasoning:**
  - Upcoming Gold Pass changes seen as hurting free players.
  - Upcoming Gold Pass changes are seen as hurting free-to-play players.
  - Complains announced Gold Pass changes hurt free-to-play players.

#### `a5b13ac9-e9d6-4ed2-baab-b1de6f8fb705`

*Clash of Clans · 2 stars*

> This game is dangerous due to its addicting nature. This game is so time consuming and so frustrating that despite liking it I hate it more. This game needs to lower its time consumption in order to create a fair gameplay experience. Everything based on improvements takes days of time for a little improvement. The amount of time it takes in the early stage is unbearable.Other than that, school going kids and students are gonna get constant distractions from education.Fix this brain rot game.

- **Your label:** `difficulty_balance` · severity `low`
- **All 6 runs said:** `difficulty_balance` · severity `medium`
- **Its reasoning:**
  - Upgrades take days and early game time cost is unbearable; grind complaint.
  - Upgrade timers take days and are called unbearable early on; grind complaint.
  - Upgrade timers and early-game time cost described as unbearable grind.

### Your severity: `medium` (6 reviews)

#### `36749b68-20e0-4f71-8ec8-bc86e45d287b`

*Candy Crush Saga · 2 stars*

> frustrating when you watch ads for awards and then get redirected to Amazon and can't get out and don't get reward. lose all if it is part of a package.

- **Your label:** `ads` · severity `medium`
- **All 6 runs said:** `ads` · severity `high`
- **Its reasoning:**
  - Ad redirects to Amazon with no way out and no reward, player is stuck.
  - Ad redirects to Amazon, player cannot get out and loses the reward; the game is stuck.
  - Ad redirects to Amazon, cannot exit and reward is lost, breaking the game flow.

#### `6198054b-b3ba-420b-92d6-7574c712dad1`

*Candy Crush Saga · 1 stars · jargon*

> I love this game, I love playing it, it's challenging and everything else but I CAN'T STAND it telling me what to do! I HATE the flashing candies to show you a move! I've been playing this game 10 years and spend quiet a bit of money but I'm about to quit playing just because of those damn flashing candies!!! SERIOUSLY!!!

- **Your label:** `content_ux` · severity `medium`
- **All 6 runs said:** `content_ux` · severity `low`
- **Its reasoning:**
  - Dislikes the flashing hint candies and wants them off; a UI preference.
  - Dislikes the flashing hint candies and wants them off, a UI preference.
  - Dislikes flashing candy move hints with no way to turn them off.

#### `1e6e58b1-6c16-4871-b198-882d0924f78d`

*Clash of Clans · 2 stars · jargon*

> This game use to rule our generation but now supercell has made it super boaring by removing trophies, removing waiting time for armies, conversion of gold to elixir and vice versa. Coc before lockdown was OG. 😞

- **Your label:** `content_ux` · severity `medium`
- **All 6 runs said:** `content_ux` · severity `low`
- **Its reasoning:**
  - Dislikes removed features such as trophies, army waiting time and resource conversion.
  - Unhappy about removed or changed features that made the game boring.
  - Unhappy about removed features and changes.

#### `8a91f24a-85b9-49d5-83e4-08975408d21e`

*Clash of Clans · 4 stars · jargon*

> clash of clans is my favourite game because it is a creative game but I give it four stars because of the time of building when I upgrade buildings.

- **Your label:** `difficulty_balance` · severity `medium`
- **All 6 runs said:** `difficulty_balance` · severity `low`
- **Its reasoning:**
  - Loses a star over long building upgrade times.
  - Took a star off for long building upgrade times.
  - Mild complaint about building upgrade time.

#### `8ac09b04-67cc-42b1-a8e7-6302d208afe8`

*Clash of Clans · 1 stars · jargon*

> I hate the new update. You can’t trophy push anymore, and the new revenge system sucks. You only have 12 hours to attack back, unlike the old system where you could take your time and attack whenever you wanted. On top of that, the new attacking system is terrible. When you’re attacking, it brings you back to the barracks to check your troops before letting you attack again. It’s annoying and a complete waste of time.

- **Your label:** `content_ux` · severity `medium`
- **All 6 runs said:** `content_ux` · severity `low`
- **Its reasoning:**
  - Dislikes new revenge time limit and extra step before attacking.
  - Dislikes the changed revenge window and attack flow introduced by the update.
  - Dislikes new revenge time limit and extra barracks step before attacking.

#### `de0a97a1-0305-4b17-b0e0-7cd408aa9e75`

*Clash of Clans · 2 stars · jargon*

> I love the old version of coc the league and a normal attack sytem in town hall but they make the town hall into base hall and now I am leaving this, I will back when the old version coc will back .

- **Your label:** `content_ux` · severity `medium`
- **All 6 runs said:** `content_ux` · severity `low`
- **Its reasoning:**
  - Dislikes changes to the league and attack system and wants the old version back.
  - Dislikes changed attack system and renamed content, wants old version back.
  - Dislikes removed old league and attack system, wants old version back.

### Your severity: `high` (2 reviews)

#### `6f583892-aa38-4ed4-ad5c-2b3d7c680963`

*Candy Crush Saga · 3 stars*

> Even though I win the game I am bounced out of the challenge

- **Your label:** `stability_performance` · severity `high`
- **All 6 runs said:** `stability_performance` · severity `medium`
- **Its reasoning:**
  - Player is kicked out of a challenge despite winning, a session fault.
  - Player is ejected from a challenge despite winning, a functional fault.
  - Player is kicked out of the challenge despite winning, which looks like a fault.

#### `b628bd09-e795-4a85-9321-d1ed38b767f6`

*Clash of Clans · 2 stars · jargon*

> I have been playing this game for a long time. There's a problem that is literally the worst. Switching from one network to another the game will pop up "try again" no matter what important task you're doing, it doesn't care about cwl or rank attacks or even loot attacks or even common war attacks, it literally does its usual pop up stuff. I hope you are the developers that will fix it immediately. When it's not a problem for other online games then why for this??

- **Your label:** `stability_performance` · severity `high`
- **All 6 runs said:** `stability_performance` · severity `medium`
- **Its reasoning:**
  - Network switch triggers a try-again popup that interrupts attacks.
  - Network switch triggers a try-again popup, interrupting important attacks.
  - Network switching triggers a 'try again' popup that interrupts attacks.

