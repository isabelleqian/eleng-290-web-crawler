"""Filter rules and taxonomy classification for routing apps research corpus.

Separates curated in-scope research documents (algorithmic navigation, cut-through
traffic, municipal traffic calming, platform governance, commercial truck GPS)
from off-topic noise (crime blotters, consumer gadget how-tos, commercial market
forecasts, routine highway maintenance, sports/campus parking, etc.).
"""

import re
from typing import Any

# ==============================================================================
# 1. Affirmative Research Pillars (The 4 Core Tracks)
# ==============================================================================

# Track 1: Algorithmic Routing & Navigation Apps
RE_TRACK1_ROUTING = re.compile(
    r"\b(waze|google maps|apple maps|mapquest|navigation app[s]?|routing app[s]?|"
    r"traffic app[s]?|turn-by-turn|in-car navigation|gps app[s]?|in-dash navigation)\b",
    re.I,
)
RE_TRACK1_EFFECT = re.compile(
    r"\b(shortcut[s]?|cut-through|neighborhood[s]?|residential|diversion|divert\w*|"
    r"side street[s]?|traffic congestion|traffic woes|clogged streets|pothole[s]?|"
    r"speed trap[s]?|road closure[s]?|rerout\w*|secret shortcut[s]?|traffic flows?|"
    r"traffic engineer[s]?|traffic nightmare|steepest streets?|longer way|route|"
    r"routing|congestion|traffic)\b",
    re.I,
)

# Track 2: Municipal Traffic Calming & Operational Interventions
RE_TRACK2_CALMING = re.compile(
    r"\b(traffic calm\w*|speed hump[s]?|speed bump[s]?|speed cushion[s]?|speed table[s]?|"
    r"chican\w*|traffic diverter[s]?|diverter[s]?|neighborhood greenway|home zone|"
    r"resident[s]?-only|no through traffic|closed to through traffic|turn restriction[s]?|"
    r"turn ban[s]?|peak-hour turn|no left turn|one-way|thru-traffic|through-traffic|"
    r"road diet[s]?|traffic circle[s]?|bollard[s]?)\b",
    re.I,
)

# Track 3: Platform Governance, Regulation & Public-Private Partnerships
RE_TRACK3_GOVERNANCE = re.compile(
    r"\b(connected citizens program|waze for cities|project green light|signal optimization|"
    r"data-sharing (partnership|pact|program|agreement)|traffic-reporting partnership|"
    r"partners? with waze|waze.*partner|partner.*waze|regulate.*(navigation|maps|apps)|"
    r"regulating.*(navigation|maps|apps)|leonia|krekorian|garcetti.*waze|mayor.*waze|"
    r"app poisoning|poisoning waze|plant false|fake traffic|fake accident[s]?|"
    r"99 phones|dwi checkpoint[s]?|dui checkpoint[s]?|speed trap[s]?|police.*waze|"
    r"waze.*cops|nypd.*waze|caltrans.*waze|vdot.*waze|massdot.*waze|penndot.*waze|"
    r"aldot.*waze|ridot.*waze|cdot.*waze|waze discuss|citizens advisory committee|"
    r"smart city challenge|council meeting minutes|delridge neighborhood)\b",
    re.I,
)

# Track 4: Commercial Freight & Truck GPS Routing
RE_TRACK4_TRUCKS = re.compile(
    r"\b(truck routing|commercial vehicle routing|truck gps|trucks hit (overpass|bridge)|"
    r"bridge strike[s]?|low clearance|smarttruckroute|teletype.*truck|ban commercial buses|"
    r"commercial buses.*ban|truck restrictions?|truck navigation)\b",
    re.I,
)

# Policy Overrides (high-signal research controversies that may contain sensitive terms)
RE_OVERRIDE = re.compile(
    r"\b(ab[ -]?2015|regulate navigation|regulating navigation|navigation applications?: pilot study|"
    r"curb waze traffic|waze traffic on side streets|streets closed to drivers who don’t live there|"
    r"bills would exempt car navigation|dwi checkpoint[s]?|dui checkpoint[s]?|cop checkpoint[s]?|"
    r"checkpoint notification|plant false information|fake traffic accidents|reporting fake|"
    r"99 phones|bridge strike[s]?|(truck[s]?|semi|trailer|bus[es]?)\s+(hit|hits|struck|strikes)\s+(overpass|bridge)|"
    r"trucks hit overpasses|combat bridge strikes|prevent bridge strikes|"
    r"truck routes and education on truck gps|truck info on phone gps|"
    r"commercial buses to be banned|smarttruckroute|scott\'s law|google told drivers|longer way on purpose)\b",
    re.I,
)

# ==============================================================================
# 2. Exclusion Signatures (Noise Filtering)
# ==============================================================================

