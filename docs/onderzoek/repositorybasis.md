# Onderzoek naar de repositorybasis van OpenT1D

## 1. Advies

OpenT1D heeft vanaf de start een samenhangende openbare projectbasis nodig: een begrijpelijke ingang, een uitvoerbare bijdrageprocedure, duidelijke verantwoordelijkheden en een controleerbaar spoor van wetenschappelijke aannames. Het passende resultaat is een repository waarin een nieuwe onderzoeker snel kan beoordelen wat het project wil bouwen, wat al werkt en hoe een eigen bijdrage kan worden beoordeeld.

De aanbevolen inrichting combineert een beknopte README met verdiepende documentatie, een actuele roadmap, wetenschappelijke bijdrageformats en geautomatiseerde documentatiecontroles. Het eindbeeld blijft een modulair virtueel laboratorium met infrastructuur én bouwblokken. De eerste concrete onderzoekstaak maakt die ambitie uitvoerbaar; de repository mag het project niet terugbrengen tot alleen een benchmark of wrapper.

Volledigheid betekent hier dat belangrijke verantwoordelijkheden zijn afgedekt en dat de beschreven werkwijze werkelijk uitvoerbaar is. Een lege map voor ieder toekomstig subsysteem, een badge zonder bewijs of een commissie zonder leden maakt de basis niet beter. Ook een perfect georganiseerde repository bewijst nog niet dat een fysiologisch model klopt.

## 2. Onderzoekskader

De peildatum is 12 september 2026. De vergelijking gebruikt officiële repositories en documentatie van gevestigde open-sourceprojecten, aangevuld met primaire documentatie van GitHub en gebruikte standaarden. De selectie omvat brede wetenschappelijke bibliotheken en projecten die inhoudelijk lijken op een modulair simulatieplatform. Zij is geen ranglijst naar sterren en geen volledige audit van de onderzochte software.

Het onderzoek beoordeelt zes aspecten: de eerste kennismaking, toetreding als bijdrager, wetenschappelijke controleerbaarheid, onderhoud, verantwoordelijkheden en de geschiktheid voor een project dat nog geen runtime heeft. Waargenomen praktijken en aanbevelingen voor OpenT1D zijn hieronder gescheiden. Documenten op een bewegende hoofdbranch kunnen na de peildatum veranderen.

De technische en biologische kwaliteit van T1D-modelkandidaten wordt behandeld in het afzonderlijke [projectonderzoek](projectopzet.md). In dit rapport gaat het om de inrichting die nodig is om zulke kwaliteit later te beoordelen en te onderhouden. Populaire projecten leveren bruikbare voorbeelden; hun omvang of bekendheid is geen reden om hun volledige proces over te nemen.

## 3. Vergelijking met bestaande projecten

| Project | Waargenomen praktijk | Vertaling naar OpenT1D |
| --- | --- | --- |
| PyBaMM | Combineert een simulatieframework, modellen en parameters met experimenten; de README geeft een uitvoerbaar begin en verwijst naar voorbeelden, documentatie en modelafhankelijke citaties. | Positioneer infrastructuur en modules samen. Voeg een echte eerste simulatiehandleiding toe zodra die bestaat; bewaar citaties van de werkelijk gebruikte modules. |
| SciPy | Onderscheidt verschillende soorten bijdragen en documenteert besluitvorming en bestuurlijke rollen. | Waardeer onderzoek, documentatie en reproductie naast code. Leg huidige verantwoordelijkheid vast zonder een volwassen bestuursstructuur te simuleren. |
| scikit-learn | Vraagt reproduceerbare probleemmeldingen, rechten op bijdragen en onderbouwde voorstellen; heeft expliciete regels voor geautomatiseerde bijdragen. | Laat iedere bijdrage begrijpelijk en controleerbaar zijn. Maak AI-gebruik mogelijk met verantwoordelijkheid voor kwaliteit, bronnen en verificatie. |
| Mesa | Verbindt bijdragen aan documentatie, tests en formattering; grotere uitbreidingen vragen inhoudelijke afstemming. | Laat kleine verbeteringen direct toe en bespreek gedeelde interfaces of nieuwe modules vroeg. Gebruik dezelfde controles lokaal en in CI. |
| PhysiCell | Organiseert de kennismaking rond concrete voorbeeldprojecten, buildcommando's en wetenschappelijke bronverwijzingen. | Maak een reproduceerbaar experiment later de belangrijkste gebruiksingang. Scheid documentatietooling nu duidelijk van toekomstige simulatiecommando's. |
| BioSimulators test suite | Verbindt expliciete simulatorconventies aan voorbeeldarchieven en uitvoeringscontroles. | Een compatibiliteitsclaim hoort bij uitvoerbare bewijsgevallen. Maak onderscheid tussen standaardconformiteit en biologische geldigheid. |

