# IV-001 — Numerieke verificatie en gevoeligheid

## Status en afbakening

De lokale numerieke campagne is uitgevoerd volgens [IV-001](internal-verification-protocol.md), los van OT-001/OT-014. De [canonieke handleiding](../internal-verification.md) beschrijft installatie, uitvoering en reconstructie. Dit rapport onderbouwt interne software- en numerieke verificatie; onafhankelijke menselijke reproductie en biologische validatie worden niet geclaimd. De geselecteerde mutatiecampagne en twee volledige robuustheidsmatrices zijn eveneens uitgevoerd.

De pilot draaide op schone commit `b35232e`; de volledige lokale matrix op schone commit `adf7cbc`. De opgeslagen manifesten bevatten volledige revisions, bron- en lockhashes. De volledige matrix is daarna op schone commit `903f72d` herhaald: alle tachtig traces zijn exact gelijk. De review corrigeerde vervolgens processtatus bij mislukte campagnes, campagne-annulering en controles op ontbrekende runtime-instellingen. Deze correcties veranderen geen numerieke berekening; gerichte foutinjecties controleren ze. De definitieve PR-controle voert de volledige matrix opnieuw uit in Linux.

## Vooraf vastgelegde grenzen

De pilot gebruikte uitsluitend adult#001/101/basal-bolus en Cambridge/PID: twee configuraties, drie solverinstellingen en afzonderlijke feedback/replay, dus twaalf volledige runs. De native toleranties zijn simglucose dopri5 `rtol=1e-6`, `atol=1e-12` en Cambridge SolverRK1_2 relatieve foutdoelstelling `0.001`. Beide worden met factor 10 en 100 verfijnd; de native buitenste cadans blijft gelijk. MPC behoudt zijn eigen Euler-predictiesolver.

De grootste native-naar-fijnste pilotafwijking was 0,00003310 mg/dL bij simglucose en 0,08648801 mg/dL bij Cambridge/PID. Gemiddelde absolute afwijkingen waren respectievelijk 0,000001575 en 0,01534833 mg/dL. De maximale exposureverschuiving was één Cambridge-interval: 0,06944445 procentpunt. De gemodelleerde insulinetoediening bleef gelijk.

Vóór de volledige matrix werden de grenzen vastgelegd in `experiments/verification/criteria.json` en een afzonderlijk freeze-artefact met pilotinvoerhashes, bronhashes en de volledige planning:

| Signaal | Technische grens | Interpretatie |
| --- | --- | --- |
| Maximale absolute glucoseafwijking | 0,1 mg/dL | Een tiende mg/dL als numerieke rapportageschaal |
| Duurgewogen gemiddelde absolute afwijking | 0,02 mg/dL | Detectie van aanhoudende kleine drift |
| Maximale absolute exposureverschuiving | 0,25 procentpunt | 3,6 minuten; ongeveer één simglucose-interval |
| Absolute verschil in dagtotaal insuline | 0,01 U | Kleine verandering door gekwantiseerde feedback; replay vereist daarnaast exacte toediening |

Dit zijn ontwikkelcriteria, geen klinische nauwkeurigheidsgrenzen. Ze zijn niet aangepast na inspectie van de volledige matrix. Historische baselines blijven onveranderd.

## Volledige lokale matrix

Tien ontwikkelconfiguraties, elk zes numerieke runs en twee extra initialisatiehistories, leveren tachtig geplande runs. Daarvan zijn 71 volledig en negen native gestopt. Alle 64 simglucose-runs en zestien Cambridge-runs blijven in de inventaris; er is geen cohort- of compartimentpooling.

| Vergelijkingen | Binnen grens | Gevoelig | Onvoldoende volledige dekking |
| --- | --- | --- | --- |
| Solververfijning, zestig paren | 48 | 6 | 6 |
| Initialisatie, twintig paren | 0 | 17 | 3 |

De zes gevoelige numerieke paren horen bij Cambridge/MPC. Bij vaste nominale insulinesturing is de maximale afwijking voor native versus factor 10 circa 0,9213 mg/dL; factor 10 versus 100 geeft 0,0501 mg/dL. De gemiddelde absolute afwijking daalt van 0,5756 naar 0,0379 mg/dL. Verdere verfijning verkleint dus het verschil, maar de gemiddelde afwijking blijft boven de vooraf gekozen grens. Native versus factor 100 geeft maximaal 0,9618 mg/dL, gemiddeld 0,6135 mg/dL en 0,2083 procentpunt exposureverschil. Maaltijden en gemodelleerde toediening blijven daarbij exact gelijk over de gezamenlijke trace, inclusief initialisatie. Dit is gevoeligheid voor de native solver, niet een wijziging van de fysiologische vergelijkingen.

