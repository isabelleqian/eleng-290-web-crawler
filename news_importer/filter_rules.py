"""Filter rules and taxonomy classification for routing apps research corpus.

Separates curated in-scope research documents (algorithmic navigation, cut-through
traffic, municipal traffic calming, platform governance) from off-topic noise
(crime blotters, consumer gadget how-tos, commercial market forecasts, etc.).
"""

import re
from typing import Any

# --- Affirmative Research Pillars ---

RE_ROUTING_CORE = re.compile(
    r"\b(waze|google maps|apple maps|mapquest|here wego|navigation app[s]?|"
    r"routing app[s]?|traffic app[s]?|turn-by-turn navigation|in-car navigation|"
    r"gps routing|routing algorithm[s]?|connected citizens program|waze for cities|"
    r"project green light|in-dash navigation|car navigation system[s]?)\b",
    re.I,
)

RE_CALMING_CORE = re.compile(
    r"\b(cut-through|cut through|rat run[s]?|rat-run[s]?|traffic calm\w*|"
    r"speed hump[s]?|speed bump[s]?|speed cushion[s]?|speed table[s]?|chican\w*|"
    r"traffic diverter[s]?|diverter[s]?|resident[s]?-only|no through traffic|"
    r"closed to through traffic|turn restriction[s]?|turn ban[s]?|neighborhood cut-through|"
    r"residential cut-through|side street[s]? cut-through|side street traffic|"
    r"local traffic only|one-way street[s]?|road diet[s]?|through-traffic)\b",
    re.I,
)

RE_GOVERNANCE_CORE = re.compile(
    r"\b(waze partnership|data-sharing partnership|traffic signal optimization|"
    r"app poisoning|poisoning waze|regulating navigation|regulate navigation|"
    r"regulate maps|leonia|fremont.*traffic|krekorian.*waze|takoma park|"
    r"tracking police.*waze|police checkpoint[s]?.*waze|dwi checkpoint[s]?.*waze|"
    r"dui checkpoint[s]?.*waze|gps task force)\b",
    re.I,
)

# --- Exclusion Signatures ---

RE_NOISE_SUBJECT = re.compile(
    r"\b(website design|web design|emergency go bag|failed gop|tennis player|"
    r"personal injury|law firm|bbq|ribbon cutting|grand opening|obituary|dies at|"
    r"savannah bananas|fsu football|spirit week|commencement parking|game day traffic|"
    r"stadium parking|parking/traffic advisory|parade route|unhoused|anti-homeless|"
    r"hostile architecture|patent[s]? infring|proof-of-delivery|trimble|"
    r"construction materials|mcleod software|pc miler|pc\*miler|covered bridge|"
    r"drone market|cagr|allied market research|research and markets|global industry snapshot|"
    r"delhi.*pollution|animal services|cia facility|sand quarry|ocean data portal|"
    r"figma nyse|via transportation nyse|wipo publishes patent|patent of|sentenced|"
    r"parkmobile|paybyphone|web 2\.0|business\.gov|foreign-trade zone|garmin.*avionics|"
    r"dodge durangos|fairfield metro station|renaming.*route|lane closure scheduled|"
    r"ramp closure|spaghetti bowl|routine repaving|bridge painting|guardrail repair|"
    r"potholes for other drivers|spot all of them|highway command center|"
    r"earnings conference call|series [a-d] round|mobilosoft|new atlantis|"
    r"clean energy future|undergrads and a hospital|headspace integration|iheartradio|"
    r"renames main thoroughfare|best electric commuter scooters|hacks every google maps user|"
    r"fd wire|audio integration on mapquest)\b",
    re.I,
)

RE_CRIME_VIOLENCE = re.compile(
    r"\b(cops:|cops say|arrested|suspect|stabbing|shooting|shot dead|murder|homicide|"
    r"inmates escape|robbery|fatal crash|deadly collision|pedestrian killed|"
    r"bicyclist killed|cyclist killed|fatally strikes|kicks 4 kids|road rage driver|"
    r"slammed into another vehicle|naked in traffic|warrant issued|drug bust|"
    r"dui manslaughter|drowned|handcuffed in patrol car|domestic violence|assault|"
    r"child neglect|sentenced)\b",
    re.I,
)

