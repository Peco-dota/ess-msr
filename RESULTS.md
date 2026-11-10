# Výsledky RQ1, RQ2 a RQ3 (P1 = AIDev, 2025)

## Kde je čo

| Čo | Kde |
|---|---|
| Návrh štúdie (RQ1–RQ4) | `../project-details.md` |
| Definície pravidiel a labelov | `rules.md` |
| RQ1 pipeline + výsledky | `src/ess_msr/fetch_data.ipynb` (sekcie 1–9) |
| RQ2 analýza | `src/ess_msr/rq2.ipynb` (reuse RQ1 pipeline, sekcie 1–8) |
| RQ3 analýza | `src/ess_msr/rq3.ipynb` (reuse RQ1 pipeline, sekcie 1–7) |
| Ručná kontrola package-manager porušení | `package_manager_violations.csv` (23 riadkov, vyplnené `correct` + `note`) |
| Ručná validácia 100 párov (PR, pravidlo) | `validation_sample.csv` (`rule_correct`, `label_correct`, `note`) |
| Overenie opravených checkerov (30 nových porušení) | `validation_sample_v2.csv` (`label_final` = label finálneho checkera) |
| Dáta GHAgentFiles | `instruction-data/` (AIDev sa ťahá z Hugging Face) |

## Dáta

- 71 677 agent PR v AIDev v4
- 23 422 PR v 1 326 repo malo v čase otvorenia context file (AGENTS.md, CLAUDE.md, ...)
- 590 z nich nemá info o zmenených súboroch, preto ich vynechávame

## Pravidlá, ktoré kontrolujeme (s príkladmi)

Každému páru (PR, pravidlo) priradíme label `complied`, `violated` alebo `not_applicable`. Kontrolujeme iba pravidlá, ktoré naozaj stoja v context file platnom v čase otvorenia PR.

### Changelog

`CHANGELOG.md` je súbor v repe, do ktorého sa pri každej zmene zapíše riadok typu „pridané X, opravené Y“. Používatelia v ňom vidia, čo sa medzi verziami zmenilo.

Takto to znie v AGENTS.md / CLAUDE.md (reálne citáty z dát):
> - Update `CHANGELOG.md` with changes
> - **Update CHANGELOG.md** under "Unreleased" section
> - Whenever you add a new feature, please also add a new line into `CHANGELOG.md`.

Ako to kontrolujeme:
- Pravidlo sa uplatní iba na PR, ktoré zmenili zdrojový kód (`.py`, `.ts`, `.java`, ...). PR, ktoré menia len dokumentáciu, dostanú `not_applicable`.
- Pravidlo sa musí týkať daného PR (rozsah pravidla, pozri `rules.md`):
  - riadky v sekcii o release/publish, podmienené riadky („if applicable“, „if the user asks“) a odkazy na `/changelog/` stránky za pravidlo nepovažujeme;
  - druh PR určíme z titulku (`feat`/Add… = feature, `fix`/Fix… = fix, docs, iné). Pravidlo „pre nové funkcie“ alebo „pre významné zmeny“ sa uplatní len na feature PR, pri zmienke o bugoch aj na fix PR. Docs-only PR sú `not_applicable`;
  - pravidlo pre konkrétny jazyk („unit tests for new Python functions“) sa uplatní len ak PR mení súbory toho jazyka.
  - pravidlo „whenever `foo.py` is modified“ sa uplatní len ak sa `foo.py` zmenil.
- `complied` = PR zmenil aj changelog (`CHANGELOG.md`, `docs/changelog/...`, `.changeset/*.md`, alebo `README.md`, ak pravidlo hovorí, že changelog je tam).
- `violated` = PR zmenil kód, ale changelog nie.

Príklad:
| PR zmenil | Label |
|---|---|
| `src/api.ts`, `CHANGELOG.md` | complied |
| `src/api.ts` | violated |
| `README.md` | not_applicable |

### Required tests

Pravidlo, že nový alebo zmenený kód má mať aj testy.

Takto to znie v context file (reálne citáty):
> - Always add tests for new functionality
> - Please follow the existing code style and include tests for any new functionality.
> - ALWAYS write tests when creating a new component

Ako to kontrolujeme:
- Uplatní sa iba na PR, ktoré zmenili zdrojový kód.
- Pravidlo sa musí týkať daného PR (rozsah pravidla, pozri `rules.md`):
  - riadky v sekcii o release/publish, podmienené riadky („if applicable“, „if the user asks“) a odkazy na `/changelog/` stránky za pravidlo nepovažujeme;
  - druh PR určíme z titulku (`feat`/Add… = feature, `fix`/Fix… = fix, docs, iné). Pravidlo „pre nové funkcie“ alebo „pre významné zmeny“ sa uplatní len na feature PR, pri zmienke o bugoch aj na fix PR. Docs-only PR sú `not_applicable`;
  - pravidlo pre konkrétny jazyk („unit tests for new Python functions“) sa uplatní len ak PR mení súbory toho jazyka.