Met actieve MPC-terugkoppeling is de maximale native-naar-fijnste afwijking 0,8379 mg/dL, gemiddeld 0,2571 mg/dL; het verschil in insulinetoediening bedraagt 0,01667 U. Feedbackverschillen zijn niet strikt monotoon: kwantisatie en de controllerreactie veranderen de sturing. De MPC-intern gebruikte solver is niet verfijnd. De factor-100 feedback- en replayruns zijn exact herhaald in nieuwe processen. Geen van deze resultaten bewijst nauwkeurigheid ten opzichte van een analytische of biologische waarheid.

## Initialisatie en stops

De acht varianten van adult#001/102/PID stoppen op minuut 1077 vanaf native reset. Bij nul uur initialisatie levert dat 1077 geobserveerde scoreminuten; bij 24 of 48 uur initialisatie wordt de scoredag niet bereikt. Er wordt geen nulinsulinetotaal voor een onwaargenomen scoredag gerapporteerd.

Daarnaast stopt adult#001/101/PID bij 48 uur initialisatie op minuut 2946, dus na 66 scoreminuten, bij 9,92254116 mg/dL. Een directe uitvoering met de oorspronkelijke native patiënt, sensor, pomp en PID bevestigt glucose, sensorwaarden en toediening exact tot de native `done`-vlag. De eerste diagnostische poging gebruikte SimObj, dat die vlag negeert en verder doorrekent; ook die uitvoer en de daardoor onjuiste lengteaanname in de diagnostiek zijn bewaard. Het OpenT1D-stopbeleid is niet gewijzigd.

Alle zeventien vergelijkingen met volledige scoredagen zijn gevoelig voor de voorgeschiedenis volgens deze strenge technische grenzen. Ook 24 versus 48 uur is niet algemeen stabiel. De verschillen omvatten fysiologie, opgebouwde controllerstaat en sensorhistorie; zij rechtvaardigen geen uitspraak dat één initialisatieduur biologisch juist is.

## Verificatie en bewaring

De nieuwe nominale workers zijn vergeleken met de bestaande M1/M2-uitvoering voor basal-bolus, de bekende simglucose-PID-stop, LT1-PID en LT1-MPC. Volledige tracegelijkheid, nieuwe-procesherhaling en nominale vaste-inputreplay zijn gecontroleerd. Native M0/M1/M2-reset- en historische controles blijven in CI. De nieuwe controles omvatten tevens time-out, annulering, mislukte initialisatie, gewijzigde invoerbytes en een werkelijk complete bundel die wordt afgekapt en opnieuw geïnventariseerd om specifiek onterechte voltooiing te testen.

De rapportreconstructie werkt in een Python-proces met `-S`, zonder simulatorimports. De volledige lokale matrix is hiermee bytegelijk gereconstrueerd op de gebruikte analyseversie. Bronrevision, configuraties, effectieve instellingen, waarschuwingen, fouten, probe-scripts en complete/gedeeltelijke uitvoer worden buiten Git bewaard; de oorspronkelijke numerieke inventaris in `experiments/verification/evidence-index.json` identificeert zes gecontroleerde lokale bundels, inclusief de afgebroken eerste PR #18-CI, de geslaagde definitieve PR/main-CI, beide volledige lokale matrices en de definitieve native verificatie. De definitieve native verificatie op `5807aae` slaagt ook voor ontbrekende runtime-provenance, campagne-annulering en zes opzettelijk falende workers naast zes volledige controleruns. De repositorycontrole bevat 63 tests en een succesvolle documentatiebouw. Lokale archivering is geen externe backup.

De conclusie is begrensd: nominale integratie is exact behouden; een deel van de berekeningen is solvergevoelig en initialisatieafhankelijk. Extra zelftests sluiten deze beperkingen niet weg. Menselijke data en een onafhankelijke uitvoerder blijven afzonderlijke bewijsstappen.

## Geselecteerde foutherkenning

Op schone commit `47c6980` zijn zeven vooraf gekozen bronmutaties uitgevoerd in afzonderlijke tijdelijke kopieën. Alle zeven ongewijzigde controles slagen; alle zeven mutaties worden door de bedoelde assertion ontdekt. Iedere mutationele test eindigt met exitcode 1 wegens die assertion, niet door een importfout, syntaxfout of time-out. Het oorspronkelijke werkbestand blijft bytegelijk. Patches, bronhashes, testcommando's, omgevingsgegevens en diagnostiek zijn bewaard.

