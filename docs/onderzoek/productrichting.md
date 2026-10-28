# Productrichting: een gemeenschappelijk T1D-onderzoekslaboratorium

**Onderzoeksdatum: 25 oktober 2026.** Dit rapport onderbouwt de productrichting
van OpenT1D. Het [productdocument](../product-laboratory.md) is de canonieke
beschrijving van requirements; de [roadmap](../../ROADMAP.md) is het canonieke
implementatieplan. Onderstaande ontwerpkeuzes en gebruiksproeven zijn
onderzoeksconclusies, geen aanvullende implementatietoezeggingen.

## Vraag, aanpak en bewijskracht

De centrale vraag is welke waarde OpenT1D toevoegt wanneer bestaande projecten
al simulatie, controllers, glucosevoorspelling en biologische analyse leveren.
De kans ligt in een samenhangend laboratorium waarin onderzoekers geschikte
modellen, methoden, scenario's en observaties combineren, vergelijken en later
opnieuw gebruiken. De wetenschappelijke algoritmen hoeven daarvoor niet nieuw
te zijn. De praktische winst moet blijken uit minder verbindingswerk bij de
tweede engine, tweede methode en tweede onderzoeksvraag.

Drie onderzoeksagents onderzochten parallel wetenschappelijke
interoperabiliteit, onderzoekerswerkstromen en productervaring/adoptie. De
hoofdagent onderzocht architectuur, kwaliteit, distributie en onderhoud en
integreerde de bevindingen. Dit is onderzoek door drie agents plus de
hoofdagent, geen onafhankelijke menselijke of wetenschappelijke review.
Geraadpleegd zijn repositorycode en documentatie, oorspronkelijke publicaties,
officiële documentatie en upstream issues. Bronlinks staan bij hun claims.

Er zijn geen onderzoekers geïnterviewd, partners geworven, private
gezondheidsgegevens geopend of nieuwe wetenschappelijke benchmarks uitgevoerd.
De beschreven gebruikersbehoeften en kostenbesparingen zijn hypotheses.
Publieke documentatie toont dat een functie wordt aangeboden; zij bewijst geen
superioriteit. Een preprint en een open issue hebben een andere bewijskracht
dan een gerepliceerde studie of onafhankelijke producttest.

## Uitgangspositie van OpenT1D

De bestaande [architectuur](../architecture.md) omvat begrensde native
M1/M2-tracks en onderzoekerintakes voor controllers, voorspellers,
secretiebronnen en prognostische modellen. Daarnaast zijn er een lokale GUI,
runtime-locks, campagnes, bronregistratie, bewaarde mislukkingen en
rapportreconstructie. Dat zijn bruikbare bouwstenen voor een laboratorium.
Een stabiele algemene modelinterface en gepubliceerde installeerbare SDK zijn
nog geen huidige capabilities.

De [algemene taakentry](../local-workflow-entry.md) registreert tien routes.
De registry, checks en dispatch bevatten taakafhankelijke keuzes. De
[campagnes](../maintained-campaigns.md) beheren herhaalde M4-studies, maar
vormen geen algemene keten van import, fit, simulatie en analyse. De twee
[MMTT-taken](../mmtt-sampling.md) tonen al concreet hergebruik van één
analysekern. De grootste productachterstand is de overgang tussen zulke taken:
een bruikbaar fitresultaat, observatieartefact of scenario moet een volgende
vraag kunnen voeden zonder nieuw projectbeheer en rapportparsing.

Enkele grenzen zijn bepalend voor de beoordeling. De huidige
[M2-vergelijking](../m2-tutorial.md) gebruikt afzonderlijke native tracks met
verschillende controllers, signalen en parameterisaties. Zij voert niet één
gemeenschappelijke controller uit op twee verwisselbare engines en is geen
geïsoleerd experiment naar alleen het effect van fysiologie. De
[M5-archiefbibliotheek](../research/m5-archive-library-verification.md) biedt
inzage en verificatie van bewaarde prognostische rapporten, geen algemene
M5-uitvoerings-GUI. Veel huidige voorbeelden zijn synthetisch en intern
geverifieerd; onafhankelijke gebruiksacceptatie en toepassingsgebonden
empirisch bewijs blijven afzonderlijk open.