De projectobservaties volgen uit de eigen README's, bijdragegidsen en projectdocumentatie.[^1][^2][^3][^4][^5][^6][^7]

### 3.1 Wat vooral bruikbaar is

PyBaMM is inhoudelijk een sterke analogie: een domeingericht platform kan tegelijk gedeelde infrastructuur en een verzameling modellen zijn. Het model en de toepassing staan zichtbaar voorop. De praktische les voor OpenT1D is om de README te organiseren rond de onderzoekservaring die het platform wil bieden, met een eerlijke statusverklaring zolang die ervaring nog gebouwd wordt.[^1]

SciPy laat zien dat bijdragen breder zijn dan nieuwe algoritmen. Een duidelijke verdeling van verantwoordelijkheden maakt samenwerking voorspelbaar. Voor OpenT1D is een genoemde initiële maintainer met een openbaar besluitproces voldoende; een grote stuurgroep past pas wanneer de bijbehorende mensen en verantwoordelijkheden bestaan.[^2][^3]

De wetenschappelijke voorbeelden maken ook een grens zichtbaar. De BioSimulators-controles gaan over vastgelegde uitvoeringsconventies en voorbeeldexperimenten. Dat onderbouwt de noodzaak van compatibiliteitscontroles, maar ondersteunt op zichzelf geen claim dat een model een bepaalde patiënt of behandeling betrouwbaar voorspelt.[^7]

### 3.2 Wat niet letterlijk wordt overgenomen

De bijdrageprocedure van een groot bestaand project kan veel specialistische kennis en reviewcapaciteit veronderstellen. OpenT1D begint met een kort proces en specificeert per bijdrage welk bewijs nodig is. De strengere AI-beperkingen van scikit-learn worden niet gekopieerd; de gekozen OpenT1D-afspraak is dat AI-assistentie welkom is en de indiener verantwoordelijk blijft voor de inhoud.[^4]

Ook een bestaande branchingstrategie, website-infrastructuur of releasekalender wordt niet automatisch overgenomen. Die keuzes dienen de volwassenheid van het voorbeeldproject. OpenT1D heeft eerst één hoofdbranch, een controleerbare wijzigingsroute en een werkend documentatieproces nodig.

## 4. Informatiearchitectuur

De README heeft één taak: een nieuwe bezoeker helpen begrijpen wat OpenT1D is en waar de volgende stap staat. Zij bevat de ambitie, huidige status, eerste onderzoekstaak, belangrijkste navigatie, bijdrage-ingang, licentie en citatie. Gedetailleerde architectuur, modelvoorwaarden en onderhoudsinstructies horen in gelinkte documenten.

De documentatie krijgt afzonderlijke ingangen voor projectontwerp, onderzoek, bijdragen en onderhoud. Binnen die structuur helpt het Diátaxis-onderscheid tussen tutorials, taakgerichte handleidingen, referentie en uitleg. Die vier documentsoorten beantwoorden verschillende lezersvragen; ze hoeven niet direct vier grotendeels lege mapbomen te worden.[^8]

Voor OpenT1D zijn uitleg en bijdragehandleidingen nu echt te schrijven. Een simulatie-tutorial en API-referentie volgen met de eerste werkende implementatie. De aanwezige model- en protocoltemplates zijn documentatieformats en worden expliciet niet als technische interfaces gepresenteerd.

De publieke gidsen worden Engels. De bestaande Nederlandse onderzoeksrapporten blijven behouden en worden vanuit de documentatie ontsloten. Er komt één actuele roadmap. Onderzoeksrapporten leveren onderbouwing en verwijzen voor de huidige werkvolgorde naar die roadmap, zodat wijzigingen niet op drie plekken handmatig moeten worden bijgehouden.

