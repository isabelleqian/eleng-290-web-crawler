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


def compute_relevance_meta(
    record: dict[str, Any],
    is_relevant: int,
    tier: str,
    exclusion_reason: str | None,
) -> tuple[int, str]:
    """Compute numerical relevance score (0-99%) and a crisp 1-line rationale."""
    title = str(record.get("title") or "").strip()
    summary = str(record.get("factual_summary") or "").strip()
    text = f"{title} {summary}".lower()

    if not is_relevant:
        reason = exclusion_reason or tier or "Off-Topic"
        if "Metaphor" in reason:
            return 10, "Excluded: Metaphorical brand reference rather than navigation app routing policy."
        if "Foreign" in reason:
            return 15, "Excluded: International jurisdiction outside the scope of US municipal traffic governance."
        if "Consumer Tech" in reason:
            return 10, "Excluded: Consumer gadget tutorial, tech tips, or feature review without public policy impact."
        if "Highway Operations" in reason:
            return 12, "Excluded: Routine highway operations, DOT command centers, or standard maintenance."
        if "Automated Commute" in reason:
            return 5, "Excluded: Automated daily commute traffic report or routine radio broadcast."
        if "Police Blotter" in reason or "Crime" in reason:
            return 5, "Excluded: Law enforcement blotter, fatal crash report, or crime news."
        return 8, f"Excluded: Outside research scope ({reason})."

    # IN-SCOPE SCORING & RATIONALES:

    # Tier 1: Statutory mandates, federal regulations & landmark municipal street bans (98-99%)
    if re.search(r"\bleonia\b", text):
        return 99, "Landmark municipal ordinance restricting residential cut-through streets to residents during peak commute hours to counter navigation apps."
    if re.search(
        r"\bab\s*2015\b|\bassembly bill\b|california legislation|\bblumenthal\b|\brep(s)?\. latimer\b|\bschumer\b.*bridge|\bking street bridge\b|illinois bill.*truck route",
        text,
    ):
        return 99, "Statutory and legislative mandate requiring navigation platforms to respect municipal street restrictions and commercial bridge heights."
    if re.search(
        r"u\.s\. government wants to regulate|feds to regulate|feds.*regulate|government seeks to regulate maps|smartphone navigation.*regulated by the transportation department|bills would exempt car navigation",
        text,
    ):
        return 98, "Federal regulatory proposal by the US Department of Transportation and NHTSA to establish safety and routing oversight over mobile navigation apps."
    if re.search(
        r"krekorian|los angeles city council|l\.a\. may crack down|council file #11-2130|motion 14-1741|pilot program to curb waze|l\.a\. council seeks solutions to waze|waze restricted due to buildup|will work together to reduce growing traffic on residential",
        text,
    ):
        return 98, "Municipal city council legislative action and legal initiatives addressing navigation platform cut-through traffic on neighborhood streets."
    if re.search(
        r"town beset by traffic.*closes off streets|town that closed streets.*court reprieve|judge nixes new jersey town",
        text,
    ):
        return 98, "Municipal cut-through street closures and court challenges concerning local government authority to restrict navigation app traffic."

    # Tier 2: Platform resistance, gaming, police warnings, and extreme road hazards (96-97%)
    if re.search(r"simon weckert|99 (smart)?phones|wagon.*google maps", text):
        return 97, "Empirical demonstration of algorithmic resistance simulating virtual traffic jams on Google Maps using 99 smartphones in a handcart."
    if re.search(r"baxter st|steepest street|spin out|falling off.*hill|absolute chaos", text):
        return 97, "Severe physical traffic hazards and vehicle rollovers on extreme-gradient residential streets caused by routing algorithm shortcuts."
    if re.search(r"fake (traffic )?accident|false report|game the app|spoof|trolling waze|reporting fake", text):
        return 96, "Neighborhood resident collective action and algorithmic resistance via crowdsourced false accident reporting to divert Waze traffic."
    if re.search(
        r"nypd.*dui|dui checkpoint|dwi checkpoint|checkpoint notification|speed trap|speed traps|stop reporting locations of dw?i|letter demands google stop|nypd sends letter|nypd demands|la cops bury the hatchet",
        text,
    ):
        return 96, "Law enforcement agency pushback demanding navigation apps remove crowdsourced police location, speed trap, and DUI checkpoint alerts."
    if re.search(r"colorado transportation.*false information|plant false information", text):
        return 96, "State transportation department intervention attempting to inject false road closure information into navigation apps to manage flow."

    # Tier 3: Public-private data partnerships, signal optimization & smart infrastructure (94-95%)
    if re.search(r"project green light|signal optimization|signal timing", text):
        return 95, "Municipal traffic signal timing optimization initiative using navigation platform mobility data to reduce intersection delays and emissions."
    if re.search(
        r"urban congestion relief experiments|using waze data to measure traffic|traffic control and routing in the era of algorithmic navigation|data integration, sharing, and management for transportation planning|smart city challenge|traffic app a two-way street",
        text,
    ):
        return 95, "Empirical research and transportation authority studies evaluating algorithmic navigation impacts and municipal data integration."
    if re.search(
        r"connected citizens program|waze for cities|esri.*waze|waycare|data-sharing|partnership with.*waze|partners? with.*waze|works with waze|joins waze|waze.*google cloud|joins forces to alleviate congestion|mayor garcetti details agreement|agreement with waze|waze, abc team|collaborat.*waze|partner for real-time traffic|partner to share real-time|louisville announces real-time traffic app",
        text,
    ):
        return 94, "Bilateral public-private data partnership integrating municipal road closure data with crowdsourced app telemetry to optimize traffic flow."
    if re.search(r"waymo.*waze.*pothole|fix (cities\x27|city) potholes|mapping potholes|spotting potholes|pothole", text):
        return 94, "Autonomous vehicle sensor fleet and crowdsourced navigation partnership alerting municipal public works departments to roadway potholes."

    # Tier 4: Physical traffic engineering, turn restrictions, and diverters (92-93%)
    if re.search(
        r"wood street.*one-way|traffic diverter|genesee.*brandon|delridge neighborhood greenway|home zone|reducing a lane on dexter",
        text,
    ):
        return 93, "Targeted traffic engineering measures (one-way street conversions and physical diverters) installed to block navigation app bypass routes."
    if re.search(
        r"nursery road|merritt traffic|towns cracking down on gps|secret shortcut|turner\x27s county road|headache for cities|shortcuts on waze|state looks to avoid gps sending drivers down small roads|why some cities have had enough of waze",
        text,
    ):
        return 93, "Municipal traffic enforcement and neighborhood resistance against navigation app shortcuts diverting highway overflow into local residential streets."
    if re.search(r"bridge strike|overpass|low clearance|commercial buses to be banned|south kent road", text):
        return 92, "Infrastructure damage risks and vehicle weight/height bans enacted to prevent GPS routing from directing heavy vehicles onto unsuitable roadways."

    # Tier 5: Specialized commercial vehicle GPS systems & mapping architecture (90-91%)
    if re.search(
        r"copilot|samsara.*truck|smarttruckroute|pc\*miler|commercial navigation|truck gps|truck routing app|teletype.*truck|u\.s\. xpress drivers get|commercial vehicle|senators call for more truck info on phone gps|navigation partnership with alk",
        text,
    ):
        return 91, "Commercial fleet navigation technology designed to provide low-clearance avoidance and truck-safe routing to prevent infrastructure strikes."
    if re.search(
        r"blacklist areas|maps now change as roads close|adds road closure reporting|international partner program|google told drivers to drive a longer way|flow a smart traffic and parking platform|traffic safety digital alert",
        text,
    ):
        return 90, "Navigation platform mapping architecture, emergency vehicle alerts, and municipal requests for road closure integrations."

    # Tier 6: Neighborhood traffic calming, speed hump programs, and eco-routing (87-89%)
    if re.search(
        r"speed hump|speed cushion|speed bump|traffic calming|traffic circle|shady ave|traffic-calming|slowing down for safety",
        text,
    ):
        return 88, "Municipal neighborhood traffic calming program (speed humps/cushions) implemented to slow and discourage cut-through commuter traffic."
    if re.search(r"eco friendly|eco-friendly|lower your carbon footprint", text):
        return 87, "Algorithmic routing policy shift toward eco-friendly routing to optimize fuel consumption and minimize residential emissions."

    # Tier 7: Algorithmic governance, route personalization, and commuter dynamics (85-86%)
    if re.search(
        r"working properly.*make traffic flows worse|traffic-weary homeowners|suburban congestion|carmageddon|cut-through|traffic calming illusion|impact privacy, the law and google maps",
        text,
    ):
        return 86, "Investigation into legal implications and systemic traffic dynamics of routing algorithms redirecting commuter flows onto local roads."

    return 85, "Analysis of navigation platform routing patterns, feature updates, and commuter navigation behavior."