RE_METAPHOR = re.compile(
    r"\b(treat .* like waze|waze treats traffic|google maps for (cancer|the brain|health)|"
    r"waze for (commercial buildings|real estate|retail)|trapped building data|physical ai boom|"
    r"creates new waze of)\b",
    re.I,
)

RE_CRIME = re.compile(
    r"\b(cops:|cops say|arrested|suspect|stabbing|shooting|shot dead|murder|homicide|"
    r"inmates escape|robbery|fatal crash|deadly collision|pedestrian killed|"
    r"bicyclist killed|cyclist killed|fatally strikes|kicks 4 kids|road rage driver|"
    r"slammed into another vehicle|naked in traffic|warrant issued|drug bust|"
    r"dui manslaughter|drowned|handcuffed in patrol car|domestic violence|assault|"
    r"child neglect|sentenced|hit-and-run crash|carjacking|stolen vehicle|busted for dui)\b",
    re.I,
)

RE_ROUTINE_CONSTRUCTION = re.compile(
    r"\b(pipe culvert|culvert under|bridge painting|routine repaving|guardrail repair|"
    r"resurfacing project|potholes for other drivers|spot all of them|highway command center|"
    r"overnight offramp closures?|offramp closed overnight|off-ramp closed overnight|"
    r"interstate \d+ lane restrictions?|lane reductions? near|overnight lane reductions?|"
    r"ndot awards|pavement work|northbound i-\d+ closed|closed for two special events|"
    r"closed for railroad (repairs|crossing)|railroad crossing (repairs|closed)|"
    r"special events september|mosquitoes|sprayed for mosquitoes|long-term lane closure reopens|"
    r"lane closure reopens|full closures? scheduled on .* overpass in .* for paving|"
    r"rescheduled overnight full closures? on .* overpass in .* for beam installation)\b",
    re.I,
)

RE_CONSUMER_GADGET = re.compile(
    r"\b(apple maps vs\.? google maps|google maps vs\.? apple maps|google maps vs\.? waze|"
    r"waze vs\.? google maps|best navigation apps for|top \d+ best navigation|"
    r"settings i (changed|always change)|voice commands i wish|how to (make|blur|avoid tolls|change voice|spot|find|use|report)|"
    r"review: a driver\'s best friend|waze review|apple maps review|google maps review|"
    r"is waze still worth using|como você pode|economizar dinheiro|"
    r"\d+ (handy|hidden|ways to|tips|tricks|hacks|settings|reasons|features)|"
    r"immersive view for cities|gemini on a road trip|retro camper|unpaid tolls scam|"
    r"i\'m an apple maps fan, but i switch|find parked car|custom routes feature in ios|"
    r"key new ios \d+ software features|\d+ key things to know about apple|"
    r"hands-on with|redefining what a map can be|appstore reviews|map apps for android auto|"
    r"4 carplay|tested: \d+|headspace integration|audio integration on mapquest|"
    r"testing a clean ui|fuel-efficient routes|flock and other license plate reader|"
    r"flock safety|access denied|stories from slate|racing simulation lounge|"
    r"subdivision traffic calming, package|grant county land information|"
    r"motor carriers\' road atlas|tripquest driving directions service|"
    r"google maps update adds transit directions|targets on-demand rides|"
    r"predicts parking availability)\b",
    re.I,
)

RE_FOREIGN = re.compile(
    r"\b(cape town|saltillo|iraq to ban waze|china criticises taiwan|mainland criticizes dpp|"
    r"n2 safety|amap navigation app|formula 1 streaming outside the us)\b",
    re.I,
)

RE_COMMUTE_BULLETIN = re.compile(
    r"\b((heavy|moderate|light|usual|minor) traffic (through|on|building) [a-z ]+ (this morning|today|tonight|friday night|highways)|"
    r"weekday traffic pattern resumes|traffic follows weekly pattern|usual morning traffic builds)\b",
    re.I,
)