| Inhoud | Canonieke plaats | Onderhoudsmoment |
| --- | --- | --- |
| Doel, huidige status en ingang | `README.md` | Iedere verandering in beschikbare mogelijkheden |
| Lange termijn en ontwerpprincipes | `docs/vision.md` | Wijziging in projectrichting |
| Mijlpalen en werkpakketten | `ROADMAP.md` | Bereikte uitkomst of gewijzigde afhankelijkheid |
| Architectuurgrenzen | `docs/architecture.md` | Eerste integraties en interfacebesluiten |
| Model-, data- en bewijsafspraken | `docs/research/` | Nieuwe toepassing of relevante methodische les |
| Deelname en verantwoordelijkheid | Root community-documenten | Veranderde werkwijze, contactpersoon of rol |
| Operationele inrichting | `docs/maintenance.md` | Activatie van GitHub-functies en releases |
| Onderzoeksbronnen | `docs/onderzoek/` | Nieuwe of gewijzigde beslissende informatie |

## 5. Benodigde repositorybestanden

GitHub ondersteunt herkenbare communitybestanden zoals CONTRIBUTING, CODE_OF_CONDUCT, SECURITY en SUPPORT. Die kunnen bezoekers naar de juiste informatie leiden. De plaatsing en aanwezigheid ervan zijn nuttig, maar een bestand activeert geen werkend proces of contactkanaal.[^9]

### 5.1 Vanaf de foundation

| Bestand of onderdeel | Waarom nodig | Concrete invulling |
| --- | --- | --- |
| README | Begrijpelijke eerste kennismaking | Ambitie, status, eerste taak en verwijzingen |
| CONTRIBUTING | Voorspelbare bijdrageprocedure | Lokale setup, review, bewijs en rechten |
| LICENSE en NOTICE | Rechten en attributie | Apache-2.0 voor origineel materiaal; behoud van upstreamvoorwaarden |
| CITATION.cff | Vindbare onderzoeksvermelding | Gecontroleerde bestaande auteursinformatie, nog geen verzonnen release of DOI |
| GOVERNANCE | Verantwoordelijkheid en besluitvorming | Eén genoemde maintainer en korte besluitdocumenten |
| CODE_OF_CONDUCT | Gedragsverwachtingen en reactie | Praktische eigen tekst met expliciete contactstatus |
| SECURITY en SUPPORT | Juiste route voor vragen en problemen | Scheiding tussen kwetsbaarheid, wetenschappelijke fout en projectvraag |
| CHANGELOG | Zichtbare betekenisvolle wijzigingen | Alleen Unreleased zolang er geen release is |
| Issue- en PR-templates | Bruikbare probleem- en bijdrage-informatie | Vraag, herkomst, reproductie en beperkingen |
| CODEOWNERS | Aangewezen reviewverantwoordelijke | De bestaande maintaineraccount |
| Editor- en Git-configuratie | Consistente tekstbestanden | UTF-8, LF, beperkte ignore-regels |
| Tooling en CI | Herhaalbare kwaliteitscontrole | Lockfile, één lokaal/CI-commando en strikte documentatiebuild |

Een Code of Conduct zonder bruikbare meldroute is operationeel onvolledig. Het adres mag daarom niet worden verzonnen. Het inrichten en controleren van een vertrouwelijk contact blijft een expliciete voorwaarde voor publieke community-onboarding. Hetzelfde geldt voor de beschikbaarheid van private vulnerability reporting: GitHub behandelt dat als een afzonderlijke instelling.[^10]

De eerste issueforms verzamelen een probleem en zijn bewijs, een voorstel met acceptatiecriteria of een projectvraag. Het GitHub-formaat ondersteunt verplichte velden, maar de inrichting vraagt alleen informatie die bij dat type melding helpt. Blanco issues blijven beschikbaar voor uitzonderingen.[^11]

### 5.2 Pas toevoegen bij een concrete aanleiding

Een FUNDING-bestand komt wanneer een echte financieringsroute bestaat. Een DOI, publicatiebadge en releaseversie komen na daadwerkelijke publicatie. Automatisch package-publishing, releaseattestaties en een distributie-inventaris horen bij een echt pakket. Een API-referentie hoort bij een bestaande API.

Een uitgebreide auteursdatabase, meerdere vertaalsystemen, een pluginregister, algemene voorbeelddata en een formele adviesraad zijn nu geen vereisten. Ze krijgen pas een plaats als de bijbehorende inhoud, personen of gebruiksvraag bestaan. Hierdoor blijft de huidige basis volledig voor haar taak en toch onderhoudbaar.

## 6. Wetenschappelijke afspraken