def evaluate_document(record: dict[str, Any]) -> tuple[int, str, str | None, int, str]:
    """Evaluate an article record and return (is_relevant, tier, exclusion_reason, relevance_score, relevance_rationale).

    Returns:
        (1, 'In-Scope', None, score, rationale) if article belongs in the filtered research corpus.
        (0, 'Excluded: <Category>', reason_str, score, rationale) if article is outside scope.
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
            tier = "Excluded: Police Blotter / Crime"
            reason = "Police report, fatal collision, or criminal assault with incidental mapping/traffic mentions."
            score, rationale = compute_relevance_meta(record, 0, tier, reason)
            return (0, tier, reason, score, rationale)
        tier = "Excluded: Market Research / Financial Wire"
        reason = "Automated artificial intelligence software valuation and equity market snapshot."
        score, rationale = compute_relevance_meta(record, 0, tier, reason)
        return (0, tier, reason, score, rationale)

    # 2. Check for Policy Overrides
    is_override = bool(RE_OVERRIDE.search(head_text))

    if not is_override:
        # Metaphorical usages
        if RE_METAPHOR.search(head_text):
            tier = "Excluded: Metaphorical Brand Usage"
            reason = "Uses Waze or Google Maps metaphorically as an industry or technology analogy."
            score, rationale = compute_relevance_meta(record, 0, tier, reason)
            return (0, tier, reason, score, rationale)

        # Foreign / Non-US Jurisdictions
        if RE_FOREIGN.search(head_text):
            tier = "Excluded: Foreign Jurisdiction"
            reason = "Article reports on foreign routing controversies outside US municipal and policy scope."
            score, rationale = compute_relevance_meta(record, 0, tier, reason)
            return (0, tier, reason, score, rationale)

        # Consumer Tech Tips, How-Tos, Reviews
        if RE_CONSUMER_GADGET.search(head_text) or RE_CONSUMER_GADGET.search(tl):
            tier = "Excluded: Consumer Tech Tips / Gadget Blog"
            reason = "Consumer tech tip, gadget walkthrough, or app review without public policy relevance."
            score, rationale = compute_relevance_meta(record, 0, tier, reason)
            return (0, tier, reason, score, rationale)

        # Routine Highway Operations & Maintenance
        if RE_ROUTINE_CONSTRUCTION.search(head_text) or RE_ROUTINE_CONSTRUCTION.search(tl):
            tier = "Excluded: Highway Operations / Maintenance"
            reason = "State DOT freeway monitoring room overview or routine asphalt/bridge maintenance."
            score, rationale = compute_relevance_meta(record, 0, tier, reason)
            return (0, tier, reason, score, rationale)

        # Daily Automated Commute Bulletins
        if RE_COMMUTE_BULLETIN.search(tl):
            tier = "Excluded: Automated Commute Bulletin"
            reason = "Routine automated daily morning/evening highway traffic bulletin."
            score, rationale = compute_relevance_meta(record, 0, tier, reason)
            return (0, tier, reason, score, rationale)

        # Police Blotters, Fatal Crashes, Violence
        if RE_CRIME.search(tl):
            tier = "Excluded: Police Blotter / Crime"
            reason = "Police report, fatal collision, or criminal assault with incidental mapping/traffic mentions."
            score, rationale = compute_relevance_meta(record, 0, tier, reason)
            return (0, tier, reason, score, rationale)

        # Generic Off-Topic Subjects
        if RE_OFF_TOPIC_MISC.search(head_text) or RE_OFF_TOPIC_MISC.search(tl):
            tier = "Excluded: Off-Topic Subject"
            reason = "Article subject is outside project scope (sports parking, drone market, web design, earnings call, etc.)."
            score, rationale = compute_relevance_meta(record, 0, tier, reason)
            return (0, tier, reason, score, rationale)

    # 3. Affirmative Evaluation (Must match at least one of the 4 Core Tracks in Title or Lead)
    t1 = bool(RE_TRACK1_ROUTING.search(head_text) and RE_TRACK1_EFFECT.search(head_text))
    t2 = bool(RE_TRACK2_CALMING.search(head_text))
    t3 = bool(RE_TRACK3_GOVERNANCE.search(head_text))
    t4 = bool(RE_TRACK4_TRUCKS.search(head_text))

    if t1 or t2 or t3 or t4 or is_override:
        if not is_override and (RE_CONSUMER_GADGET.search(tl) or RE_OFF_TOPIC_MISC.search(tl)):
            tier = "Excluded: Consumer Tech Tips / Gadget Blog"
            reason = "Consumer tech tip, gadget walkthrough, or app review without public policy relevance."
            score, rationale = compute_relevance_meta(record, 0, tier, reason)
            return (0, tier, reason, score, rationale)
        score, rationale = compute_relevance_meta(record, 1, "In-Scope", None)
        return (1, "In-Scope", None, score, rationale)

    tier = "Excluded: Off-Topic / Incidental Match"
    reason = "No substantive mention of routing apps, traffic calming, or municipal navigation governance."
    score, rationale = compute_relevance_meta(record, 0, tier, reason)
    return (0, tier, reason, score, rationale)