| Aangebrachte fout | Controle die de fout ontdekt |
| --- | --- |
| U/h als U/min integreren: factor 60 | Onafhankelijke duurgewogen hoeveelheidfixture: 3,5 U in plaats van 210 U |
| Aankondiging meerdere keren afleveren | Tweede aanvraag op dezelfde tijd levert nul gram |
| Aankondiging drie minuten vervroegen | Nul op minuut 417, 45 g op 420, nul op 423 |
| Native sensorgeneratie tijdens maskering overslaan | De componentstream moet ook tijdens maskering doorlopen |
| Ongefilterde toekomstige informatie doorgeven | De controller ontvangt alleen de toegestane aankondiging |
| Een ontbrekend laatste punt toch als voltooid accepteren | Een vooraf geldige volledige fixture wordt afgekapt en opnieuw geïnventariseerd |
| Gewijzigde invoerbytes negeren | Whitespace verandert de bytes ondanks dezelfde JSON-waarde |

De eerder bestaande gerichte aankondigingstest liet de tijdverschuiving passeren: die controleerde totalen en eenmaal afleveren. De nieuwe test controleert de exacte intervaltoewijzing. Dit is een aangetoonde lacune in die geselecteerde test, geen uitspraak dat alle historische regressies de fout zouden missen.

De voorbereidingsproef vond ook een begrensde M2-provenancelacune: een willekeurig niet-leeg object kon de geregistreerde packagegegevens vervangen nadat de bundel consistent opnieuw was geïnventariseerd. De lezer vergelijkt deze gegevens nu exact met de opgeslagen lockfile, inclusief het verschil tussen JSON-booleans en getallen. De nieuwe regressietest begint met een geldige volledige synthetische formatfixture; het betreft geen nieuwe fysiologische referentie. Numerieke functies, native engines, controllerinstellingen en historische baselines veranderen niet.

De score is uitsluitend zeven uit zeven geselecteerde fouten. Er wordt geen totale mutatiedekking, onafhankelijke menselijke review of biologische validiteit uit afgeleid. De Linux-numerieke PR #19-run bevestigt daarnaast dezelfde 71 volledige runs, negen stops en dezelfde classificatieaantallen als de lokale campagne.

De foutencampagne is gecontroleerd met 66 repositorytests, een geslaagde documentatiebouw en een geslaagde native M2-reproductie inclusief nieuwe-processenherhaling en rapportreconstructie. Bij PR #20 bevatte de bijgehouden inventaris daarnaast de definitieve PR #19-CI, de bewaarde ontdekkingsproeven en de lokale foutencampagne: destijds negen bundels in totaal.

## Bevroren robuustheidsmatrix

De eerste volledige matrix is uitgevoerd op `c1edb9a`, de tweede op `4be1a79`. Beide freezes leggen vóór uitvoering alle 170 cases, bron- en lockhashes, parameterdefinities en daadwerkelijk gelezen native parameterwaarden vast. Er is geen tuning verricht. De tien ontwikkelconfiguraties krijgen elk zeventien afzonderlijke varianten; de eerder bekeken OT-014-evaluatie wordt niet hergebruikt. De uitvoering blijft begrensd tot de twee bestaande native families en hun oorspronkelijke controllers.

| Uitkomst | Beide volledige lokale matrices |
| --- | --- |
| Geplande runs | 170 |
| Succesvol afgerond | 151 |
| Native gestopt | 19 |
| Workerfouten of niet uitgevoerde cases | 0 |
| Geplande controllerparen | 85 |
| Volledige succesvolle controllerparen | 66 |

Alle 170 traces, sensor-audits en terminale statussen zijn tussen beide matrices exact gelijk. Een afzonderlijke verificatie op `4be1a79` vergelijkt alle tien baselines exact met de oorspronkelijke numerieke workflow en herhaalt 36 gekozen cases in nieuwe processen: alle zeventien varianten voor adult#001/101/basal-bolus en Cambridge/PID, plus twee Cambridge/MPC-varianten. Ook die traces en sensor-audits zijn exact gelijk. Het volledige rapport wordt bytegelijk gereconstrueerd in een Python-proces zonder simulatorimports.

Zeventien stops horen bij adult#001/102/PID. Zonder initialisatie zijn 1077 scoreminuten beschikbaar; bij de andere varianten ontbreekt de volledige scoredag en blijft de insulinetotaalmaat ongedefinieerd. Adult#001/101/PID stopt daarnaast na 66 scoreminuten bij 48 uur initialisatie, en bij de grotere maaltijden precies op de eindtijd van 2880 minuten, met glucose 9,555803939319874 mg/dL. Voor die laatste nieuwe stop bevestigt een onafhankelijk opgebouwd native env/controller-loop exact dezelfde glucose, CGM, aflevering en stop. De trace bevat 960 intervallen, maar de run is niet succesvol. Hij wordt daarom ondanks 1440 beschikbare scoreminuten niet gebruikt als volledig succesvol controllerpaar. Dit is eigen softwareverificatie, geen onafhankelijke menselijke reproductie.