RE_CELL_PHONE_BAN = re.compile(
    r"\b(distracted driving|hands-free|handheld cell phone|cell phone use behind the wheel|"
    r"texting while driving|texting ban|distracted drivers|drivers: send a text)\b",
    re.I,
)

RE_METAPHOR = re.compile(
    r"\b(treat .* like waze|the waze (of|for)|like waze|google maps for (cancer|the brain)|"
    r"waze for (commercial buildings|real estate)|creates new waze of)\b",
    re.I,
)

RE_ROUTINE_MAINTENANCE = re.compile(
    r"\b(highway command center|bridge painting|resurfacing project|guardrail repair|"
    r"routine repaving|potholes for other drivers|spot all of them|routine maintenance)\b",
    re.I,
)

RE_PHOTO_CAMERAS = re.compile(
    r"\b(proposition 319|photo enforcement cameras, not alpr|"
    r"flock and other license plate reader|red light cameras under proposed ordinance|"
    r"prohibiting traffic photo enforcement|automated traffic enforcement speed program)\b",
    re.I,
)

RE_ROUTINE_POLICE = re.compile(
    r"\b(operation wicked safe|traffic crackdown with 5|speed week [0-9]|"
    r"statewide speed enforcement|targeted patrols|speed awareness billboard)\b",
    re.I,
)

RE_CONSUMER_TIPS = re.compile(
    r"\b(how to avoid tolls|settings i (changed|always change)|voice commands i wish|"
    r"how to use|tips for|review:|hands-on with|top 5 features|redefining what a map can be|"
    r"appstore reviews|map apps for android auto|4 carplay|best navigation apps for|"
    r"\d+ google maps settings|\b\d+ (handy|hidden|ways to|tips|tricks|hacks|settings|reasons)\b)\b",
    re.I,
)

RE_TRANSIT_AVIATION_WEATHER = re.compile(
    r"\b(amtrak|commuter rail ridership|rail line.*scrapped|subway service|"
    r"flight delays?, cancellations|winter storm response|flash flooding.*closure)\b",
    re.I,
)

RE_COMMUTE_BULLETIN = re.compile(
    r"\b((heavy|moderate|light|usual) traffic through [a-z]+ (this morning|today)|"
    r"weekday traffic pattern resumes|traffic follows weekly pattern|usual morning traffic builds)\b",
    re.I,
)

# Overrides for legitimate policy controversies or pilot programs
RE_POLICY_OVERRIDE = re.compile(
    r"\b(regulate navigation|regulating navigation|navigation applications: pilot study|"
    r"curb waze traffic|waze traffic on side streets|streets closed to drivers who don’t live there|"
    r"bills would exempt car navigation)\b",
    re.I,
)