## Het bestaande functionele landschap

| Project of ecosysteem | Bestaande functie | Betekenis voor OpenT1D |
| --- | --- | --- |
| [simglucose](https://github.com/jxx123/simglucose) | Fysiologische simulator, virtuele profielen, controllers, scenario's, batchuitvoering en Gymnasium | Een native engine hergebruiken; geen nieuwe kopie van dezelfde simulatie bouwen |
| [LoopInsighT1](https://lt1.org/method/) | Meerdere modellen en componenten, controllers, sensoren en interactieve experimenten | Zowel native host als componentbron; meer dan een visualisatietool |
| [APS_TestBed](https://github.com/UVA-DSA/APS_TestBed) | Meerdere simulators, controllers en foutinjectie | Twee engines en storingsscenario's vormen op zichzelf geen nieuwe bijdrage |
| [RL4T1D](https://github.com/RL4H/RL4T1D) en [GluCoEnv](https://github.com/RL4H/GluCoEnv) | RL-omgevingen, algoritmen en trainingsexperimenten | Training en inference aansluiten; geen algemeen RL-framework herbouwen |
| [GluPredKit](https://github.com/replicahealth/GluPredKit) | Gegevensverwerking, modeltraining, voorspelling, evaluatie en rapporten | Een bestaande voorspelketen integreren in plaats van een parallelle modelcatalogus onderhouden |
| [ReplayBG](https://gcappon.github.io/py_replay_bg/documentation/twinning_procedure.html) | Persoonlijke parameterschatting via MAP/MCMC en [replay](https://gcappon.github.io/py_replay_bg/documentation/replaying.html) met gewijzigde inputs | Observaties, fit en scenario-uitvoering verbinden zonder de schattingsmethode opnieuw te implementeren |
| [BioSimulators](https://docs.biosimulators.org/Biosimulators_test_suite/) | Capabilities, standaarden en conformatietests voor simulatoren | Algemene conventies en validators hergebruiken; eigen werk concentreren op T1D-betekenis |

De voorspelruimte is inmiddels bijzonder druk. [GlucoBench](https://arxiv.org/abs/2410.05780)
biedt datasets, taken en referentiemodellen. De preprint
[MetaboNet-Bench van juni 2026](https://arxiv.org/abs/2606.18640) behandelt
multimodale voorspelling, meerdere gegevensbronnen en subgroepen. De preprint
[From Prediction to Practice van mei 2026](https://arxiv.org/abs/2605.00645)
combineert taakgerichte voorspeldevaluatie met simulatorinterventies.
Meer modellen, meer datasets of een interventiebenchmark zijn daarom geen
voldoende onderscheidende productbelofte.

Ook biologische analyse heeft bestaande oplossingen.
[ISEC](https://pubmed.ncbi.nlm.nih.gov/8894385/) en het open R-pakket
[`insulin.secretion`](https://cran.r-project.org/web/packages/insulin.secretion/index.html)
bieden C-peptidedeconvolutie; [AOMM](https://www.nanomath.us/aomm) biedt
Windows-batchanalyse van maaltijd- en glucosetolerantietests. De
[AOMM-publicatie](https://journals.sagepub.com/doi/10.1177/19322968251365274)
beschrijft validatie tegenover handmatig geëxtraheerde referentieresultaten
uit een eerdere studie. Een
vergelijking met OpenT1D vereist nog overeenkomende endpoints, toegankelijke
software en passende gebruiksrechten. Een moderne deconvolutiefunctie of GUI
is op zichzelf geen wetenschappelijke vernieuwing.

## Waar een geïntegreerd laboratorium waarde kan leveren

De relevante producteenheid is een onderzoek dat wordt uitgebreid. Een
controlleronderzoeker wil dezelfde vraag in een andere engine onderzoeken.
Een modelleur wil een absorptiecomponent vervangen en een eenvoudiger
parameterwijziging als comparator behouden. Een dataonderzoeker wil dezelfde
cohortselectie gebruiken voor een tweede voorspeller. Een biomedisch analist
wil na een gevoeligheidsanalyse onderzoeken welke meetmomenten informatie
toevoegen. Deze rollen hebben gemeenschappelijk beheer nodig, maar geen
identieke wiskundige interface.

Een gemeenschappelijke route kan lopen van vraag en project naar bronnen,
compatibiliteit, scenario/cohort, ontwikkeling, bevroren evaluatie, uitvoering,
vergelijking en overdracht. Een Pythongebruiker kan in een notebook beginnen
en hetzelfde plan in de GUI volgen. Een collega kan een toegestane export
openen en de analyse controleren. Nieuwe domeinen leveren hun eigen
wetenschappelijke payload en rapportsecties, terwijl projectopslag,
uitvoeringsstatus en archiefvoorzieningen worden hergebruikt.

Dit is een producthypothese met toetsbare baten. Meet hoeveel extra code,
configuratie, installatie, hulp en interpretatiewerk nodig zijn voor de tweede
en derde taak. Vergelijk met competente bestaande tools en een goed notebook,
inclusief voorbereiding en onderhoud aan beide kanten. Minder stappen zijn
alleen winst wanneer de gebruiker ook een correct resultaat en juiste
interpretatie bereikt. Een auditfunctie ondersteunt dit werk; zij vervangt
niet de bredere laboratoriumambitie.

## Wetenschappelijke compatibiliteit als kernfunctie

Compatibiliteit moet betrekking hebben op concrete mogelijkheden. Een engine
kan geschikt zijn voor een basal-ratecontroller en ongeschikt voor een
pompgeschiedenisafhankelijke policy. Een offline estimator hoeft geen
tijdstapfunctie te verzinnen. Hele-engine-integratie behoudt solver, toestand
en componentlifecycle. Biologische compositie is een apart integratieniveau,
met expliciete eigenaar voor absorptie, secretie, transit, extractie,
klaring, vertraging en meetruis.

Aan iedere relevante grens horen eenheid, compartiment, toedieningsroute,
hoeveelheid versus rate, whole-body/per-kg-schaal, tijdsteun en beschikbaarheid.
Solverstappen, sensoracquisitie, ontvangst, controllerbeslissing en aflevering
zijn verschillende klokken. Een vijfminutenpolicy wordt geen equivalente
drieminutenpolicy door alleen de actie-eenheid om te rekenen. De bestaande
[oref0-routebeoordeling](../research/c1-comparator-route.md) laat zo'n
praktische incompatibiliteit zien. Een adapter moet die uitleggen voordat
een langdurig experiment begint.

Gelijke grammen betekenen evenmin een gelijke maaltijd wanneer de ene engine
een instantane bolus en de andere een opnameprofiel gebruikt. Plasma,
interstitium en CGM zijn verschillende signalen; puntmetingen en
intervalgemiddelden zijn niet uitwisselbaar. Een scenario legt zowel bedoeling
als effectieve native vertaling vast. Virtueel profiel 1 in twee engines is
geen gepaarde persoon. Identieke seeds maken verschillende toevalsprocessen
niet automatisch gepaard.

Vergelijk daarom eerst passende contrasten binnen engines en onderzoek
vervolgens gevoeligheid voor enginekeuze. Bewaar tuningbudget, volledige
geplande roosters, niet-ondersteunde cellen en mislukkingen. Onderscheid
numerieke, parameter-, meet-, toevals-, structuur- en populatieonzekerheid.
Een synthetische parameterstress is geen empirische populatieverdeling.
Een technisch geldige compositie erft de biologische validiteit van haar
onderdelen niet automatisch.

Een adapterconformatietest moet native en aangepaste uitvoering onder
betekenisvolle stimuli vergelijken en reset, events, aflevering, causaliteit,
fouten en numerieke verfijning toetsen. Bestandsintegriteit helpt daarbij,
maar vervangt deze controles niet. De bestaande
[absorptievervanging](../lit002-tutorial.md) is een bruikbaar uitgangspunt:
zij vergelijkt een componentverandering met native gedrag en een eenvoudiger
parameteralternatief.

## Gegevens, voorspelling, kalibratie en biologische analyse

Een gedeelde gegevenslaag moet tijdreeksen, events, bezoeken en afgeleide
artefacten kunnen onderscheiden. Bewaar bronidentiteit, werkelijke meettijden,
beschikbaarheid waar bekend, units, missingness, censoring, context en
participant-/visitverband. Eén vijfminutenrooster kan niet alle taken dragen.
Onbekende maaltijd- of insulinegegevens mogen niet stilzwijgend als nul worden
geïnterpreteerd om een importer te laten slagen. ReplayBG's
[gegevensvereisten](https://gcappon.github.io/py_replay_bg/documentation/data_requirements.html)
illustreren hoeveel semantiek achter een ogenschijnlijk eenvoudige tabel zit.

Bij forecasting horen preprocessing, fit, modeltoestand en evaluatie als
herkenbare fasen bij elkaar. Een bevroren model kan in zijn eigen omgeving
worden geëvalueerd; aanpassen van de rapportage hoeft geen training te
herhalen. Bewaar fitdata, splits en eerdere evaluatietoegang. Een nieuwe map
maakt bekende gegevens niet ongezien. Imports van bestaande voorspellingen
maken heranalyse mogelijk, maar bewijzen niet achteraf welke informatie het
model werkelijk gebruikte.

De [reproduceerbaarheidsstudie van Lu et al. uit september 2026](https://journals.plos.org/digitalhealth/article?id=10.1371%2Fjournal.pdig.0001633)
onderzocht 67 papers en acht modellen. Naast technische en statistische
reproduceerbaarheid onderzocht zij prestaties op andere gegevensbronnen.
Daarbij werden modellen per dataset opnieuw getraind met vijfvoudige
crossvalidatie; dit was geen bevroren modeltransport vanuit OhioT1DM. Onze
ontwerpconclusie is dat passende onafhankelijke evaluatie nodig blijft en
beoogd bevroren cohorttransport een afzonderlijke toets vraagt. De studie
bewijst geen vraag naar OpenT1D; synthetische platformtests stellen geen
menselijke voorspelprestatie vast.

Kalibratie voegt een andere keten toe: observaties en meetmodel, parameters,
fit, onzekerheid, identificeerbaarheid en toetsing onder andere condities.
Een betere CGM-fit identificeert niet automatisch absorptie of leverextractie.
Hergebruik bestaande schatters zoals ReplayBG of geschikte
[PEtab-tooling](https://petab.readthedocs.io/en/latest/). Een fitparameter is
gebonden aan zijn modelstructuur; hij wordt niet vanzelf geldig in een andere
engine. Historische replay met gegeven behandeling bewijst op zichzelf geen
counterfactueel behandelingseffect.

MMTT is een waardevolle tweede domeinproef doordat zij inverse analyse en
assays toevoegt. De huidige [observatieanalyse](../observation-analysis.md)
schat totale whole-bodysecretie inclusief basaal over 0–120 minuten, met
follow-up minus baseline, onder vaste synthetische kinetiek. Dat is een andere
uitkomst dan gemeten C-peptide-AUC. Toets daarom afzonderlijk de meerwaarde
van deze modelstap tegenover eenvoudiger passende maten, en de productwaarde
tegenover een notebook met dezelfde estimator. Notebookpariteit bewijst geen
extra wetenschappelijke waarde.

Voor empirische toepassing zijn geschikte gekoppelde bezoeken, werkelijke
sampletijden, assay/LOQ, medicatie- en niercontext, gerechtvaardigde kinetiek
en een passend interpretatieplan nodig. De
[standaardkinetiek van Van Cauter](https://pubmed.ncbi.nlm.nih.gov/1551497/)
verleent synthetische instellingen geen individuele T1D-validiteit. Bestaand
[onderzoek naar 90-minutenmetingen](https://pmc.ncbi.nlm.nih.gov/articles/PMC3554273/)
onderbouwt evenmin automatisch het longitudinale secretie-endpoint. De
[huidige empirische voorbereiding](../research/mmtt-sampling-empirical-plan.md)
houdt deze eisen terecht apart van softwareontwikkeling.

## Architectuur, standaarden en hergebruik

De aangewezen richting is een kleine gedeelde project-, experiment-,
capability-, uitvoerings- en resultaatlaag met taakgebonden wetenschappelijke
contracten. Python-API, CLI en GUI gebruiken dezelfde diensten. Migreer
bestaande routes stapsgewijs door deze kern en behoud hun historische
readers. Een nieuwe abstractie naast onveranderd routebeheer zou juist een
tweede codebase creëren.

Een multi-environment-adapter kan een bestaande Pythonomgeving, Nodeproces,
Rscript, native executable of container aanroepen. Begin met complete runs
en batches. Tijdsgekoppelde componenten vragen een afzonderlijk contract;
een bestandsworkflow mag geen nauw gekoppelde ODE-feedback nabootsen zonder
numerieke koppelingsanalyse. Een plugin moet beschrijfbaar zijn zonder het
model bij alleen openen van een project uit te voeren.

Gebruik een algemeen resultaatmanifest met taakgebonden tabellen voor
trajecten, events, parameters, metrics, coverage en attempts. Iedere metric
draagt betekenis, versie, eenheid, steun en aggregatie-eenheid. Verschillende
taakuitkomsten mogen in dezelfde bibliotheek staan zonder gezamenlijke
kwaliteitsranglijst. Gewone data-/figuurexport maakt het lab ook bruikbaar
naast notebooks en bestaande analysetools.

Standaarden vervullen verschillende rollen:

| Grens | Passend hulpmiddel | Te behouden beperking |
| --- | --- | --- |
| Uitvoerbare modeluitwisseling | [FMI](https://fmi-standard.org/docs/3.0.2/) | Een FMU bepaalt niet het co-simulatiealgoritme of biologische ownership |
| Modelrepresentatie | [SBML](https://sbml.org/documents/specifications/) en [CellML](https://www.cellml.org/specifications/cellml_2.0/index) | Gelijke syntax of units bewijst geen passende schaal of populatie |
| Experiment en bundel | [SED-ML](https://sed-ml.org/documents/sed-ml-L1V5.pdf) en [OMEX](https://github.com/combine-org/combine-specifications/blob/main/specifications/omex.md) | Ondersteun een expliciete subset; willekeurige callbacks worden niet automatisch portable |
| Kalibratie | [PEtab](https://petab.readthedocs.io/en/latest/) | Geen vervanging voor een causale controllerinterface |
| Uitvoeringsherkomst | [Workflow Run RO-Crate](https://www.researchobject.org/workflow-run-crate/profiles/) | Metadata is geen bewijs van correcte uitvoering of geldige fysiologie |

Voeg een bridge toe wanneer zij een nuttige donor of uitwisseling ontsluit.
Alle engines eerst naar één standaard vertalen is geen voorwaarde voor
gemeenschappelijke laboratoriumwaarde. Zelf te bouwen zijn vooral
T1D-semantiek, compatibiliteitscontroles, experimentflow en eerlijke
vergelijkingen. Solvers, inferentie, plotting en generieke schedulers zijn
geschikte hergebruikdoelen.

Voor grotere studies bieden [Snakemake](https://snakemake.readthedocs.io/en/stable/executing/cli.html)
en [Nextflow](https://docs.seqera.io/nextflow/executor) bestaande executorgrenzen.
Koppel eerst één backend aan een echte studie; bouw geen eigen clusterbeheer.
Beperk resources en voorkom oversubscriptie bij intern parallelle fitters.
Behoud een eigen volledig gepland-run-/attemptregister: de beschreven
[Nextflow-lineage](https://docs.seqera.io/nextflow/tutorials/data-lineage)
neemt gefaalde en afgebroken taken niet op.

Cache-identiteit geldt per stap. Veranderde metrics vereisen nieuwe analyse,
maar ongewijzigde simulatie- of voorspelartefacten kunnen hergebruikt worden.
Veranderde inputs, scenario's, modellen of runtimes raken de bijbehorende
upstreamstappen. Een cachehit is geen onafhankelijke replicatie. Native
checkpointing en opnieuw uitvoeren zijn verschillende capabilities.
[MLflow](https://mlflow.org/docs/latest/ml/tracking) kan bestaande teams
ondersteunen met runs en modelregistratie; een centrale trackingdienst hoeft
geen verplichte dependency van iedere lokale gebruiker te zijn.

## Werkbank, installatie en toegankelijkheid

Een project buiten de installatie/checkout is een stabielere gebruikseenheid
dan een verzameling uitvoermappen. De werkbank moet een vraag, bronnen,
conceptplan, freeze, uitvoering en vergelijking begrijpelijk verbinden.
Programmeerexperts behouden toegang tot scripts en volledige configuraties;
andere onderzoekers hoeven geen Pythonobjecten of hashes te beheren om een
ondersteunde taak uit te voeren. Domeinbeperkingen verschijnen bij keuzes
die zij beïnvloeden.

De voorbeelden van [Galaxy history](https://training.galaxyproject.org/training-material/topics/galaxy-interface/tutorials/history/tutorial.html)
en de [nf-core launcher](https://nf-co.re/docs/nf-core-tools/cli/pipelines/launch)
tonen herbruikbare patronen voor geschiedenis en configuratie. Zij bewijzen
geen vraag naar een nieuwe OpenT1D-interface. Gebruik zulke patronen zonder
een IDE of volledige collaboratiesuite na te bouwen.

De geselecteerde Windowsuitkomst van [OT-058](../../ROADMAP.md#planned-windows-installer-ot-058)
is één installer en launchshortcut, zonder dat de gebruiker Git, WSL/Ubuntu,
Python, dependencies of terminalcommando's hoeft te beheren. De huidige
POSIX-afhankelijke lifecycle vereist daarvoor productwerk. Een native backend
is een te onderzoeken optie; appbeheerde WSL is hiermee niet bij voorbaat
verboden. De gekozen oplossing moet de gebruikersuitkomst en echte
clean-Windowschecks halen. Voorbereid macOSgebruik bewijst geen
Windowsinstallatie.

Toegankelijkheid hoort bij de gewone flow: toetsenbordbediening, focus,
leesbare status, labels, contrast en fouten met herstelactie. Gebruik
[WCAG 2.2](https://www.w3.org/TR/WCAG22/) als expliciet beoordelingskader;
claim geen conformiteit zonder toetsing. Tutorials, taakgidsen,
API-referentie en uitleg hebben verschillende functies, zoals
[Diátaxis](https://diataxis.fr/start-here/) beschrijft. Test zelfstandig
installeren, correct uitvoeren en heropenen met werkelijke onderzoekers en
registreer ook hulp en interpretatiefouten.

## Kwaliteit, privacy en houdbaarheid

Maak uitvoering, volledigheid, integriteit, rapportreconstructie en
wetenschappelijke acceptatie afzonderlijk zichtbaar. Reconstructie controleert
de bewaarde selectie en analyse; zij reproduceert niet vanzelf een arbitrair
aangeleverd algoritme. Een onafhankelijke modelheruitvoering en een
modelspecifieke arithmetic replay zijn sterkere, afzonderlijke garanties.
Een correct gereconstrueerd mislukt onderzoek blijft mislukt.

Combineer snelle contracttests met native regressies, numerieke oracles,
platformlifecycle en GUI/CLI-pariteit. Meer tests zijn geen vervanging voor
individuele bron- en numericaliteitscontroles. Behoud passende vertrouwde
readers voor historische archieven; een nieuwe appversie mag oude plannen
niet stil wijzigen. API-, protocol-, parameter-, metric- en readerversies
beantwoorden verschillende vragen.

Onderzoekercode draait momenteel met lokaal vertrouwen; workers en deadlines
vormen geen sandbox. Een gedeeld project openen mag geen callback, notebook
of installatiehook starten. Containers bieden ook geen automatische garantie
voor vijandige gedeelde uitvoering; zie [Docker security](https://docs.docker.com/engine/security/).
Datatoegang, netwerk, secrets en resources moeten passen bij de gekozen
backend en gebruikssituatie.

Private brondata, individuele uitkomsten en logs horen apart van een
deelbaar protocolpakket. De huidige native archieven bewaren juist inputbytes
en traces. Een deelbare export moet bewust toegestane onderdelen kiezen;
hashes anonimiseren gegevens niet. Zonder passende datatoegang kan een collega
metadata of vrijgegeven analyse controleren, maar het empirische resultaat
niet volledig opnieuw uitvoeren. Een synthetisch fixture maakt de route
testbaar zonder dat resultaat te vervangen.

Distributierechten gelden per asset: code, parameters, checkpoints, data en
binaries kunnen andere voorwaarden hebben. Procesisolatie is geen algemene
licentie-uitzondering. Behoud bronidentiteit, notices en distributiescope en
beoordeel passende rechten vóór bundeling; zie de [licentiegids](../licensing.md).
Release-identiteit en eventuele citaties moeten daadwerkelijk bestaan.

Houd officiële, experimentele, community- en historische integraties
herkenbaar. Een ondersteunde adapter vraagt onderhoudseigenaarschap,
upstreambeleid, conformancefixtures en documentatie. Ondersteunde kernomgevingen
en expliciete historische locks kunnen naast elkaar bestaan; het
[Scientific Python-onderhoudskader](https://scientific-python.org/specs/spec-0000/)
is een referentie, geen reden om onderzoeksbaselines stil te vervangen.
Meet supportlast en opslaggroei voordat extra engines of diensten worden
toegezegd. [JOSS-review](https://joss.readthedocs.io/en/latest/reviewer_guidelines.html)
kan later helpen, maar vervangt geen aangetoonde onderzoekstoepassing.

## Welke productproeven de richting kunnen beoordelen

Een overtuigende proef omvat een passende controllerstudie via twee engines,
gevolgd door een tweede controller en vraag zonder nieuwe kern- of GUIroute.
Een andere proef gebruikt dezelfde projectvoorzieningen voor MMTT-gevoeligheid
en samplingverlies. Een forecastroute toetst vervolgens fit/evaluatie en eigen
runtimes. Een collega moet een toegestane overdracht kunnen openen en een
rapport reconstrueren; een onderbroken campagne moet haar volledige
pogingengeschiedenis behouden. Dit zijn gebruikscriteria, geen extra
werkpakketten naast de roadmap.

Meet tijd tot eerste correct resultaat, hulp, nieuwe verbindingscode,
instelwerk, kritieke interpretatiefouten, handoff en werkelijk hergebruik bij
een volgende studie. Leg grenzen vooraf per proef vast; verzin geen universeel
percentage tijdswinst. Als iedere nieuwe vraag opnieuw projectbeheer,
supervisie en rapportlogica nodig heeft, vraagt de kern consolidatie. Als
een bestaande tool de volledige taak beter oplost, kan een upstreambijdrage
of kleine adapter waardevoller zijn dan een nieuwe interne functie.

Immunologie, celtherapie, multiscale modellen, surrogates, optimalisatie en
cloudteams blijven mogelijke richtingen. Toelating vraagt telkens een
concrete onderzoeksvraag, geschikte bron en rechten, verdedigbare koppeling,
passende evaluator en onderhoudscapaciteit. Een celmodel wordt niet door een
eenhedenconversie een menselijke whole-body T1D-engine. Een synthetische
prognose is geen therapie- of immuunsimulatie. Zulke open evidencevragen hoeven
bruikbare interne platformontwikkeling niet te blokkeren; zij begrenzen de
claims van iedere uitbreiding.

De hoofdconclusie is daarom een breed maar toetsbaar productdoel: bestaande
modellen en methoden samen bruikbaar maken voor opeenvolgende onderzoeken,
met hun verschillen behouden. De concrete requirements horen in het
[productdocument](../product-laboratory.md); selectie, afhankelijkheden en
implementatie blijven vastgelegd in de [roadmap](../../ROADMAP.md).