De rangorde hangt af van de conditie en uitkomstmaat. Bij de drie volledige simglucose-paren verandert het verschil PID minus basal-bolus in gemiddelde glucose van positief onder baseline naar negatief zonder scoredag-aankondigingen. Het teken voor tijd-in-bereik keert in twee van die drie paren om. Bij Cambridge verandert MPC minus PID voor tijd boven 180 mg/dL van +3,4722 procentpunt onder baseline naar -0,7639 procentpunt bij anderhalf keer de maaltijdhoeveelheid. De bijbehorende verschillen in tijd-in-bereik zijn +37,3611 en +40,6944 procentpunt; dit is dus geen algemene omkering van een totale controllerscore. Lager gemiddelde glucose wordt niet automatisch als beter geïnterpreteerd.

Het rapport geeft verschillen en beschrijvende bereiken per model/conditie, met de volledige individuele paren en ontbrekende vergelijkingen. De Cambridge-singleton is geen cohort; de twee simglucose-seeds leveren geen populatiebetrouwbaarheidsinterval. Parametervarianten zijn geen extra patiënten. De eerder aangetoonde numerieke gevoeligheid van Cambridge/MPC blijft een beperking; deze campagne bewijst geen numerieke nauwkeurigheid van elke perturbatie en geen biologische robuustheid. Er is geen gepoolde ranglijst of algemeen robuustheidspredicaat.

De geselecteerde parameters zijn simglucose `kabs` en `kd` en Cambridge `SIT` en `tmaxG`, elk afzonderlijk op 0,9 en 1,1 van de native waarde. De native brondefinities en eenheden worden bewaard. simglucose behoudt zijn tabelbeginstaat; Cambridge berekent opnieuw het native evenwicht. Een voorbereidende proef liet zien dat Cambridge een wijzigbaar parameterobject teruggeeft: oorspronkelijke waarden worden daarom vóór wijziging gekopieerd. Controllerinstellingen en MPC-predictor blijven ongewijzigd.

## Correcties en begrenzing van de eindcontrole

De robuustheidsreader controleert alle native sensoraanroepen vóór maskering, inclusief de twee simglucose-resetmetingen op minuut nul. Een onafgesloten laatste auditregel in een onderbroken run wordt apart geteld en blijft via de invoerbytehash geïdentificeerd; zo'n regel in een succesvol gemelde run wordt afgewezen. Ontbrekende sensoraanroepen, een extra parameterwijziging, ontbrekende freeze-provenance en onterechte study-voltooiing worden met bewaarde tegenvoorbeelden gecontroleerd. De eerste resetmeting krijgt eveneens een strikte numerieke tijdcontrole: een boolean mag niet als nul dienen.

Werkelijke annulering van de robuustheidscampagne bewaart één onderbroken case en 169 niet uitgevoerde cases. De deadlinecontrole behoudt eveneens een onderbroken resultaat. Op main na PR #20 liep één bestaande M1-test incidenteel tegen zijn 0,3-seconde-deadline aan tijdens provenance-opbouw, vóór de eerste checkpoint. De eerste CI-poging is bewaard; een gerichte herhaling van alleen de repositoryjob op dezelfde commit slaagde. De test onderscheidt nu die geldige vroege timeout van een gegarandeerd ná de checkpoint opgewekte timeout. Die laatste, SIGTERM, SIGINT en SIGKILL moeten de drie geschreven minuten exact behouden. De productie-timeout is niet verruimd.

Alle interne IV-001-stappen zijn hiermee uitvoerbaar en voorzien van numeriek en softwarebewijs. De onafhankelijke menselijke M2-reproductie blijft een later open acceptatiepunt. Er zijn geen patiëntgegevens gebruikt, geen toegangsaanvragen ingediend en geen release of klinische geldigheid geclaimd.

De uitgebreide inventaris bevat zestien gecontroleerde archieven, waaronder beide robuustheidsmatrices, de volledige lokale verificatie, ontdekte fouten en correctieproeven, en de eerdere PR/main-CI inclusief de mislukte timingtest. De afsluitende repositorycontrole omvat 70 tests en een geslaagde documentatiebouw. Definitieve CI-bundels die na een PR-commit ontstaan, worden aanvullend buiten Git bewaard; geen eerdere bundel is overschreven.

De eerste volledige PR #21-CI op `097026a` slaagde voor alle zeven jobs en bevestigde in Linux eveneens 151 succesvolle runs en negentien native stops. De daaropvolgende lokale reconstructie van de gedownloade Linux-artefacten leverde exact gelijke JSON-gegevens op, maar andere bytes door de besturingssysteemafhankelijke volgorde van `inputs_sha256`. De reader sorteert deze sleutels nu canoniek. Een gerichte controle keert de volledige bestandsenumeratie om en vereist identieke rapportserialisatie. De oorspronkelijke Linux-uitvoer en de afwijkingsproef blijven bewaard; geen numerieke waarde of historische baseline is gewijzigd.
