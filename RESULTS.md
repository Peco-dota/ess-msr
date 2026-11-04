# Výsledky RQ1, RQ2 a RQ3 (P1 = AIDev, 2025)

## Kde je čo

| Čo | Kde |
|---|---|
| Návrh štúdie (RQ1–RQ4) | `../project-details.md` |
| Definície pravidiel a labelov | `rules.md` |
| RQ1 pipeline + výsledky | `src/ess_msr/fetch_data.ipynb` (sekcie 1–9) |
| RQ2 analýza | `src/ess_msr/rq2.ipynb` (reuse RQ1 pipeline, sekcie 1–8) |
| RQ3 analýza | `src/ess_msr/rq3.ipynb` (reuse RQ1 pipeline, sekcie 1–7) |
| Ručná kontrola package-manager porušení | `package_manager_violations.csv` (23 riadkov, stĺpec `correct` je zatiaľ prázdny) |
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
- `complied` = PR zmenil aj changelog (`CHANGELOG.md`, `docs/changelog/...`, `.changeset/*.md`).
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
- `complied` = PR zmenil aj aspoň jeden testový súbor (`tests/...`, `test_foo.py`, `foo_test.go`, `foo.test.ts`, `FooTest.java`).
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
- Úvodný tag v hranatých zátvorkách ignorujeme, takže `[alpha_factory] feat: ...` prejde.
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
- Changelog a testy kontrolujeme hrubo. Pri changelogu niektoré repá chcú záznam len pri „significant“ alebo „breaking“ zmenách, my však rátame každú zmenu kódu. Pri testoch zase nevieme, či malá oprava test naozaj potrebovala. Tieto rates sú preto skôr horná hranica.

## RQ1: Ako často agenti porušujú pravidlá z context file?

Violation rate = violated / (complied + violated). `repo_avg` je priemer per-repo rates, takže každé repo váži rovnako.

| Pravidlo | PR | Repo | Violation rate | Repo-avg rate |
|---|---:|---:|---:|---:|
| changelog | 728 | 42 | 52 % | 61 % |
| required_tests | 1 930 | 153 | 35 % | 35 % |
| commit_format | 2 043 | 139 | 13 % | 20 % |
| package_manager | 267 | 61 | 9 % | 18 % |

Jednoduché formálne pravidlá (conventional commits, package manager) agenti väčšinou dodržia. Pravidlá, ktoré znamenajú prácu navyše, teda pridať testy alebo doplniť changelog, porušujú často. Changelog vynechajú vo viac ako polovici prípadov.

### Podľa agenta (repo-avg violation rate)

| Pravidlo | Claude Code | Copilot | Cursor | Devin | Codex |
|---|---:|---:|---:|---:|---:|
| changelog | 54 % | 58 % | 86 % | 99 % | 42 % |
| commit_format | 7 % | 34 % | 29 % | 31 % | 10 % |
| package_manager | 0 % | 26 % | 16 % | 0 % | 14 % |
| required_tests | 22 % | 35 % | 51 % | 69 % | 46 % |

Claude Code má najnižšie rates pri všetkých pravidlách, Devin a Cursor najvyššie. Google Jules sme vynechali, lebo mal len 1 až 14 PR. Devin má navyše dáta len zo 4 až 7 repo, takže jeho čísla treba brať opatrne.

## RQ2: Dodržiavajú agenti pravidlo lepšie, keď je zapísané?

V tom istom repo porovnávame agent PR pred pridaním pravidla a po ňom. Repo musí mať aspoň 5 PR na každej strane a z nich aspoň 3 labelované. Changelog sme vynechali, lebo takých repo bolo málo.

### Hlavný výsledok (každé repo = 1 bod, Wilcoxon signed-rank)

| Pravidlo | Repo | Medián bez pravidla | Medián s pravidlom | Zlepšené / horšie / bez zmeny | Wilcoxon p |
|---|---:|---:|---:|---|---:|
| commit_format | 16 | 28.6 % | 3.7 % | 10 / 4 / 2 | 0.056 |
| required_tests | 16 | 43.5 % | 20.6 % | 9 / 6 / 1 | 0.047 |
| package_manager | 7 | 0 % | 0 % | 3 / 1 / 3 | 0.625 |

### Regresia (conditional logit, v rámci repo)

| Pravidlo | PR | Odds ratio | 95 % CI | p |
|---|---:|---:|---|---:|
| commit_format | 1 044 | 0.29 | 0.19–0.45 | <0.001 |
| required_tests | 891 | 0.46 | 0.29–0.72 | 0.001 |
| package_manager | 117 | 0.40 | 0.04–4.57 | 0.46 |

Keď je pravidlo zapísané, šanca porušenia klesne asi o 71 % pri commit formáte a asi o 54 % pri testoch. Pri package manageri merateľný efekt nevidíme. Agenti ho dodržiavajú aj bez pravidla, pretože napodobňujú lockfile, ktorý už v repe je.

### Kontrola s ľuďmi (len commit_format, len PR title, difference-in-differences)

Ľudské PR sú z AIDev v3. Je ich iba 151 v 5 zo 16 repo, takže tento výsledok je len predbežný a treba ho overiť na väčšej vzorke.

| | bez pravidla | s pravidlom |
|---|---:|---:|
| agent | 42 % (392) | 15 % (652) |
| human | 3 % (107) | 16 % (44) |

