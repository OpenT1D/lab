"""Session goals, kept separate from a moderator's expected scientific outcomes."""

TASKS = (
    (
        "context",
        (
            "Compare the two supplied secretion models under all three starting con"
            "ditions. Explain the inputs and time window."
        ),
        (
            "Vergelijk de twee meegeleverde secretiemodellen onder de drie begincon"
            "dities. Leg uit welke invoer en tijdsduur worden gebruikt."
        ),
    ),
    (
        "execute",
        "Make the experiment ready and run it. Say when you need help.",
        "Maak het experiment klaar en voer het uit. Geef aan wanneer je hulp nodig hebt.",
    ),
    (
        "return",
        "Visit another view while the experiment runs, then find the ongoing operation again.",
        "Ga tijdens het rekenen naar een ander scherm en vind het lopende experiment terug.",
    ),
    (
        "find_result",
        "Leave the study view, then find your own result.",
        "Verlaat het experimentscherm en vind je eigen resultaat terug.",
    ),
    (
        "interpret_complete",
        (
            "Explain the graph, its units, the accepted/planned cases and the concl"
            "usions this result supports."
        ),
        (
            "Leg de grafiek, eenheden en geslaagde/geplande berekeningen uit. Wat k"
            "un je uit dit resultaat concluderen?"
        ),
    ),
    (
        "saved_analysis",
        "Check the saved analysis and download the report. Explain what was checked.",
        "Controleer de opgeslagen analyse en download het rapport. Leg uit wat werd gecontroleerd.",
    ),
    (
        "interpret_partial",
        "Inspect the supplied interrupted report. Explain what is available and what is missing.",
        "Bekijk het meegeleverde onderbroken rapport. Leg uit welke informatie er wel en niet is.",
    ),
    (
        "recover",
        (
            "Enter an invalid Source ID, check it, then restore the original value. "
            "Describe the error and recovery."
        ),
        (
            "Vul een ongeldige Source ID in, controleer deze en herstel de oorspronk"
            "elijke waarde. Leg de foutmelding uit."
        ),
    ),
    (
        "cancel",
        "Use a separate fresh run to try cancellation. Keep the completed study.",
        "Start een apart experiment om annuleren te proberen. Bewaar het voltooide experiment.",
    ),
    (
        "accessibility",
        (
            "Try one navigation and disclosure using only the keyboard, and one tas"
            "k in a narrow window. Record which device or window was used."
        ),
        (
            "Navigeer en open een onderdeel met alleen het toetsenbord. Probeer ook"
            " een taak in een smal venster. Noteer welk apparaat of venster is gebr"
            "uikt."
        ),
    ),
    (
        "installation",
        (
            "Separately assess installation and startup on the tester's own compute"
            "r. A preinstalled session does not assess this task."
        ),
        (
            "Test installeren en starten op de eigen computer apart. Met een vooraf"
            " geïnstalleerde omgeving is deze taak niet getest."
        ),
    ),
)


def goals(language):
    return [{"id": item[0], "goal": item[2 if language == "nl" else 1]} for item in TASKS]


MMTT_TASKS = (
    (
        "installation",
        "Installation: could you prepare the software on your own computer? "
        "Record help and errors.",
        "Installeren: lukte het om de software op je eigen computer klaar te zetten? "
        "Noteer hulp en fouten.",
    ),
    (
        "startup",
        "Startup: could you check setup, open the interface and later stop and reopen it?",
        "Starten: lukte controleren, openen en later stoppen en opnieuw openen?",
    ),
    (
        "mmtt_assumptions",
        "Task 1 — Does the conclusion about a change in estimated insulin secretion depend on "
        "analysis assumptions? Use the second supplied paired meal-test example with its supplied "
        "settings. Find the results and explain your conclusion using the report. Later find it "
        "again, check the saved analysis and save the report. Say what you do not understand.",
        "Opdracht 1 — Hangt de conclusie over verandering in geschatte insulinesecretie af van "
        "de analyse-aannames? Insulinesecretie betekent hoeveel insuline het lichaam afgeeft. "
        "Gebruik het tweede meegeleverde voorbeeld met twee maaltijdtesten en de bijbehorende "
        "instellingen. Zoek de resultaten en leg je conclusie uit met het rapport erbij. Vind "
        "het resultaat later terug, controleer de opgeslagen analyse en bewaar het rapport. "
        "Vertel wat je niet begrijpt.",
    ),
    (
        "mmtt_sampling",
        "Task 2 — What changes when measurement times within the same meal test are omitted? "
        "Use the first supplied fewer-measurement-times example with its supplied settings. "
        "Compare the full and reduced schedules over the same time window. Explain what "
        "changes and what you can conclude. Later reopen and check the saved result and save "
        "the report. Say what you do not understand.",
        "Opdracht 2 — Wat verandert als meetmomenten binnen dezelfde maaltijdtest wegvallen? "
        "Gebruik het eerste meegeleverde voorbeeld voor minder meetmomenten met de "
        "bijbehorende instellingen. Vergelijk alle metingen met de kleinere meetschema’s "
        "over dezelfde tijdsduur. Leg uit wat verandert en wat je daaruit kunt concluderen. "
        "Open en controleer het opgeslagen resultaat later opnieuw en bewaar het rapport. "
        "Vertel wat je niet begrijpt.",
    ),
)


def session_goals(language, session="m4"):
    if session == "m4":
        return goals(language)
    if session != "mmtt":
        raise ValueError("Choose m4 or mmtt session goals")
    return [{"id": item[0], "goal": item[2 if language == "nl" else 1]} for item in MMTT_TASKS]


def participant_goals(items):
    """Keep setup feedback separate from the two MMTT participant assignments."""
    if any(item["id"] == "mmtt_assumptions" for item in items):
        return [item for item in items if item["id"].startswith("mmtt_")]
    return items
