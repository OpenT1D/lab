# Kritische review van de OpenT1D-repositorybasis

Dit rapport bewaart de bevindingen over baselinecommit `b6bb60486a6bdf158f9954073ca70c9c5bfa31bb`. Na de review zijn verbeteringen opgepakt; de [maintainerhandleiding](../maintenance.md#current-setup) beschrijft de actuele operationele status en resterende activeringspunten. Het oorspronkelijke oordeel hieronder is geen nieuwe controle van die opvolgende wijzigingen.

## 1. Oordeel

**De repositorybasis is geschikt om M0 te starten en verder te ontwikkelen op de huidige private hoofdbranch. Zij is nog niet gereed voor volledige publieke onboarding en de gebouwde documentatiesite heeft een concrete toegankelijkheidsfout.** De onderzoeksrichting, bijdrageafspraken en bestaande technische controles vormen een samenhangende basis. Er is geen bevestigde P0 of P1 gevonden die de huidige private `main` onbruikbaar of onverantwoord maakt.

De voornaamste inhoudelijke kracht is dat OpenT1D een groot wetenschappelijk doel verbindt aan controleerbare tussenresultaten. Het onderscheid tussen eigen infrastructuur, externe modellen en gerichte eigen modules is duidelijk. De documenten kennen geen algemene validatiestatus toe aan software die alleen installeert of een simulatie kan uitvoeren. Dat is voor dit project wezenlijker dan een lange lijst communitybestanden of badges.

Vier punten vragen gerichte opvolging. Een vertrouwelijk meldkanaal ontbreekt, branchregels worden niet afgedwongen, dependencywaarschuwingen staan uit en Nederlandstalige rapporten krijgen Engelse taalmetadata. De eerste twee waren al als open activeringspunten beschreven; de actuele GitHub-status bevestigt ze. De uitgeschakelde kwetsbaarheidsmeldingen zijn nu expliciet via de API vastgesteld. De verkeerde taalmarkering is een nieuw gereproduceerde fout in de uitvoer.

| Bevinding | Ernst | Private main | Publieke bijdragen | Gebouwde documentatiesite / eerste release |
| --- | --- | --- | --- | --- |
| B1 — Geen werkende vertrouwelijke meldroute | P1 voor publieke onboarding | Geen huidige blokkade | Eerst oplossen | Securityroute nodig voor een publieke softwarerelease |
| B2 — Checks en wijzigingsroute zijn niet afgedwongen | P2 | Bekende operationele beperking | Eerst de eigen publicatieafspraken uitvoeren | Releaseproces moet een aantoonbaar gecontroleerde bronversie gebruiken |
| B3 — Dependencywaarschuwingen staan uit | P2 | Verbetering van doorlopend onderhoud | Activeren en dekking controleren | Kwetsbaarheidsbeoordeling opnemen vóór een softwaredistributie |
| B4 — Nederlandse rapporten hebben Engelse taalmetadata | P2 | Geen huidige blokkade | Geen blokkade voor alleen Markdown op GitHub | Oplossen vóór publieke verspreiding van de HTML-site |

P0 betekent een direct ernstig probleem; P1 blokkeert verantwoord gebruik of de genoemde publicatiestap; P2 is een betekenisvol kwaliteits- of onderhoudsprobleem. P3 wordt hieronder alleen gebruikt voor optionele versterkingen van de controles. De prioriteiten zijn een beoordeling van impact in deze fase, geen automatisch afgeleide Scorecard-score.

## 2. Reikwijdte en bewijs

De beoordeelde basis is commit `b6bb60486a6bdf158f9954073ca70c9c5bfa31bb`, op 12 september 2026 zowel lokaal als op GitHub `main`. De werkdirectory was bij aanvang schoon. Alle 50 bijgehouden bestanden zijn betrokken: projectdocumenten, onderzoeksrapporten, templates, licentie- en citatiemateriaal, Python-tooling, tests, lockfile en GitHub-configuratie. Dit nieuwe rapport en zijn navigatievermelding vallen buiten de beoordeelde baseline.

De technische verificatie omvat een nieuwe clone zonder gedeelde Git-objecten, een nieuwe `.venv` en een lege uv-packagecache. De installatie haalde de dependencies opnieuw op. De aanwezige uv 0.11.16 en Python 3.12.13 op macOS ARM64 werden gebruikt; de Python-installatie zelf is niet opnieuw vanaf een lege machine opgebouwd. De aanvullende negatieve proeven gebruikten afzonderlijke tijdelijke kopieën en een bestaande toolingomgeving. Dat is een andere bewijssoort dan de schone installatie.

GitHub-instellingen en bestaande hosted runs zijn opnieuw gelezen. De geslaagde [run op de huidige main-commit](https://github.com/OpenT1D/OpenT1D/actions/runs/34717812888) en de [pull-requestrun vóór de merge](https://github.com/OpenT1D/OpenT1D/actions/runs/34717784427) bevestigen uitvoering op Ubuntu 24.04. Er is voor deze review geen nieuwe remote workflow gestart en geen instelling, issue, pull request of branch gewijzigd.

De vergelijking gebruikt actuele officiële projectdocumentatie en primaire richtlijnen. Zij beoordeelt concrete praktijken, niet de volledige kwaliteit van de voorbeeldprojecten. Bewegende documentatiebranches kunnen na de peildatum veranderen. De wetenschappelijke broncontrole is gericht op beslissende claims; zij is geen volledige audit van alle 41 wetenschappelijke voetnoten, de onderliggende vergelijkingen of klinische datasets.

## 3. Wat sterk is

### 3.1 Een duidelijke ingang en één uitvoeringsplan

[README.md](../../README.md) maakt de huidige status onmiddellijk zichtbaar. De installatiecommando's bouwen documentatie en worden ook zo omschreven. Een bezoeker krijgt geen fictieve simulator-API, gevalideerde virtuele patiënt of toekomstige release aangeboden als bestaande mogelijkheid.

[ROADMAP.md](../../ROADMAP.md) is de leidende planning. M0 vraagt om een concreet protocol, controle van upstreamherkomst en rechten, en een reproduceerbare referentie. M1 levert een volledige experimentketen; M2 controleert vervangbaarheid met een andere fysiologische familie. De latere biologische en datagerichte paden hebben eigen afhankelijkheden. Het ontbreken van de simulator is daarmee een expliciete projectfase, geen ontbrekend foundationbestand.

De publicatiechecklist maakt bovendien onderscheid tussen voorbereiding in bestanden en activatie op GitHub. Dat voorkomt dat bijvoorbeeld CODEOWNERS, een securitypolicy of een workflowbestand wordt verward met respectievelijk verplichte review, een bereikbaar meldkanaal of een daadwerkelijk geslaagde run.

### 3.2 Modulariteit met betekenisvolle grenzen

De [architectuur](../architecture.md) ondersteunt zowel volledige engines als fijnere compositie. Bestaande onderzoekers hoeven hun model niet eerst in een nieuwe vergelijkingstaal te herschrijven. Tegelijk zijn eenheden, compartimenten, routes, tijdsconventies en eigenaarschap van processen expliciete integratievoorwaarden.

Dit principe komt terug in de modelgids, modelkaart en biologische roadmap. Het voorkomt bijvoorbeeld dat een module en een engine ongemerkt beide dezelfde absorptie berekenen. De documenten schrijven nog geen universele interface voor voordat de eerste integraties aantonen welke afspraken werkelijk nodig zijn.

### 3.3 Wetenschappelijk bewijs blijft afzonderlijk zichtbaar

De [validatiegids](../research/validation.md) onderscheidt correcte implementatie, behoud van upstreamgedrag, toepassingsgerichte empirische toetsing en onafhankelijke reproductie. De roadmap houdt technische voortgang en ontbrekend bewijs apart. Een exploratieve module kan dus bruikbaar zijn zonder een ongefundeerde behandelingsclaim te krijgen.

Databeoordeling begint in M0. De [datagids](../research/data.md) behandelt onder meer ontbrekende waarden, deelnemeroverlap, tijdsbetekenis, feitelijke afgifte versus commando's en toegangsrechten. De model- en protocoltemplates vragen om bronversies, beperkingen, failures en evaluatiescheiding. Dat is een passende inhoudelijke basis voor later reproduceerbaar onderzoek.

### 3.4 Een uitvoerbare bijdrageprocedure

[CONTRIBUTING.md](../../CONTRIBUTING.md) biedt concrete ingangen voor code, documentatie, bronbeoordeling en reproductie. Het benodigde bewijs verschilt per type bijdrage. Kleine correcties mogen direct naar een pull request; gedeelde interfaces en nieuwe modules vragen een vroeg inhoudelijk voorstel. Er is geen algemene verplichting om voor iedere wijziging een nieuw besluitdocument te schrijven.

Governance noemt een echte verantwoordelijke, belangenconflicten en de beperkingen van één maintainer. AI-assistentie is toegestaan met verantwoordelijkheid voor begrip, herkomst en verificatie. Dat past bij snelle ontwikkeling zonder automatisch gegenereerde inhoud tot wetenschappelijk bewijs te verheffen.

### 3.5 Bestaande technische maatregelen doen werkelijk iets

Dezelfde repositorycheck wordt lokaal en in CI gebruikt. De lockfile bevat 62 pakketrecords uit PyPI; de daarin vermelde distributiearchieven hebben SHA-256-hashes. De twee Actions zijn op volledige commit-hashes vastgezet. De workflows hebben leesrechten, een tijdslimiet, annulering van vervangen runs en geen geprivilegieerde pull-requesttrigger.

De bestaande regressietests bewaken concrete fouten. Het uitschakelen van beperkte paginadetectie laat de test voor lokale notities falen. Het uitschakelen van het opruimen van HTML-uitvoer laat de test voor verwijderde pagina's en downloads falen. De eerdere oplossingen zijn dus opnieuw gecontroleerd en worden niet opnieuw als open defect opgevoerd.

## 4. Vergelijking met toonaangevende projecten

| Project en gecontroleerde praktijk | Probleem dat wordt opgelost | Betekenis voor OpenT1D |
| --- | --- | --- |
| PyBaMM gebruikt een vastgelegde ontwikkelomgeving, strikte documentatiecontroles en credit voor gebruikte modellen en methoden.[^1] | Een experiment moet uitvoerbaar zijn en zijn wetenschappelijke herkomst behouden. | De locked tooling en strikte build behouden. Upstreamcitatie later verbinden aan daadwerkelijke modelmanifesten en uitgevoerde experimenten. Voorbeeldtests toevoegen zodra echte simulatievoorbeelden bestaan. |
| SciPy benoemt ook documentatie, review en reproductie als bijdragen en maakt besluitbevoegdheid zichtbaar.[^2][^3] | Nieuwe bijdragers moeten een ingang vinden en weten hoe men een besluit neemt of betwist. | De verschillende bijdragevormen en founder-governance passen. Een steering council is pas zinvol wanneer er echte leden en verantwoordelijkheden zijn. |
| scikit-learn vraagt begrijpelijke, zorgvuldig beoordeelde bijdragen en behandelt onzorgvuldige AI-voorstellen als belasting voor reviewers.[^4] | Een indiener moet de voorgestelde wijziging kunnen beoordelen en onderhouden. | Verantwoordelijkheid en verificatie behouden; de beperktere AI-werkwijze hoeft niet te worden gekopieerd. OpenT1D mag een eigen, expliciet beleid voeren. |
| Mesa vraagt vroege afstemming over probleem en ontwerp, en voorbeelden en tests bij bruikbare nieuwe functies.[^5] | Voorkomen dat veel code wordt gebouwd voordat nut en integratie duidelijk zijn. | Een korte upstreamproef in M0 en gerichte ontwerpbesluiten behouden. Geen universele extra goedkeuringsrondes voor kleine wijzigingen invoeren. |
| PhysiCell geeft concrete voorbeeldprojecten met build- en uitvoercommando's en wetenschappelijke referenties.[^6] | Gebruikers leren het systeem via daadwerkelijk werkende experimenten. | Met M1 een vergelijkbare eerste gebruikservaring opleveren. De huidige toolingquickstart is eerlijk; een simulatiehandleiding zonder simulator zou dat niet zijn. |
| BioSimulators verbindt uitvoeringsconventies aan toetsbare voorbeeldarchieven.[^7] | Een interoperabiliteitsclaim moet controleerbaar zijn. | Het principe van een referentie per ondersteunde adapter overnemen. COMBINE/OMEX of SED-ML alleen implementeren wanneer een concrete ondersteunde taak dat nodig heeft. Technische conformiteit blijft iets anders dan biologische geldigheid. |

Deze vergelijking ondersteunt de bestaande richting. De grootste resterende verbetering zit in het afronden en controleren van operationele afspraken, niet in het kopiëren van meer documenten. De bijdrageprocedure van een groot project is een voorbeeld van een oplossing voor diens omstandigheden, geen universeel voorschrift voor OpenT1D.

De actuele AI-policy van SciPy vraagt bijvoorbeeld expliciete disclosure en begrenst autonome inzendingen.[^8] Dat is een eigen projectbeleid. OpenSSF maakt bij de Code-Review-controle daarnaast expliciet onderscheid tussen onafhankelijke menselijke review en AI- of botreview, maar erkent ook de beperkingen van een project met één actieve bijdrager.[^9] Deze review vormt geen bewijs dat OpenT1D al een onafhankelijke menselijke reviewpraktijk heeft.

## 5. Relevante standaarden en richtlijnen

| Kader | Status | Toetsing en oordeel |
| --- | --- | --- |
| GitHub-communitybestanden en formschema | Productconventies en schemas | Herkenbare bestanden en drie inhoudelijk passende issueforms zijn aanwezig. Schemaregels zijn iets anders dan YAML-opmaak. De werkelijke private formulierweergave blijft apart te controleren.[^10][^11] |
| GitHub Actions secure use | Beveiligingsrichtlijn | Minimale tokenrechten, volledige SHA-pinning en ontbreken van geprivilegieerde PR-uitvoering passen. Branchafdwinging staat hier los van.[^12] |
| CODEOWNERS en branchregels | Productvoorwaarden en instellingen | Het genoemde account heeft administratorrechten en GitHub rapporteert geen CODEOWNERS-fouten. `main` is volgens de branch-API niet beschermd. Zie B2.[^13] |
| OpenSSF Scorecard | Heuristische controles | Bruikbare dimensies zijn CI, review, branchbescherming, updatebeleid, tokenrechten en kwetsbaarheden. Er is geen volledige Scorecard uitgevoerd of totaalscore toegekend.[^9] |
| OpenSSF Best Practices | Criteria voor een vrijwillig badgeprogramma | Licentie, projectbeschrijving, bijdrageprocedure en tests passen bij de basis. Publieke toegankelijkheid, onderhoudshistorie en overige criteria zijn daarmee niet aangetoond. Geen badge claimen.[^14] |
| FAIR software | Aanbevelingen | Repository, licentie, registratie, citatie en kwaliteitscontrole zijn bruikbare doelen. De huidige private repository heeft geen volledige publieke FAIR-status. Registratie en archivering bij een werkelijk bruikbaar artefact organiseren.[^15] |
| SPDX en REUSE | Metadata-afspraken; REUSE is een vrijwillige specificatie | `Apache-2.0` is een duidelijke identifier. Bestandsgewijze rechtenmetadata wordt nuttiger bij gemengde assets. Zonder REUSE-claim is het ontbreken van REUSE-configuratie geen schending van die specificatie.[^16][^17] |
| Apache-2.0 | De gekozen licentievoorwaarden | Rootlicentie en attributiebeleid zijn aanwezig. De gids behandelt rechten van code, data en parameters afzonderlijk. Dit is geen compatibiliteitsoordeel over nog niet geïntegreerde engines.[^18] |
| Citation File Format | Metadataformaat | De CFF-validator slaagt. Er zijn geen fictieve releasegegevens of DOI's. Auteursrecht, toestemming en GitHub-weergave volgen niet uit een geslaagde schemavalidatie.[^19] |
| Diátaxis | Documentatiemethode | De documentatie is rond lezersvragen georganiseerd. Er is geen verplichting om vier lege mapbomen of een niet-bestaande API-reference aan te maken.[^20] |
| WCAG 2.2, taalmarkering | Formeel toegankelijkheidscriterium wanneer conformiteit wordt beoordeeld | De Nederlandse HTML-inhoud krijgt Engelse taalmetadata. Zie B4. Dit is geen volledige WCAG-audit en geen uitspraak over wettelijke verplichtingen.[^21][^22] |
| uv en Sphinx | Toolgedrag en configuratie | De gedocumenteerde Python 3.12-route werkt vanuit een nieuwe omgeving. Een Sphinx-build controleert documentverwijzingen, maar is geen algemene GitHub-schema- of raw-HTML-validator.[^23][^24] |

Geen van deze kaders vereist dat OpenT1D nu een fictieve release, pakket-API, DOI, adviesraad of volledige biologische standaardimplementatie toevoegt. Evenmin bewijst een community-health-percentage dat de wetenschap, contactkanalen of onderhoudspraktijk goed zijn.

## 6. Bevindingen

### B1 — P1 bij publieke onboarding: vertrouwelijke meldroute ontbreekt

**Locatie:** `SECURITY.md:7–9`, `CODE_OF_CONDUCT.md:20` en `docs/maintenance.md:20–21` in de beoordeelde commit.

**Bewijs:** beide policies zeggen expliciet dat geen vertrouwelijk kanaal is geconfigureerd. Het actuele private-vulnerability-reporting-endpoint retourneerde HTTP 404. Die status alleen bewijst geen oorzaak; de combinatie met de expliciete policies toont wel dat geen werkende route is bevestigd. Een conditionele verwijzing naar een eventuele GitHub-knop is nog geen bereikbaar kanaal. GitHub behandelt private vulnerability reporting als een afzonderlijk te activeren voorziening.[^25]

**Impact:** een externe bijdrager kan een kwetsbaarheid of vertrouwelijk gedragsincident niet via een vastgelegde operationele projectroute melden. De tekst is eerlijk, maar de ontbrekende uitvoering blijft relevant zodra de community wordt opengesteld. Dit is een bestaande, expliciet bekende publicatievoorwaarde, geen nieuw aangetroffen exploit.

**Voorstel:** een door de eigenaar aangewezen en beheerde contactroute opnemen. Security- en conductmeldingen mogen dezelfde ingang hebben als de afhandeling duidelijk is. Waar passend de GitHub-voorziening activeren zodra die beschikbaar is. Geen adres, ontvanger of onafhankelijke ombudsfunctie verzinnen.

**Acceptatie:** de policies noemen een echte bereikbare route en verantwoordelijke; een toegestane testmelding bereikt privé de bedoelde ontvanger; beperkingen bij een melding over de enige maintainer blijven zichtbaar. Het versturen van zo'n testbericht vraagt afzonderlijke toestemming en is in deze review niet gedaan.

### B2 — P2: controles en wijzigingsroute worden niet afgedwongen

**Locatie:** GitHub-instellingen voor `main`; bijbehorende afspraken in `docs/maintenance.md:24–25`; `.github/workflows/checks.yml:3–27` en `.github/CODEOWNERS:2`.

**Bewijs:** `GET /repos/OpenT1D/OpenT1D/branches/main` rapporteerde `protected: false`. Zowel het ruleset-endpoint als het branch-protection-endpoint gaf HTTP 403 met de melding dat een planwijziging of publieke zichtbaarheid nodig is. Tegelijk slagen hosted checks en herkent GitHub de code owner. Er bestaat dus een werkende controle, maar geen afgedwongen koppeling tussen die controle en iedere wijziging op `main`.

**Impact:** een geslaagde vorige run voorkomt niet dat later een wijziging zonder geslaagde controle wordt geplaatst of historie wordt overschreven. Voor de huidige private founderfase is dit een bekende operationele beperking. Voor publieke samenwerking moet de repository haar eigen beschreven wijzigingsroute daadwerkelijk inrichten. CODEOWNERS op zichzelf is geen bescherming.[^13]

**Voorstel:** bij de geschikte plan- of zichtbaarheidskeuze de `Repository checks`-status, pull-requestroute en bescherming tegen force-push/deletie instellen. Leg een eventuele maintainerbypass expliciet vast. Tot die tijd wijzigingen via de afgesproken PR- en controleprocedure laten verlopen en niet beweren dat GitHub dit afdwingt.

**Acceptatie:** instellingen en een gecontroleerde proef bevestigen dat een gewone wijziging de vereiste status moet halen en dat force-push/deletie beperkt zijn. Een tweede menselijke goedkeurder wordt pas verplicht wanneer die werkelijk beschikbaar is. De huidige beperking is geen reden om tijdens een review de repository ongevraagd openbaar te maken.

### B3 — P2: kwetsbaarheidsmeldingen voor dependencies staan uit

**Locatie:** actuele GitHub-securityinstellingen; `.github/dependabot.yml:3–18`; open onderhoudspunt `docs/maintenance.md:29`.

**Bewijs:** het vulnerability-alerts-endpoint gaf HTTP 404 met een expliciete melding dat de alerts uitstaan. Het Dependabot-alerts-endpoint bevestigde dit met HTTP 403. De YAML-configuratie plant maandelijkse versie-updates. GitHub onderscheidt die functie van waarschuwingen over bekende kwetsbaarheden en van security-updates.[^26][^27]

**Impact:** het project krijgt via deze voorziening geen doorlopende waarschuwing bij een nieuw bekend dependencyprobleem. Een maandelijkse update-PR en een lockfile lossen dit niet zelfstandig op. Een geïsoleerde scan met pip-audit 2.10.1 vond op de peildatum geen bekende kwetsbaarheden in de 61 geïnstalleerde Python-pakketten, zonder overgeslagen pakketten. Dit is een momentopname, geen bewijs dat monitoring overbodig is.[^28]

**Voorstel:** dependency alerts activeren en controleren of de dependencygraph de gebruikte Python-afhankelijkheden werkelijk herkent. Wijs afhandeling toe en controleer de notificatievoorkeur. Kies bij onvoldoende graphdekking een kleine periodieke audit van de feitelijk gebruikte dependencies. Behoud maandelijkse versie-updates daarnaast; automatische merges zijn niet nodig.

**Acceptatie:** het alerts-endpoint bevestigt activatie, de relevante dependencies zijn zichtbaar en er is een verantwoordelijke voor opvolging. Eventuele ontbrekende ecosysteemdekking is expliciet opgevangen. De audit of meldingen hebben een gecontroleerde route, zonder bewust een kwetsbaar pakket in de hoofdbranch te introduceren.

Dit is een onderhoudsgat, niet een aangetoonde kwetsbare dependency in de huidige versie. De Python-scan dekt niet automatisch Actions, de Python-interpreter of de via CDN geladen Mermaid-library.

### B4 — P2: Nederlandse rapporten worden als Engels gemarkeerd

**Locatie:** `docs/conf.py:7–35` en de gegenereerde versies van `docs/onderzoek/projectopzet.md` en `docs/onderzoek/repositorybasis.md`.

**Bewijs:** beide HTML-pagina's bevatten `lang="en"` op het `html`-element en geen `lang="nl"` op het Nederlandse artikel of een andere passende inhoudscontainer. Dit is opnieuw vastgesteld na de schone build. De documenttaal erft daardoor Engels. De huidige tests controleren deze eigenschap niet.

**Impact:** schermlezers en andere taalafhankelijke hulpmiddelen krijgen de verkeerde uitspraaktaal voor duizenden woorden Nederlands. Een document kan visueel goed ogen en tegelijk onjuist worden voorgelezen. WCAG 2.2 SC 3.1.1 vraagt een programmatisch bepaalbare hoofdtaal; SC 3.1.2 behandelt afwijkende talen binnen inhoud.[^21][^22]

**Voorstel:** taalmetadata per document invoeren en in de daadwerkelijke template-uitvoer verwerken. Overwegend Nederlandse pagina's krijgen `html lang="nl"`, Engelse gidsen blijven `en` en de Engelstalige interfaceonderdelen krijgen `lang="en"`. Een frontmatterveld toevoegen zonder effect op HTML is onvoldoende.

**Acceptatie:** controle van de gegenereerde HTML toont de juiste effectieve taal voor beide bestaande rapporten én dit nieuwe rapport; Engelse pagina's behouden hun taal. Voeg een regressiecontrole toe en controleer ten minste één rapport met taalinspectie of een schermlezer. Omdat deze review alleen rapportagewijzigingen bevat, blijft de fout ook voor de HTML-versie van dit rapport nog open.

De fout blokkeert geen verdere private ontwikkeling. Zij moet worden opgelost vóór het publiek delen van de gebouwde site. Alleen de Markdown-bestanden openbaar maken op GitHub is een afzonderlijke publicatiestap met andere rendering.

## 7. Verificatie en grenzen van de controles

### 7.1 Werkelijk uitgevoerde controles

| Controle | Uitkomst | Bewijsgrens |
| --- | --- | --- |
| Nieuwe clone, nieuwe `.venv`, lege packagecache; `uv sync --locked` | Geslaagd; dependencies opnieuw opgehaald | Bestaande uv- en Python-installatie gebruikt; geen volledig nieuwe machine |
| `uv run --locked python scripts/check.py` | Geslaagd: Ruff, Markdown, YAML, CFF, navigatie, zeven tests, strikte HTML-build | Geen simulatie- of biologische tests |
| Gegenereerde interne links en ankers | 1.464 verwijzingen over 28 HTML-pagina's, geen fout | Baseline vóór toevoeging van dit rapport; geen volledige toegankelijkheidstoets |
| Bestaande GitHub Actions-runs | Geslaagd op de beoordeelde main-commit en op de genoemde PR | Historische echte hosted runs opnieuw geverifieerd; geen nieuwe remote run voor de review gestart |
| `actionlint` 1.7.12 op beide workflows | Geslaagd | Afzonderlijk aanwezig via Homebrew; geen onderdeel van de vastgelegde repositorycheck |
| pip-audit 2.10.1 op de schone Python-omgeving | 61 pakketten, nul bekende kwetsbaarheden, nul overgeslagen | PyPI-advisorygegevens op de peildatum, alleen geïnstalleerde Python-pakketten |
| Lockfile-inventaris | 62 pakketrecords, PyPI-bronnen, distributiehashes aanwezig | Sommige platformafhankelijke pakketten worden lokaal niet geïnstalleerd; hashes bewijzen geen afwezigheid van schadelijke code |
| CODEOWNERS-API en accountrechten | Geen parsefouten; genoemde account heeft administratorrechten | Geen verplichte onafhankelijke review door het bestaan van dit bestand |
| Taalmetadata van Nederlandse HTML-rapporten | Fout gereproduceerd: alleen Engelse taalmarkering | B4; visuele opmaak en uitspraak zijn afzonderlijke eigenschappen |

De uv-waarschuwing over ontbrekende `requires-python` bij deze tooling-only configuratie is zichtbaar. De vastgelegde Python 3.12-route werkt. Ook `uv add --group dev PACKAGE` is in een tijdelijke kopie met een beschikbare dependency gecontroleerd. Er is geen bewijs dat daarvoor nu een fictief installeerbaar OpenT1D-pakket moet worden toegevoegd.[^23]

### 7.2 Negatieve proeven

Elke onderstaande verandering is in een afzonderlijke tijdelijke kopie aangebracht. Alleen synthetische inhoud is gebruikt. De hoofdrepository en haar bestaande tests zijn niet gewijzigd.

| Proef | Werkelijke reactie | Beoordeling |
| --- | --- | --- |
| Beperkte Sphinx-paginadetectie uitschakelen | Test voor lokale notities faalt | Bestaande beveiliging tegen onbedoelde paginadetectie is aantoonbaar bewaakt |
| Opruimen van oude HTML-uitvoer uitschakelen | Test voor verwijderde pagina's/downloads faalt | Eerdere fix heeft een relevante regressietest |
| Expliciete downloadlink naar synthetisch bestand in `data/private/` toevoegen | Check slaagt; bestand wordt als download opgenomen | Exact gedocumenteerde grens in `docs/development.md:42`; een pagina-allowlist is geen sandbox voor expliciete assets |
| Raw HTML-link naar een ontbrekend bestand toevoegen | Check slaagt; foutieve link staat in uitvoer | HTML-links worden niet volledig door MyST gecontroleerd |
| Kapotte Markdown-link in de PR-template toevoegen | Check slaagt | GitHub-only Markdown krijgt stijlcontrole, maar geen Sphinx-referentiecontrole |
| `runs-on` wijzigen in `runs-onn` | Repositorycheck slaagt; actionlint faalt | YAML-opmaakcontrole is geen Actions-schemavalidatie |
| Issueformtype `textarea` wijzigen in `textinput` | Repositorycheck slaagt | YAML-opmaakcontrole bewijst geen formschema-conformiteit |

Deze proeven tonen controlegrenzen, niet dat de huidige workflows, formulieren of bestaande verwijzingen defect zijn. De huidige workflows slagen juist voor actionlint en hosted uitvoering. De bestaande expliciete-assetwaarschuwing moet behouden blijven; een testbestand dat bewust wordt gelinkt is geen bewijs van een verborgen lek in automatische paginadetectie.

De laatste vier proeven rechtvaardigen optionele P3-versterkingen: actionlint reproduceerbaar opnemen, een beperkte formschemacheck toevoegen en GitHub-only/raw-HTML-links controleren. Hun acceptatiecriterium is dat de beschreven synthetische fout wordt afgewezen terwijl geldige bestaande bestanden slagen. Nieuwe tooling moet dezelfde lokale en CI-route krijgen, met beperkte onderhoudslast.[^11][^29]

### 7.3 Externe links

De afzonderlijke Sphinx-linkcheck eindigde met exitcode 1. Van 87 externe URL-records werden er 70 als werkend gerapporteerd, twee als redirect en vier bewust overgeslagen vanwege private repositorytoegang. Elf verzoeken werden geweigerd: tien met HTTP 403 bij PMC, NEJM en Sage, en één met HTTP 429 bij GitHub/PhysiCell. Er werd in deze run geen HTTP 404 gerapporteerd. Daarnaast waren er tien lokale fragmentrecords die deze builder niet controleerde; die vallen onder de afzonderlijk geslaagde interne HTML-linkcontrole.

Een 403 of 429 is onvoldoende om een wetenschappelijke bron als verdwenen te classificeren. De broncontrole heeft relevante publicatieclaims waar mogelijk via de oorspronkelijke abstracten of auteursversies onderzocht. Niet iedere geweigerde pagina is daarmee volledig geverifieerd. De keuze om externe beschikbaarheid buiten de verplichte PR-check te houden is passend; voeg geen brede permanente uitzonderingen toe om het rapport kunstmatig groen te maken.

### 7.4 Overige GitHub-status

De repository is privé, `main` is de default branch, Issues staan aan en Discussions uit. De About-beschrijving is leeg en er zijn geen topics. Dat is een klein vindbaarheidspunt vóór publieke opening, geen fout in de projectinhoud. De licentie wordt als Apache-2.0 herkend.

Actions staan aan en de standaard workflowrechten zijn read-only. De huidige workflows pinnen hun Actions, terwijl accountbrede SHA-afdwinging niet aanstaat. Dat verschil is geen gebrek in de huidige twee bestanden. Secret-protectionstatus kon niet betrouwbaar uit de geretourneerde metadata worden vastgesteld; een ontbrekende waarde is niet als uitgeschakeld of geslaagd geïnterpreteerd.

Issueformweergave, het citaatpaneel en externe-bijdragegoedkeuring zijn niet volledig via een ingelogde browser bevestigd. De maintainerchecklist vermeldt de eerste twee al. De officiële formschemadocumentatie beperkt het blokkeren van indiening via `validations.required` bovendien tot publieke repositories; afwijkend gedrag in een private repository is daardoor niet automatisch een formulierfout.[^11]

## 8. Inhoudelijke en wetenschappelijke broncontrole

De gecontroleerde kernclaims ondersteunen de beschreven fasering. Een repositorylabel of publicatieabstract is daarbij alleen bewijs voor de betreffende beschrijving, niet voor de numerieke kwaliteit van een toekomstige adapter.

| Onderwerp | Bevinding bij primaire broncontrole | Consequentie |
| --- | --- | --- |
| simglucose | UVA/Padova 2008, 30 virtuele profielen en toegang tot extra patiënttoestanden staan in de oorspronkelijke repository.[^30] | Ancestry en begrenzing van controllerinformatie zijn terecht expliciet |
| GluCoEnv | De repository verwijst naar simglucose/UVA2008 en PyTorch-uitvoering.[^31] | Een tweede implementatie van deze basis is geen tweede onafhankelijke fysiologiefamilie |
| LT1 | `Cambridge.ts` noemt Hovorka-gerelateerde bronnen; de paper beschrijft headless uitvoering en modulaire architectuur.[^32][^33] | Een kandidaat voor een andere familie en een adapterproef is onderbouwd; uitvoerbaarheid binnen OpenT1D nog te bewijzen |
| APS TestBed | Het oorspronkelijke artikel beschrijft twee simulatoren en foutinjectie.[^34] | De roadmap onderzoekt terecht of bestaande infrastructuur al een deel van de behoefte dekt |
| ReplayBG | De oorspronkelijke evaluatie gebruikt 100 virtuele personen en twee casussen met echte gegevens.[^35] | De beperkte claim in de onderzoeksbasis is passend; een Python-port of nieuwe toepassing erft dit bewijs niet automatisch |
| MetaboNet | Tabel 1 rapporteert 3.135/1.895 subjects en 1.228,2/867,4 patiëntjaren voor totaal/publiek; §2.2 beschrijft overlap en resterende meerdere identifiers.[^36] | Brongetallen kloppen, maar zijn geen eigen audit van unieke deelnemers of data-inhoud |
| MetaboNet-Bench | De appendix noemt beperkingen tot niet-commercieel onderzoek en onderwijs voor de bundel.[^37] | De teksten laten terecht feitelijke download- en componentvoorwaarden beslissend blijven |
| Toepassingsgericht modelbewijs | FDA-guidance beschrijft risicogerichte geloofwaardigheid; het kalibratieprotocol behandelt identificeerbaarheid en onzekerheid.[^38][^39] | OpenT1D gebruikt dit als ontwerpkader en claimt geen automatische regulatoire conformiteit |
| Biologische modelgrenzen | De OGTT-methodestudie is geen algemene T1D/graftvalidatie; PhysioLab betreft de NOD-muis.[^40][^41] | De repository draagt bewijs niet ongegrond tussen populaties en soorten over |
| Therapievragen | TN10 onderzoekt risico vóór diagnose, PROTECT recente diagnose; de zimislecel-publicatie rapporteert 10 van 12 volledige-dosisdeelnemers insulineonafhankelijk op één jaar, met immuunsuppressie en interimanalyses.[^42][^43][^44] | De teksten onderscheiden fase, eindpunt en behandelvoorwaarden en beloven geen universele genezing |

Ook het onderscheid tussen oudere UVA/Padova-generaties en de uitbreiding naar dagsimulatie is in de versiegebonden literatuur gecontroleerd.[^45] Geen van deze controles installeerde een simulator of onderzocht patiëntrecords. De huidige ontbrekende tolerantiegetallen, controllersettings en definitieve populatiekeuze horen bij M0; willekeurige waarden toevoegen zou de basis minder betrouwbaar maken.

Drie inhoudelijke aanscherpingen zijn bruikbaar als ontwerpkeuze, maar geen bevestigde fout. Maak in M0 desgewenst één externe gebruiksvraag explicieter, zodat de technische added value ook aan een echte behoefte kan worden getoetst. Benoem bij de MetaboNet-aantallen desgewenst direct dat de gerapporteerde subjecttelling geen onafhankelijk gededupliceerd aantal unieke personen is; de bestaande overlapwaarschuwing dekt dit risico al. Voeg een ingevulde claim-evidencekaart toe wanneer de eerste echte upstreamreproductie daarvoor inhoud oplevert.

## 9. Geprioriteerd verbeterplan

| Volgorde | Actie | Gereed wanneer | Afhankelijkheid |
| --- | --- | --- | --- |
| Eerstvolgende onderhoudsverbetering | B3: dependencywaarschuwingen en dekking regelen | Activatie, relevante dependencygraph en verantwoordelijke aantoonbaar aanwezig; eventuele dekkingstekorten opgevangen | Bevoegde GitHub-instelling; geen nieuwe modelcode nodig |
| Vóór externe publieke bijdragen | B1: vertrouwelijk meldkanaal afronden | Policies verwijzen naar werkende route en toegestane ontvangsttest slaagt | Eigenaar levert kanaal en ontvanger |
| Vóór externe publieke bijdragen | B2: wijzigingsroute afdwingen waar beschikbaar | Vereiste check, PR-route, bescherming en eventuele bypass aantoonbaar ingesteld | Geschikt plan of bewuste publicatiestap |
| Vóór publieke HTML-site | B4: taalmetadata herstellen | Nederlandse en Engelse inhoud hebben passende effectieve taal; regressietest slaagt | Kleine documentatieconfiguratie-/templatewijziging |
| Bij publieke opening | Overige bestaande checklist uitvoeren | About, topics, private reporting waar beschikbaar, formulieren, citaatpaneel en rechten voor externe bijdragen gecontroleerd | Gekozen publicatie- en notificatiebeleid |
| Optioneel, bij verdere toolingwijzigingen | P3: schemas en overige links beter bewaken | De vier genoemde synthetische fouten worden afgewezen met bruikbare uitleg | Beperkte reproduceerbare toolinguitbreiding |
| Daarna inhoudelijk verder | M0 uitvoeren volgens de bestaande roadmap | Protocol, bronrevisies, assetrechten, upstreamreferentie en datafit concreet | Werkelijk modelonderzoek, geen extra foundationbureaucratie |

Voor een eerste software- of onderzoeksrelease blijven de bestaande mijlpaalcriteria gelden: een reproduceerbaar voorbeeld, versies en toegestane assets, relevante numerieke checks, claimgrenzen en een passende correctieprocedure. Packaging, distributie-inventaris, archivering en eventuele attesten moeten de daadwerkelijke release volgen. Het ontbreken daarvan in de huidige documentatiefase is niet als fout geclassificeerd.

## 10. Reproductie en beperkingen

De kerncontrole is vanuit een nieuwe clone te herhalen met onderstaande commando's. Gebruik voor een vergelijking met dit rapport de genoemde baselinecommit en een afzonderlijke lege cache; de omvang van de site verandert zodra dit rapport wordt toegevoegd.

```sh
uv sync --locked
uv run --locked python scripts/check.py
uv run --locked sphinx-build -E -a -b linkcheck -c docs . _build/linkcheck
```

De taalbevinding is zonder extra Python-library te inspecteren:

```sh
uv run --locked python - <<'PY'
from html.parser import HTMLParser
from pathlib import Path

class Languages(HTMLParser):
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "lang" in values:
            print(tag, values["lang"])

for name in ("projectopzet", "repositorybasis"):
    print(name)
    page = Path(f"_build/html/docs/onderzoek/{name}.html")
    Languages().feed(page.read_text(encoding="utf-8"))
PY
```

Op de baseline is de uitvoer voor beide documenten uitsluitend `html en`. De negatieve proeven zijn afzonderlijk te herhalen met de wijzigingen uit §7.2; pas die nooit toe op een bronversie die wordt gepubliceerd. De toets op geretourneerde HTTP-statussen vereist passende repositorytoegang. De rapportage bewaart geen credentials, patiëntgegevens of testmeldingen.

Dit onderzoek bewijst geen volledige afwezigheid van kwetsbaarheden, volledige WCAG-conformiteit, juridische geschiktheid van toekomstige modeldistributies of biologische validiteit. De aanvullende audittools maken geen deel uit van de repositorylockfile. Windows is niet apart uitgevoerd; Linux is onderbouwd door de bestaande hosted runs, niet door een nieuwe lokale Linux-installatie. De wetenschappelijke checks betroffen vooral oorspronkelijke abstracts, relevante tekstpassages en projectdocumentatie; supplementen, volledige datalicenties en alle eventuele errata zijn niet uitputtend beoordeeld.

Tijdens de review zijn alleen dit Nederlandstalige rapport en de verwijzing ernaar in de inhoudsopgave toegevoegd. De uitvoering van verbeteringen vindt daarna plaats en verandert het bewijs over de genoemde baseline niet.

## Bronnen

Alle webbronnen zijn geraadpleegd op 12 september 2026. Projectdocumentatie en GitHub-richtlijnen betreffen de op die datum geraadpleegde versie. De repositorybevindingen verwijzen naar de vastgelegde baselinecommit; operationele GitHub-waarnemingen zijn gedateerde momentopnamen. Publicatiejaren hieronder behoren bij de oorspronkelijke studies.

[^1]: PyBaMM contributors. [Contributing to PyBaMM](https://github.com/pybamm-team/PyBaMM/blob/main/CONTRIBUTING.md). Officiële bijdragegids; tooling, documentatie, voorbeelden en citaties.
[^2]: SciPy community. [Contribute to SciPy](https://scipy.org/contribute/). Officiële bijdrage-ingang.
[^3]: SciPy community. [SciPy Project Governance](https://docs.scipy.org/doc/scipy/dev/governance.html). Rollen en besluitvorming.
[^4]: scikit-learn developers. [Contributing](https://scikit-learn.org/stable/developers/contributing.html). Bijdragekwaliteit, rechten en geautomatiseerde bijdragen.
[^5]: Mesa contributors. [Contributing to Mesa](https://github.com/mesa/mesa/blob/main/CONTRIBUTING.md). Probleemafstemming, ontwerp, voorbeelden en tests.
[^6]: PhysiCell contributors. [PhysiCell README](https://github.com/MathCancer/PhysiCell/blob/master/README.md). Voorbeeldprojecten en wetenschappelijke verwijzingen; automatische linkcheck gaf eenmaal HTTP 429.
[^7]: BioSimulators Team. [BioSimulators test suite](https://docs.biosimulators.org/Biosimulators_test_suite/). Simulatorconventies en voorbeeldarchieven.
[^8]: SciPy community. [AI Policy](https://docs.scipy.org/doc/scipy/dev/conduct/ai_policy.html). Projectspecifiek beleid, geen algemene norm voor OpenT1D.
[^9]: OpenSSF Scorecard contributors. [Scorecard Checks](https://github.com/ossf/scorecard/blob/main/docs/checks.md). Onder meer Code-Review, Branch-Protection, CI-Tests en Vulnerabilities; geen Scorecard-run of totaalscore voor deze review.
[^10]: GitHub. [Creating a default community health file](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file). Ondersteunde communitybestanden.
[^11]: GitHub. [Syntax for GitHub's form schema](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-githubs-form-schema). Elementtypes, validatie en publieke-repositorybeperking van required-velden.
[^12]: GitHub. [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use). Tokenrechten, pinning en omgang met onbetrouwbare invoer.
[^13]: GitHub. [About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners). Vereiste toegang en afzonderlijke branchregels.
[^14]: OpenSSF. [Best Practices Badge: passing criteria](https://www.bestpractices.dev/en/criteria/0). Vrijwillige programmavoorwaarden.
[^15]: Netherlands eScience Center en DANS. [FAIR software recommendations](https://fair-software.eu/). Vijf aanbevelingen voor onderzoekssoftware.
[^16]: SPDX Project. [Handling license information](https://spdx.dev/learn/handling-license-info/). Licentie-identifiers en bestandsgewijze informatie.
[^17]: Free Software Foundation Europe. [REUSE Specification 3.3](https://reuse.software/spec-3.3/). Voorwaarden voor de vrijwillige REUSE-aanpak.
[^18]: Apache Software Foundation. [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0.html). Januari 2004; officiële licentietekst.
[^19]: Citation File Format contributors. [Citation File Format](https://citation-file-format.github.io/). Metadataformaat en integraties.
[^20]: Daniele Procida. [Diátaxis](https://diataxis.fr/). Documentatiemethode.
[^21]: W3C. [Understanding WCAG 2.2 SC 3.1.1: Language of Page](https://www.w3.org/WAI/WCAG22/Understanding/language-of-page.html). Taalbepaling en hulpmiddelen; de pagina verwijst naar het formele criterium.
[^22]: W3C. [Understanding WCAG 2.2 SC 3.1.2: Language of Parts](https://www.w3.org/WAI/WCAG22/Understanding/language-of-parts.html). Taalwisseling binnen inhoud.
[^23]: Astral. [Configuring projects](https://docs.astral.sh/uv/concepts/projects/config/). Projectconfiguratie en onderscheid met packaging.
[^24]: Sphinx developers. [sphinx-build](https://www.sphinx-doc.org/en/master/man/sphinx-build.html). Buildgedrag en waarschuwingen.
[^25]: GitHub. [Configuring private vulnerability reporting for a repository](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository). Afzonderlijke activering van de meldvoorziening.
[^26]: GitHub. [Dependabot alerts](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-alerts). Detectie, activatie, meldingen en beperkingen.
[^27]: GitHub. [Dependabot version updates](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-version-updates). Onderscheid tussen versie-updates en securityfunctionaliteit.
[^28]: Python Packaging Authority. [pip-audit](https://github.com/pypa/pip-audit). Bekende kwetsbaarheden via advisorydiensten; in deze review versie 2.10.1, zonder automatische fixes.
[^29]: rhysd en contributors. [actionlint](https://github.com/rhysd/actionlint). Statische validatie van GitHub Actions; lokaal versie 1.7.12.
[^30]: Jinyu Xie en contributors. [simglucose](https://github.com/jxx123/simglucose). Oorspronkelijke repository en documentatie.
[^31]: GluCoEnv developers. [GluCoEnv](https://github.com/RL4H/GluCoEnv). Repository; fysiologische herkomst en uitvoering.
[^32]: LoopInsighT1 contributors. [Cambridge.ts](https://github.com/hpeuscher/loopinsight1/blob/master/src/core/models/Cambridge.ts). Modelimplementatie met oorspronkelijke referenties.
[^33]: Peuscher et al. [A Modular Open-Source Framework for In-Browser Diabetes Simulation](https://backend.orbit.dtu.dk/ws/files/383717203/1-s2.0-S2405896324021827-main.pdf). IFAC-PapersOnLine, 2024; vooral §2.2.
[^34]: Zhou et al. [Design and Validation of an Open-Source Closed-Loop Testbed for Artificial Pancreas Systems](https://arxiv.org/abs/2208.06479). CHASE, 2022; auteursversie.
[^35]: Cappon et al. [ReplayBG: A Digital Twin-Based Methodology](https://pubmed.ncbi.nlm.nih.gov/37368794/). IEEE Transactions on Biomedical Engineering, 2023; oorspronkelijke abstract.
[^36]: Wolff et al. [MetaboNet: The Largest Publicly Available Consolidated Dataset for Type 1 Diabetes Management](https://arxiv.org/html/2601.11505v1). 2026; tabel 1 en §2.2 van de auteursversie.
[^37]: Jeffries et al. [MetaboNet-Bench](https://arxiv.org/html/2606.18640v1). Preprint, juni 2026; appendix over datavoorwaarden.
[^38]: U.S. Food and Drug Administration. [Assessing the Credibility of Computational Modeling and Simulation in Medical Device Submissions](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/assessing-credibility-computational-modeling-and-simulation-medical-device-submissions). Definitieve guidance, november 2023.
[^39]: Villaverde et al. [A protocol for dynamic model calibration](https://pmc.ncbi.nlm.nih.gov/articles/PMC8769694/). Briefings in Bioinformatics, 2022; online 2021.
[^40]: Breda et al. [Oral glucose tolerance test minimal model indexes of beta-cell function and insulin sensitivity](https://pubmed.ncbi.nlm.nih.gov/11147781/). Diabetes, 2001; oorspronkelijke methodestudie.
[^41]: Shoda et al. [The Type 1 Diabetes PhysioLab Platform](https://pubmed.ncbi.nlm.nih.gov/20491795/). Clinical & Experimental Immunology, 2010; NOD-muismodel.
[^42]: Herold et al. [An Anti-CD3 Antibody, Teplizumab, in Relatives at Risk for Type 1 Diabetes](https://pubmed.ncbi.nlm.nih.gov/31180194/). NEJM, 2019. Populatie en eindpunt gecontroleerd; een toekomstige reproductie moet ook de gecorrigeerde publicatie en supplementen gebruiken.
[^43]: Ramos et al. [Teplizumab and β-Cell Function in Newly Diagnosed Type 1 Diabetes](https://pubmed.ncbi.nlm.nih.gov/37861217/). NEJM, 2023; PROTECT.
[^44]: Reichman et al. [Stem Cell-Derived, Fully Differentiated Islets for Type 1 Diabetes](https://pubmed.ncbi.nlm.nih.gov/40544428/). NEJM, 2025; oorspronkelijke abstract en geïndexeerde passages.
[^45]: Visentin et al. [The UVA/Padova Type 1 Diabetes Simulator Goes From Single Meal to Single Day](https://pubmed.ncbi.nlm.nih.gov/29451021/). Journal of Diabetes Science and Technology, 2018.