DiD interakcia `rule_active × agent` vyšla OR 0.058 (CI 0.012–0.284, p < 0.001). Agenti sa zlepšili výrazne viac ako ľudia, ktorí sa skôr zhoršili. Pokles teda nevysvetlí len to, že sa zmenil celý projekt.

Pri commit formáte a testoch máme dobrý dôkaz, že agenti na zapísané pravidlo reagujú. Pri package manageri nie: pravidlo je pre agentov zbytočné, lebo to robia správne aj bez neho.

## RQ3: Čo sa stane s PR, ktoré porušia pravidlo?

Vstupom sú labelované páry (PR, pravidlo) z RQ1 bez `not_applicable`. Každý PR skončí ako `merged` (má `merged_at`), `rejected` (zatvorený bez merge) alebo `open` (zatiaľ bez výsledku, tieto vynechávame).

Copilot, Devin, Cursor a Jules commitujú pod vlastným bot účtom. Ich commity preto vieme oddeliť od ľudských a zlabelovať samostatne (`agent_label`). Claude Code a Codex commitujú pod účtom používateľa, takže pri nich nevidíme, či porušenie opravil človek (`fixes_visible = False`).

### Osud PR, v ktorých agent porušil pravidlo

| Pravidlo | Nástroje | Rejected | Fixed, potom merged | Merged as is | Open | PR |
|---|---|---:|---:|---:|---:|---:|
| changelog | bot (Copilot/Devin/Cursor) | 33 % | 7 % | 35 % | 26 % | 307 |
| changelog | Claude Code/Codex | 27 % | – | 57 % | 17 % | 90 |
| commit_format | bot | 48 % | 7 % | 30 % | 14 % | 250 |
| commit_format | Claude Code/Codex | 49 % | – | 51 % | 0 % | 43 |
| required_tests | bot | 32 % | 10 % | 42 % | 16 % | 592 |
| required_tests | Claude Code/Codex | 19 % | – | 72 % | 8 % | 144 |
| package_manager | všetky | 50 % | 0 % | 35 % | 13 % | 23 |

Človek opraví porušenie pred merge len v 7 až 10 % prípadov. Oveľa častejšie sa PR buď zamietne, alebo sa zmerguje aj s porušením.

### Mergujú sa porušujúce PR menej? (iba zatvorené PR, conditional logit v rámci repo)

| Pravidlo | PR | Repo | Merge rate complied | Merge rate violated | Odds ratio | 95 % CI | p |
|---|---:|---:|---:|---:|---:|---|---:|
| commit_format | 1 848 | 135 | 79 % | 44 % | 0.20 | 0.14–0.29 | <0.001 |
| changelog | 576 | 38 | 89 % | 59 % | 0.28 | 0.14–0.55 | <0.001 |
| required_tests | 1 524 | 140 | 71 % | 66 % | 0.97 | 0.71–1.32 | 0.84 |
| package_manager | 152 | 46 | 65 % | 40 % | 0.15 | 0.02–1.42 | 0.10 |

PR, ktoré porušia commit formát alebo changelog, sa zmergujú výrazne menej často. Chýbajúce testy na merge vplyv nemajú. Ide však o koreláciu: PR s nekonvenčným názvom môžu byť horšie aj inak, napríklad nedokončené. Prázdne PR, v ktorých agent nezmenil žiadny súbor, to nevysvetľujú, lebo medzi porušeniami je ich len 8.

### Všimnú si to reviewri? (podiel porušujúcich PR, kde človek spomenul pravidlo)

| Pravidlo | Má ľudský feedback | Človek spomenul pravidlo | Bot spomenul |
|---|---:|---:|---:|
| changelog | 44 % | 1 % | 3 % |
| commit_format | 35 % | 2 % | 9 % |
| required_tests | 43 % | 1 % | 8 % |
| package_manager | 35 % | 20 % (4 PR) | 35 % |

Feedback sú reviews, bežné komentáre a inline komentáre ku kódu od účtov s `user_type == User`. Nerátame autora PR ani samotného agenta. Či komentár spomína pravidlo, zisťujeme keyword regexom, ktorý je dosť hrubý. Z vypísaných ukážok sedí pri testoch asi 6 z 9, pri commit formáte väčšina a pri package manageri asi 3 zo 6.

Ľudia porušenie v review takmer nikdy nespomenú (1 až 2 % PR). Pri commit formáte a changelogu sa porušenie aj tak prejaví nižšou mierou merge, chýbajúce testy však prechádzajú bez rozdielu. Keď už sa porušujúci PR zmerguje, väčšinou aj s porušením. Opravu človekom vidíme len v 7 až 10 % prípadov.

## Čo ešte chýba a limity

- `package_manager_violations.csv`: ručná validácia nie je vyplnená.
- Precision regexov na detekciu pravidiel nie je zmeraná, robili sme len vizuálnu kontrolu v sekcii 5 `fetch_data.ipynb`.
- Effective rule set určujeme podľa dátumu, nie podľa base SHA.
- Kontrola s ľuďmi v RQ2 má málo dát (151 PR, 5 repo).
- RQ3: opravu človekom vidíme len pri bot nástrojoch. PR title je finálny, takže premenovanie nevidíme. Precision mention regexov nie je zmeraná.
- RQ4 a P2 (2026) zatiaľ nie sú urobené.