- `complied` = PR zmenil aj aspoň jeden testový súbor (`tests/...`, `test_foo.py`, `foo_test.go`, `foo.test.ts`, `FooTest.java`, `Foo_Tests.cs`, `Foo.UnitTests/...`; lockfile v testovom priečinku sa nepočíta).
- `violated` = PR zmenil kód a nezmenil žiadny test.

Príklad:
| PR zmenil | Label |
|---|---|
| `src/app.py`, `tests/test_app.py` | complied |
| `pkg/parser.go` | violated |
| `docs/guide.md` | not_applicable |

### Commit format (Conventional Commits)

Konvencia pre názvy commitov a PR v tvare `typ(scope): popis`, napr. `feat: add login` alebo `fix(api): handle null`. Podľa prefixu sa dá automaticky generovať changelog a určovať verzie.

Takto to znie v context file (reálne citáty):
> - Use Conventional Commits: `type(scope): description` in imperative mood, ≤72 characters, no trailing period.
> - **CRITICAL**: All PR titles must follow [Conventional Commits](https://www.conventionalcommits.org/) format to pass CI validation.
> - For all commit messages use conventional commits

Pozeráme sa na PR title a na prvý riadok každého commit message v PR.

Ako to kontrolujeme:
- Pravidlo sa uplatní na každý PR, lebo každý PR má title. `not_applicable` tu teda nevzniká.
- Text musí mať tvar `slovo(scope voliteľný)!voliteľný: popis` (regex `^[\w,-]+(\(.+\))?!?: .+`, na veľkosti písmen nezáleží).
- Ako typ berieme ľubovoľné slovo, nielen `feat`/`fix`/..., pretože repá si pridávajú vlastné typy (napr. `k8s:`).
- Úvodný tag v hranatých zátvorkách a úvodné emoji ignorujeme, takže `[alpha_factory] feat: ...` aj `🐛 fix: ...` (emoji conventional commits) prejdú.
- `complied` = sedí title alebo aspoň jeden commit (benevolentné).
- `violated` = nesedí title ani žiadny commit.

Príklad:
| PR title | Commity | Label |
|---|---|---|
| `feat: add video tips` | – | complied |
| `[alpha_factory] add x` | `feat: add x` | complied (sedí commit) |
| `Add sidebar` | `Initial plan` | violated |
| `Pull request for issue #324` | `Update app.js` | violated |

### Package manager

Pravidlo, ktorý nástroj sa má používať na závislosti, napr. `pnpm` namiesto `npm` alebo `uv` namiesto `pip`. Každý manager si vedie vlastný lockfile a podľa neho vidíme, ktorý manager agent naozaj použil.

Takto to znie v context file (reálne citáty):
> - Use `pnpm add` instead of `npm install <package>`
> - **Package Manager**: Use Yarn exclusively (configured in .yarnrc.yml)
> - When suggesting dependency management, use `uv sync` instead of `pip install -r requirements.txt`

Pozeráme sa na zmenené a novo pridané lockfiles v PR.

| Lockfile | Manager | Ekosystém |
|---|---|---|
| `package-lock.json` | npm | JS |
| `pnpm-lock.yaml` | pnpm | JS |
| `yarn.lock` | yarn | JS |
| `bun.lock`, `bun.lockb` | bun | JS |
| `uv.lock` | uv | Python |
| `poetry.lock` | poetry | Python |

Ako to kontrolujeme:
1. Z context file vyčítame požadovaný manager (napr. `pnpm`) a z neho ekosystém (JS).
2. Berieme do úvahy iba lockfiles z toho istého ekosystému. Lockfiles v priečinkoch `test/`, `fixtures/` a `examples/` ignorujeme, lebo ide o ukážkové projekty.
3. `violated` = PR pridal nový lockfile iného managera (napr. nový `package-lock.json` v pnpm repe).
4. `complied` = PR menil iba lockfiles požadovaného managera (napr. iba `pnpm-lock.yaml`).
5. `not_applicable` = PR nemenil žiadny relevantný lockfile. Týka sa to väčšiny PR (1 712 z 1 979).

Úpravu už existujúceho „cudzieho“ lockfilu za porušenie nepovažujeme, lebo niektoré podbalíky legitímne používajú iný manager.

Príklad (repo vyžaduje pnpm):
| PR zmenil | Label |
|---|---|
| `pnpm-lock.yaml` (upravený) | complied |
| `package-lock.json` (nový súbor) | violated |
| `examples/demo/package-lock.json` (nový) | not_applicable (ignorovaný priečinok) |
| `src/index.ts` | not_applicable |

### Na čo dať pozor pri prezentácii

- Checkery sú zámerne benevolentné. Radšej prehliadneme porušenie, než by sme si nejaké vymysleli.
- Changelog a testy: druh PR odhadujeme len z titulku, takže časť PR skončí ako `not_applicable` aj keď pravidlo platilo (napr. „Update docs…“ PR, ktorý mení aj kód). Po oprave checkerov je precision porušení ~80 % (pozri Validácia), nie 100 %.

## RQ1: Ako často agenti porušujú pravidlá z context file?

Violation rate = violated / (complied + violated). `repo_avg` je priemer per-repo rates, takže každé repo váži rovnako.

| Pravidlo | PR | Repo | Violation rate | Repo-avg rate |
|---|---:|---:|---:|---:|
| changelog | 514 | 31 | 38 % | 50 % |
| required_tests | 1 050 | 125 | 25 % | 26 % |
| commit_format | 2 043 | 139 | 12 % | 20 % |
| package_manager | 267 | 61 | 9 % | 18 % |

Jednoduché formálne pravidlá (conventional commits, package manager) agenti väčšinou dodržia. Pravidlá, ktoré znamenajú prácu navyše, teda pridať testy alebo doplniť changelog, porušujú často. Changelog vynechajú zhruba v každom treťom PR, kde ho pravidlo vyžaduje (v priemernom repe v polovici).

### Podľa agenta (repo-avg violation rate)

| Pravidlo | Claude Code | Copilot | Cursor | Devin | Codex |
|---|---:|---:|---:|---:|---:|
| changelog | 70 % | 48 % | 86 % | 98 % | 15 % |
| commit_format | 5 % | 34 % | 29 % | 31 % | 10 % |
| package_manager | 0 % | 26 % | 16 % | 0 % | 14 % |
| required_tests | 21 % | 23 % | 41 % | 80 % | 34 % |

Claude Code má najnižšie rates pri commit formáte, package manageri a testoch; pri changelogu je najlepší Codex (15 %), Claude Code tam má len 17 PR v 5 repo. Devin a Cursor majú najvyššie rates. Google Jules sme vynechali, lebo mal len 1 až 14 PR. Devin má navyše dáta len zo 4 až 7 repo, takže jeho čísla treba brať opatrne.

## RQ2: Dodržiavajú agenti pravidlo lepšie, keď je zapísané?

V tom istom repo porovnávame agent PR pred pridaním pravidla a po ňom. Repo musí mať aspoň 5 PR na každej strane a z nich aspoň 3 labelované. Changelog sme vynechali, lebo takých repo bolo málo.

### Hlavný výsledok (každé repo = 1 bod, Wilcoxon signed-rank)

| Pravidlo | Repo | Medián bez pravidla | Medián s pravidlom | Zlepšené / horšie / bez zmeny | Wilcoxon p |
|---|---:|---:|---:|---|---:|
| commit_format | 16 | 28.2 % | 3.7 % | 9 / 5 / 2 | 0.096 |
| required_tests | 11 | 33.3 % | 12.5 % | 6 / 2 / 3 | 0.109 |
| package_manager | 7 | 0 % | 0 % | 3 / 1 / 3 | 0.625 |

### Regresia (conditional logit, v rámci repo)

| Pravidlo | PR | Odds ratio | 95 % CI | p |
|---|---:|---:|---|---:|
| commit_format | 1 044 | 0.32 | 0.20–0.49 | <0.001 |
| required_tests | 399 | 0.68 | 0.35–1.33 | 0.26 |
| package_manager | 117 | 0.40 | 0.04–4.57 | 0.46 |

Keď je pravidlo zapísané, šanca porušenia commit formátu klesne asi o 68 %. Pri testoch ide odhad tým istým smerom (−32 %), ale po oprave checkera už nie je štatisticky významný: zostalo len 11 repo a 399 PR (predtým 16 repo, OR 0.46, p = 0.001 – tento efekt bol z veľkej časti spôsobený falošnými porušeniami). Pri package manageri merateľný efekt nevidíme. Agenti ho dodržiavajú aj bez pravidla, pretože napodobňujú lockfile, ktorý už v repe je.

### Kontrola s ľuďmi (len commit_format, len PR title, difference-in-differences)

Ľudské PR sú z AIDev v3. Je ich iba 151 v 5 zo 16 repo, takže tento výsledok je len predbežný a treba ho overiť na väčšej vzorke.

| | bez pravidla | s pravidlom |
|---|---:|---:|
| agent | 41 % (392) | 15 % (652) |
| human | 3 % (107) | 16 % (44) |

DiD interakcia `rule_active × agent` vyšla OR 0.067 (CI 0.014–0.324, p = 0.001). Agenti sa zlepšili výrazne viac ako ľudia, ktorí sa skôr zhoršili. Pokles teda nevysvetlí len to, že sa zmenil celý projekt.

Pri commit formáte máme dobrý dôkaz, že agenti na zapísané pravidlo reagujú. Pri testoch je efekt naznačený, ale nepreukázaný. Pri package manageri nie: pravidlo je pre agentov zbytočné, lebo to robia správne aj bez neho.

## RQ3: Čo sa stane s PR, ktoré porušia pravidlo?

Vstupom sú labelované páry (PR, pravidlo) z RQ1 bez `not_applicable`. Každý PR skončí ako `merged` (má `merged_at`), `rejected` (zatvorený bez merge) alebo `open` (zatiaľ bez výsledku, tieto vynechávame).

Copilot, Devin, Cursor a Jules commitujú pod vlastným bot účtom. Ich commity preto vieme oddeliť od ľudských a zlabelovať samostatne (`agent_label`). Claude Code a Codex commitujú pod účtom používateľa, takže pri nich nevidíme, či porušenie opravil človek (`fixes_visible = False`).

### Osud PR, v ktorých agent porušil pravidlo

| Pravidlo | Nástroje | Rejected | Fixed, potom merged | Merged as is | Open | PR |
|---|---|---:|---:|---:|---:|---:|
| changelog | bot (Copilot/Devin/Cursor) | 30 % | 8 % | 30 % | 32 % | 199 |
| changelog | Claude Code/Codex | 33 % | – | 47 % | 20 % | 15 |
| commit_format | bot | 48 % | 8 % | 29 % | 14 % | 250 |
| commit_format | Claude Code/Codex | 49 % | – | 51 % | 0 % | 39 |
| required_tests | bot | 31 % | 11 % | 42 % | 16 % | 235 |
| required_tests | Claude Code/Codex | 25 % | – | 66 % | 8 % | 59 |
| package_manager | všetky | 50 % | 0 % | 35 % | 13 % | 23 |

Človek opraví porušenie pred merge len v 8 až 11 % prípadov. Oveľa častejšie sa PR buď zamietne, alebo sa zmerguje aj s porušením.

### Mergujú sa porušujúce PR menej? (iba zatvorené PR, conditional logit v rámci repo)

| Pravidlo | PR | Repo | Merge rate complied | Merge rate violated | Odds ratio | 95 % CI | p |
|---|---:|---:|---:|---:|---:|---|---:|
| commit_format | 1 848 | 135 | 79 % | 45 % | 0.19 | 0.13–0.28 | <0.001 |
| changelog | 410 | 28 | 90 % | 56 % | 0.34 | 0.15–0.76 | 0.009 |
| required_tests | 803 | 110 | 75 % | 65 % | 0.90 | 0.55–1.47 | 0.67 |
| package_manager | 152 | 46 | 65 % | 40 % | 0.15 | 0.02–1.42 | 0.10 |

PR, ktoré porušia commit formát alebo changelog, sa zmergujú výrazne menej často. Chýbajúce testy na merge vplyv nemajú. Ide však o koreláciu: PR s nekonvenčným názvom môžu byť horšie aj inak, napríklad nedokončené. Prázdne PR, v ktorých agent nezmenil žiadny súbor, to nevysvetľujú, lebo medzi porušeniami je ich len 8.

### Všimnú si to reviewri? (podiel porušujúcich PR, kde človek spomenul pravidlo)

| Pravidlo | Má ľudský feedback | Človek spomenul pravidlo | Bot spomenul |
|---|---:|---:|---:|
| changelog | 59 % | 3 % | 3 % |
| commit_format | 35 % | 2 % | 8 % |
| required_tests | 47 % | 3 % | 7 % |
| package_manager | 35 % | 20 % (4 PR) | 35 % |

Feedback sú reviews, bežné komentáre a inline komentáre ku kódu od účtov s `user_type == User`. Nerátame autora PR ani samotného agenta. Či komentár spomína pravidlo, zisťujeme keyword regexom, ktorý je dosť hrubý. Z vypísaných ukážok sedí pri testoch asi 6 z 9, pri commit formáte väčšina a pri package manageri asi 3 zo 6.

Ľudia porušenie v review takmer nikdy nespomenú (2 až 3 % PR). Pri commit formáte a changelogu sa porušenie aj tak prejaví nižšou mierou merge, chýbajúce testy však prechádzajú bez rozdielu. Keď už sa porušujúci PR zmerguje, väčšinou aj s porušením. Opravu človekom vidíme len v 8 až 11 % prípadov.

## Validácia (ručná kontrola)

**Package manager, všetkých 23 porušení** (`package_manager_violations.csv`, overené cez git históriu PR): 19 správnych, 3 nesprávne, 1 nejasné → **precision 86 %** (19/22).
- Chyby: lockfile v npm podprojekte, ktorý npm používa legitímne (typespec); lockfile prišiel z merge `main`, nie od agenta (azure-sdk-for-js); PR mal za úlohu migráciu Yarn→pnpm (democracy-client).
- V 8 z 19 správnych prípadov agent (alebo človek) lockfile neskôr zmazal, takže vo finálnom diffe nie je. Porušenie prvej verzie od agenta je však reálne.

**Náhodná vzorka 100 párov** (`validation_sample.csv`, seed 0; pre commit format, tests a changelog po 20 `violated` + 10 `complied`, plus 10 `complied` pre package manager):

| Pravidlo | Detekcia pravidla správna | `violated` správne | `complied` správne |
|---|---|---|---|
| commit_format | 30/30 | 19/20 | 10/10 |
| required_tests | 26/30 | 6/19 (+1 nejasné) | 9/10 |
| changelog | 22/30 | 7/19 (+1 nejasné) | 10/10 |
| package_manager | 9/10 | – | 10/10 |

Hlavné zistenie: **violation rates pre required_tests a changelog sú výrazne nadhodnotené** (precision porušení ~30–35 %). Dôvody:
- Pravidlo má rozsah, ktorý checker ignoruje: „testy pre *nové funkcie*“ (PR je bugfix/refactor/docstring), „changelog pre *významné* zmeny“, „len keď sa mení súbor X“.
- Regex chytí riadky, ktoré nie sú per-PR pravidlo: kroky release procesu („Publish a New Release → Update CHANGELOG.md“), podmienky („if the user asks…“), umiestnenie testov („write test in same directory with `.spec.tsx`“), pravidlá len pre iný jazyk („unit tests for new Python functions“ pri TS PR).
- Changelog v README.md (ioBroker) checker nevidí.
- Commit format: jediná chyba je emoji conventional commits (`🐛 fix:`), ktoré regex odmietne.

Tabuľka vyššie platí pre **pôvodné** checkery.

### Po oprave checkerov

Checkery pre tests a changelog sme sprísnili podľa zistení vyššie (pravidlá v `rules.md`, sekcia „Scope of tests and changelog rules“). Všetky čísla RQ1–RQ3 v tomto dokumente sú už s novými checkermi.

Overenie na **novej** vzorke 15 + 15 porušení (`validation_sample_v2.csv`, seed 1, žiadny PR z prvej vzorky):

| Pravidlo | `violated` správne – checker v1 | `violated` správne – finálny checker |
|---|---|---|
| required_tests | 8/13 (62 %), 2 nejasné | 8/10 (80 %) |
| changelog | 10/14 (71 %), 1 nejasné | 10/12 (83 %) |

Checker v1 = po prvom kole opráv (podľa prvej vzorky); na novej vzorke sme našli ešte 3 všeobecné chyby (test súbory `Foo_Tests.cs` / `Foo.UnitTests/`, odkazy na `/changelog/` stránky, PR „Document …“) a opravili ich. Čísla 80 % / 83 % sú preto mierne optimistické, nestranný odhad by chcel ďalšiu novú vzorku. Na prvej vzorke finálny checker: tests 5/6, changelog 5/6 správnych porušení; commit_format 19/19 (emoji chyba opravená).

## Čo ešte chýba a limity

- Validácia je na malej vzorke (100 + 23 párov) a labely navrhol Claude; treba ich prejsť človekom (ideálne dvaja anotátori kvôli inter-rater agreement).
- Effective rule set určujeme podľa dátumu, nie podľa base SHA.
- Kontrola s ľuďmi v RQ2 má málo dát (151 PR, 5 repo).
- RQ3: opravu človekom vidíme len pri bot nástrojoch. PR title je finálny, takže premenovanie nevidíme. Precision mention regexov nie je zmeraná.
- RQ4 a P2 (2026) zatiaľ nie sú urobené.