Een generieke open-sourcetemplate is voor OpenT1D onvoldoende. Een bijdrage kan softwarematig correct zijn en toch biologisch verkeerd gekoppeld. De basis heeft daarom expliciete afspraken voor modelherkomst, proceseigenaarschap, eenheden, tijd, observeerbare informatie en grenzen van gebruik.

Het modelkaartformat vraagt naar de oorspronkelijke publicatie, codeversie, parameters, licenties, populatie, mechanismen en beperkingen. Het vraagt ook wie een proces zoals absorptie of secretie modelleert. Dat voorkomt dat een technisch passende koppeling ongemerkt dezelfde fysiologie dubbel bevat.

Het protocolformat legt vraag, scenario, interventie, afstemming, uitkomstmaten en analysemethode vast. Het bevat een plaats voor failures, uitsluitingen, onafhankelijk toetsmateriaal en afwijkingen van het oorspronkelijke plan. Een resultaat moet later uit opgeslagen uitvoer kunnen worden gereconstrueerd zonder handmatige correcties aan een figuur of tabel.

Status wordt niet tot één kwaliteitsbadge samengeperst. Een module kan geïmplementeerd zijn, een upstreamvoorbeeld reproduceren en toch nog geen relevante externe validatie hebben. Deze eigenschappen moeten afzonderlijk zichtbaar blijven. De bronnen en argumenten hiervoor staan uitgebreider in het [wetenschappelijke projectonderzoek](projectopzet.md#8-validatie-als-kernfunctionaliteit).

De eerste publicatie hoeft geen nieuw optimaal regelalgoritme te presenteren. Een betekenisvolle vergelijking of een correct gedocumenteerde afhankelijkheid van de modelkeuze kan al bijdragen aan onderzoek. Het grotere laboratorium groeit vervolgens door dezelfde bewijs- en reproduceerbaarheidsinfrastructuur op nieuwe biologische vragen toe te passen.

## 7. Licentie, citatie en data

Voor nieuw OpenT1D-materiaal wordt Apache-2.0 gebruikt, aansluitend op de eerdere projectopzet. De officiële licentie bevat expliciete bepalingen voor bijdragen, patentlicenties, distributie en notices. De licentie wordt ongewijzigd opgenomen; projectspecifieke uitleg komt in de afzonderlijke licentiegids.[^12]

Deze keuze maakt geen aanspraak op rechten van andere onderzoekers. Een implementatie, parameterverzameling, dataset en figuur kunnen verschillende voorwaarden hebben. De koppeling van een GPL-component moet op de daadwerkelijk gebruikte en verspreide combinatie worden beoordeeld; een los proces is geen automatische oplossing.[^13]

CITATION.cff is geschikt voor machineleesbare citatiegegevens en wordt door GitHub herkend. Het bevat alleen bestaande metadata. Tot er een release of archiefrecord is, moet een gebruiker de gebruikte commit identificeren. De CFF-validator controleert de structuur, niet de historische juistheid van auteurschap of een wetenschappelijke claim.[^14][^15]

FAIR-softwareaanbevelingen benadrukken onder meer een openbare versiebeheerrepository, licentie, citatie en kwaliteitscontrole. Voor OpenT1D zijn dat zinvolle ontwerpdoelen. Een privérepository met voorbereide documenten heeft daarmee nog geen volledige publieke FAIR-status; publicatie en feitelijke toegankelijkheid blijven afzonderlijke stappen.[^16]

Data moeten bij hun gebruiksvoorwaarden blijven. Publieke voorbeelden kunnen synthetisch of expliciet herdistribueerbaar zijn. Toegang tot gecontroleerde gegevens kan via reproduceerbare instructies en converters worden ondersteund. Een `.gitignore` is daarbij alleen een hulpmiddel tegen onbedoeld toevoegen, geen toegangscontrole en geen middel om reeds gepubliceerde informatie terug te halen.

## 8. Tooling en automatische controle

De gekozen documentatieopzet gebruikt Sphinx, MyST, Furo en een externe inhoudsopgave. MyST verwerkt Markdown en kan onopgeloste documentverwijzingen signaleren. De externe inhoudsopgave maakt één navigatiestructuur mogelijk zonder dezelfde rootdocumenten opnieuw onder `docs/` te schrijven.[^17][^18]

Een uv-developmentgroep en lockfile beheren de documentatie- en controletools. Er wordt nog geen OpenT1D-simulatiepakket gedefinieerd. Dat sluit aan op uv's scheiding tussen projectafhankelijkheden en het bouwen of installeren van een project zelf.[^19]

De lokale en CI-route zijn gelijk: Python-toolingcontrole, Markdowncontrole, YAMLcontrole, CFF-validatie en een volledige HTML-build waarbij waarschuwingen falen. Sphinx biedt daarvoor een buildmodus met waarschuwingen als fouten. Daarnaast kan een afzonderlijke linkcheckbuild externe verwijzingen controleren.[^20]

Externe links worden niet verplicht voor iedere pull request opgehaald. Uitgevers kunnen robots blokkeren en websites kunnen tijdelijk onbereikbaar zijn. Het resultaat moet worden beoordeeld: een afwijzing door een uitgever bewijst niet dat een bron verdwenen is. Interne documentverwijzingen horen wel direct te slagen. Een uitzondering voor de huidige privérepository is tijdelijk en moet bij publicatie opnieuw worden beoordeeld.

De workflow gebruikt read-only repositoryrechten, volledige commit-hashes voor Actions, een looptijdlimiet en annulering van vervangen runs. Dat volgt GitHubs documentatie over minimale bevoegdheden en het vastzetten van externe Actions. Een gewone documentatiecontrole heeft geen schrijf-token, geheimen of geprivilegieerde pull-requesttrigger nodig.[^21]

Dependabot is geconfigureerd voor Actions en uv. Updates blijven reviewbare wijzigingen. De documentatie beschrijft ondersteunde ecosystemen en instellingen; een numerieke dependency-update zal later bovendien op veranderde wetenschappelijke uitkomsten beoordeeld moeten worden.[^22]

## 9. Governance en onderhoud

De huidige oprichter-maintainer wordt bij naam genoemd. De besluitvorming is openbaar in de projectgeschiedenis zodra die is gepubliceerd: gewone wijzigingen in een pull request, ingrijpende afspraken in korte besluitdocumenten. Dat is voldoende om keuzes terug te vinden zonder de ontwikkeling aan een vergaderschema te binden.

CODEOWNERS wijst een verantwoordelijk account aan. GitHub vereist passende repositorytoegang voor een code owner, en daadwerkelijke verplichte goedkeuring wordt via branchbescherming of rulesets ingesteld. Het bestand alleen beschermt de hoofdbranch dus niet.[^23]

Bij één maintainer mag de repository geen verplichte tweede goedkeurder verwachten die niet bestaat. De voorgestelde instelling vereist geslaagde controles en een reviewbaar wijzigingsspoor; onafhankelijke review wordt toegevoegd wanneer een tweede maintainer beschikbaar is. Wetenschappelijke claims die domeinbeoordeling nodig hebben blijven ondertussen begrensd tot het beschikbare bewijs.

Releases krijgen later semantische softwareversies en een betekenisvolle changelog. De gekozen versieconventie zegt niets over de omvang van een veranderde wetenschappelijke uitkomst. Een correctie in parameters of metriekdefinitie moet ook zichtbaar worden als de API gelijk blijft.[^24][^25]

Voor wetenschappelijke correcties is een aparte procedure nodig: beschrijf de oorspronkelijke claim, de fout, getroffen versies, verwachte impact en nieuwe uitkomst. Bewaar het oude resultaat met een correctieverwijzing. Reproduceerbaarheid verliest haar betekenis als oude artefacten achteraf stil worden overschreven.

## 10. Invoering en acceptatie

De eerste stap is de lokale foundation: coherente documenten, bestaande metadata, een geldige licentie, templates en controletooling. De tweede stap is activatie op GitHub: eerste commit en push, hosted CI, passende branchregels, werkende meldkanalen en eventueel documentatiehosting. Die tweede stap mag niet als voltooid worden gepresenteerd omdat er YAML-bestanden bestaan.

De feitelijke repository is tijdens de voorbereiding privé, zonder eerste commit. Issues zijn ingeschakeld en Discussions niet. Die uitgangssituatie verklaart waarom openbare clone- en documentlinks pas na toegang of publicatie bruikbaar zijn. Zij is vastgelegd in de [maintainergids](../maintenance.md).

Voor de lokale acceptatie moeten de documentatiebuild, relevante stijlcontroles, YAML-structuur en CFF-validatie slagen. Daarnaast moeten de navigatie en gegenereerde pagina's worden bekeken. Een defecte verwijzing moet de controle aantoonbaar laten falen. CI-instellingen en issueforms kunnen lokaal worden beoordeeld, maar hun uiteindelijke GitHub-gedrag wordt pas na activering bevestigd.

Na deze basis begint M0 met een werkelijk protocol en upstreamreproductie. Nieuwe beheertooling wordt toegevoegd als zij een concrete belemmering wegneemt. De repository is zo ingericht dat snelle ontwikkeling mogelijk blijft, terwijl duidelijk blijft welke uitkomsten al zijn aangetoond en welke nog onderzoek vragen.

## Bronnen

Alle bronnen zijn geraadpleegd op 12 september 2026. Projectdocumentatie zonder publicatiedatum betreft de zichtbare versie op die datum. De bronverwijzingen ondersteunen de waargenomen praktijken; de OpenT1D-keuzes zijn de hierboven gemotiveerde aanbevelingen.

[^1]: PyBaMM contributors. [PyBaMM repository and README](https://github.com/pybamm-team/PyBaMM). Projectdocumentatie, bewegende hoofdbranch.
[^2]: SciPy community. [Contribute to SciPy](https://scipy.org/contribute/). Projectdocumentatie.
[^3]: SciPy community. [SciPy Project Governance](https://docs.scipy.org/doc/scipy/dev/governance.html). Officiële ontwikkelaarsdocumentatie.
[^4]: scikit-learn developers. [Contributing](https://scikit-learn.org/stable/developers/contributing.html). Officiële bijdragegids, inclusief automated-contributionsbeleid.
[^5]: Mesa contributors. [CONTRIBUTING.md](https://github.com/mesa/mesa/blob/main/CONTRIBUTING.md). Projectdocumentatie, bewegende hoofdbranch.
[^6]: PhysiCell contributors. [PhysiCell README](https://github.com/MathCancer/PhysiCell/blob/master/README.md). Projectdocumentatie met voorbeeldprojecten en wetenschappelijke referentie.
[^7]: BioSimulators Team. [BioSimulators test suite documentation](https://docs.biosimulators.org/Biosimulators_test_suite/). Officiële beschrijving van conventies en voorbeeldarchieven.
[^8]: Daniele Procida. [Diátaxis](https://diataxis.fr/). Officiële beschrijving van vier documentatievormen.
[^9]: GitHub. [Creating a default community health file](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file). Officiële productdocumentatie.
[^10]: GitHub. [Configuring private vulnerability reporting for a repository](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository). Officiële productdocumentatie.
[^11]: GitHub. [Syntax for GitHub's form schema](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-githubs-form-schema). Officiële productdocumentatie.
[^12]: Apache Software Foundation. [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0.html). Januari 2004, officiële licentietekst.
[^13]: Free Software Foundation. [GNU GPL FAQ: mere aggregation](https://www.gnu.org/licenses/gpl-faq.html#MereAggregation). Officiële toelichting.
[^14]: Citation File Format contributors. [Citation File Format](https://citation-file-format.github.io/). Officiële formatsite en integratietoelichting.
[^15]: Citation File Format contributors. [cffconvert](https://github.com/citation-file-format/cffconvert). Officiële validatorrepository.
[^16]: Netherlands eScience Center en DANS. [FAIR software recommendations](https://fair-software.eu/). Officiële aanbevelingen.
[^17]: Executable Books contributors. [MyST Parser: cross-references](https://myst-parser.readthedocs.io/en/latest/syntax/cross-referencing.html). Officiële parserdocumentatie.
[^18]: Executable Book Project. [Sphinx External ToC: configuration and structure](https://sphinx-external-toc.readthedocs.io/en/latest/user_guide/sphinx.html). Officiële extensiedocumentatie.
[^19]: Astral. [uv: configuring projects](https://docs.astral.sh/uv/concepts/projects/config/). Officiële documentatie over projectconfiguratie en packaging.
[^20]: Sphinx developers. [sphinx-build](https://www.sphinx-doc.org/en/master/man/sphinx-build.html). Officiële builddocumentatie.
[^21]: GitHub. [Security hardening for GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions). Officiële beveiligingsdocumentatie.
[^22]: GitHub. [Dependabot options reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference). Officiële configuratiereferentie.
[^23]: GitHub. [About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners). Officiële productdocumentatie.
[^24]: Tom Preston-Werner en bijdragers. [Semantic Versioning 2.0.0](https://semver.org/). Officiële specificatie.
[^25]: Keep a Changelog contributors. [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/). Richtlijnen en conventie.