RE_OFF_TOPIC_MISC = re.compile(
    r"\b(website design|web design|emergency go bag|failed gop|tennis player|"
    r"personal injury|law firm|bbq|ribbon cutting|grand opening|obituary|dies at|"
    r"savannah bananas|fsu football|spirit week|commencement parking|game day traffic|"
    r"stadium parking|parking/traffic advisory|parade route|unhoused|anti-homeless|"
    r"hostile architecture|patent[s]? infring|proof-of-delivery|trimble|"
    r"construction materials|mcleod software|pc miler navigator 550|pc\*miler navigator 550|"
    r"covered bridge|drone market|cagr|allied market research|research and markets|"
    r"global industry snapshot|delhi.*pollution|animal services|cia facility|sand quarry|"
    r"ocean data portal|figma nyse|via transportation nyse|wipo publishes patent|patent of|"
    r"parkmobile|paybyphone|web 2\.0|business\.gov|foreign-trade zone|garmin.*avionics|"
    r"fairfield metro station|renaming.*route|earnings conference call|series [a-d] round|"
    r"mobilosoft|new atlantis|clean energy future|undergrads and a hospital|iheartradio|"
    r"best electric commuter scooters|hacks every google maps user|fd wire|"
    r"globee.*awards|royal farms name|abortion access|mass surveillance on a budget|"
    r"square and opentable|ask4sam|silberstein & miklos|lowenthal & abrams|wallentine injury|"
    r"new etsu parking|data center town hall|hurricane helene|ice tracking apps|iceblock|"
    r"helios and matheson|redzone|climate crisis is seriously spooking|campus should be harder to navigate|"
    r"small business trends|all stars|cannonsville adventure|artist\'s work seen in canvas|"
    r"the plat thickens|pittsburgh steelers game|ministry of health|dmv offers early access|"
    r"ford f-150 lightning|electric scooter onto lincoln drive|arizona telecommunications|"
    r"spydrsafe|don\'t let technology remove the h|gasbuddy|concept3d|city of elk grove launches|"
    r"octo-wdcep|oahu traffic is gone|kansas quarry|operation wicked safe|"
    r"proposition 319|prohibiting traffic photo enforcement|fairfield rtm authorizes speed and red light)\b",
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
    summary_lead = summary[:350]

    tl = title.lower()
    pl = publisher.lower()
    sl = summary_lead.lower()
    head_text = f"{tl} {sl}"

    # 1. Publisher blacklists
    if pl in ("law and crime", "global industry snapshot"):
        if pl == "law and crime":
            return (
                0,
                "Excluded: Police Blotter / Crime",
                "Police report, fatal collision, or criminal assault with incidental mapping/traffic mentions.",
            )
        return (
            0,
            "Excluded: Market Research / Financial Wire",
            "Automated artificial intelligence software valuation and equity market snapshot.",
        )

    # 2. Check for Policy Overrides
    is_override = bool(RE_OVERRIDE.search(head_text))

    if not is_override:
        # Metaphorical usages
        if RE_METAPHOR.search(head_text):
            return (
                0,
                "Excluded: Metaphorical Brand Usage",
                "Uses Waze or Google Maps metaphorically as an industry or technology analogy.",
            )

        # Foreign / Non-US Jurisdictions
        if RE_FOREIGN.search(head_text):
            return (
                0,
                "Excluded: Foreign Jurisdiction",
                "Article reports on foreign routing controversies outside US municipal and policy scope.",
            )

        # Consumer Tech Tips, How-Tos, Reviews
        if RE_CONSUMER_GADGET.search(head_text) or RE_CONSUMER_GADGET.search(tl):
            return (
                0,
                "Excluded: Consumer Tech Tips / Gadget Blog",
                "Consumer tech tip, gadget walkthrough, or app review without public policy relevance.",
            )

        # Routine Highway Operations & Maintenance
        if RE_ROUTINE_CONSTRUCTION.search(head_text) or RE_ROUTINE_CONSTRUCTION.search(tl):
            return (
                0,
                "Excluded: Highway Operations / Maintenance",
                "State DOT freeway monitoring room overview or routine asphalt/bridge maintenance.",
            )

        # Daily Automated Commute Bulletins
        if RE_COMMUTE_BULLETIN.search(tl):
            return (
                0,
                "Excluded: Automated Commute Bulletin",
                "Routine automated daily morning/evening highway traffic bulletin.",
            )

        # Police Blotters, Fatal Crashes, Violence
        if RE_CRIME.search(tl):
            return (
                0,
                "Excluded: Police Blotter / Crime",
                "Police report, fatal collision, or criminal assault with incidental mapping/traffic mentions.",
            )

        # Generic Off-Topic Subjects
        if RE_OFF_TOPIC_MISC.search(head_text) or RE_OFF_TOPIC_MISC.search(tl):
            return (
                0,
                "Excluded: Off-Topic Subject",
                "Article subject is outside project scope (sports parking, drone market, web design, earnings call, etc.).",
            )

    # 3. Affirmative Evaluation (Must match at least one of the 4 Core Tracks in Title or Lead)
    t1 = bool(RE_TRACK1_ROUTING.search(head_text) and RE_TRACK1_EFFECT.search(head_text))
    t2 = bool(RE_TRACK2_CALMING.search(head_text))
    t3 = bool(RE_TRACK3_GOVERNANCE.search(head_text))
    t4 = bool(RE_TRACK4_TRUCKS.search(head_text))

    if t1 or t2 or t3 or t4 or is_override:
        if not is_override and (RE_CONSUMER_GADGET.search(tl) or RE_OFF_TOPIC_MISC.search(tl)):
            return (
                0,
                "Excluded: Consumer Tech Tips / Gadget Blog",
                "Consumer tech tip, gadget walkthrough, or app review without public policy relevance.",
            )
        return (1, "In-Scope", None)

    return (
        0,
        "Excluded: Off-Topic / Incidental Match",
        "No substantive mention of routing apps, traffic calming, or municipal navigation governance.",
    )