def evaluate_document(record: dict[str, Any]) -> tuple[int, str, str | None]:
    """Evaluate an article record and return (is_relevant, tier, exclusion_reason).

    Returns:
        (1, 'In-Scope', None) if article belongs in the filtered research corpus.
        (0, 'Excluded: <Category>', reason_str) if article is outside scope.
    """
    title = str(record.get("title") or "").strip()
    publisher = str(record.get("publisher") or "").strip()
    summary = str(record.get("factual_summary") or "").strip()

    passages_list = record.get("supporting_passages") or []
    passages_text = " ".join(
        p.get("verbatim_text", "") for p in passages_list if isinstance(p, dict)
    )

    tl = title.lower()
    pl = publisher.lower()
    sl = summary.lower()
    full_text = f"{tl} {pl} {sl} {passages_text.lower()}"

    # 1. Publisher blacklists
    if pl in ("law and crime", "global industry snapshot", "newstex blogs"):
        has_calming = bool(
            re.search(
                r"\b(cut-through traffic|traffic calming|speed humps?|diverters?|turn restrictions?)\b",
                full_text,
                re.I,
            )
        )
        if not has_calming:
            if pl == "law and crime":
                return (
                    0,
                    "Excluded: Police Blotter / Crime",
                    "Police report, fatal collision, or criminal assault with incidental mapping/traffic mentions.",
                )
            if pl == "global industry snapshot":
                return (
                    0,
                    "Excluded: Market Research / Financial Wire",
                    "Automated artificial intelligence software valuation and equity market snapshot.",
                )
            return (
                0,
                "Excluded: Consumer Tech Tips / Gadget Blog",
                "Consumer tech tip, gadget walkthrough, or app review without public policy relevance.",
            )

    # 2. Daily automated commute bulletins
    if RE_COMMUTE_BULLETIN.search(tl):
        return (
            0,
            "Excluded: Automated Commute Bulletin",
            "Routine automated daily morning/evening highway traffic bulletin.",
        )

    # 3. Police blotters, fatal crashes, violence
    if RE_CRIME_VIOLENCE.search(tl):
        if not RE_POLICY_OVERRIDE.search(tl):
            return (
                0,
                "Excluded: Police Blotter / Crime",
                "Police report, fatal collision, or criminal assault with incidental mapping/traffic mentions.",
            )

    # 4. Metaphorical usages
    if RE_METAPHOR.search(tl):
        return (
            0,
            "Excluded: Metaphorical Brand Usage",
            "Uses Waze or Google Maps metaphorically as an industry or technology analogy.",
        )

    # 5. Cell phone bans / distracted driving
    if RE_CELL_PHONE_BAN.search(tl):
        if not RE_POLICY_OVERRIDE.search(tl):
            return (
                0,
                "Excluded: Cell Phone / Hands-Free Ban",
                "General distracted driving, hands-free device, or texting legislation.",
            )

    # 6. Routine highway operations & maintenance
    if RE_ROUTINE_MAINTENANCE.search(tl):
        return (
            0,
            "Excluded: Highway Operations / Maintenance",
            "State DOT freeway monitoring room overview or routine asphalt/bridge maintenance.",
        )

    # 7. Standalone photo cameras & ALPR politics
    if RE_PHOTO_CAMERAS.search(tl):
        return (
            0,
            "Excluded: Photo Enforcement / ALPR Politics",
            "Debate over red-light cameras or automated license plate reader surveillance.",
        )

    # 8. Routine police speed enforcement
    if RE_ROUTINE_POLICE.search(tl):
        return (
            0,
            "Excluded: Routine Police Traffic Enforcement",
            "State police speed enforcement campaign or sobriety crackdown.",
        )

    # 9. Public transit disruptions, flight cancellations, weather disasters
    if RE_TRANSIT_AVIATION_WEATHER.search(tl):
        return (
            0,
            "Excluded: Transit / Aviation / Weather",
            "Public rail disruption, airline flight delay, or extreme weather closure.",
        )

    # 10. Consumer tech tips & listicles
    if RE_CONSUMER_TIPS.search(tl):
        return (
            0,
            "Excluded: Consumer Tech Tips / Gadget Blog",
            "Consumer tech tip, gadget walkthrough, or app review without public policy relevance.",
        )

    # 11. Generic noise subjects (sports parking, drone forecasts, patents, corporate PR)
    if RE_NOISE_SUBJECT.search(tl):
        if not RE_POLICY_OVERRIDE.search(tl):
            return (
                0,
                "Excluded: Off-Topic Subject",
                "Article subject is outside project scope (sports parking, drone market, web design, earnings call, etc.).",
            )

    # 12. Affirmative Requirement: Article must substantively touch at least one core pillar
    has_routing = bool(RE_ROUTING_CORE.search(full_text))
    has_calming = bool(RE_CALMING_CORE.search(full_text))
    has_governance = bool(RE_GOVERNANCE_CORE.search(full_text))

    if not (has_routing or has_calming or has_governance):
        return (
            0,
            "Excluded: Off-Topic / Incidental Match",
            "No substantive mention of routing apps, traffic calming, or municipal navigation governance.",
        )

    return (1, "In-Scope", None)
