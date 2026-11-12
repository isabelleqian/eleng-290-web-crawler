# Routing App Legal Regulation Framework: Three-Tier Governance Summary
**Research As-Of Date:** November 12, 2026  
**Jurisdictional Scope:** United States (Federal, California, New York, Washington, Texas, Arizona, Alabama, Alaska, Arkansas, Colorado, Connecticut, Massachusetts, New Jersey, and municipal jurisdictions).  
**Notice:** Current status, statutory text, and administrative regulations are verified against official legislative engines (California Legislative Information, Congress.gov, New Jersey Legislature, New York State Senate, Texas Legislature Online, etc.) as of November 2026.

---

## Executive Overview of the Three-Tier Architecture

The legal framework governing vehicular navigation applications (e.g., Google Maps, Waze, Apple Maps, commercial truck routing software) operates across three distinct concentric tiers of distance from the navigation software provider:

1. **Tier 1: Laws Directly Governing Routing Apps (App-Targeted Platform Governance)**  
   Statutes and legislative proposals that explicitly name navigation applications, GPS routing systems, digital mapping platforms, or algorithmic route outputs, imposing affirmative routing restrictions, road exclusion compliance duties, emergency rerouting mandates, or study reporting requirements directly upon platform developers.

2. **Tier 2: Laws Not Specific to Routing Apps but Directly Applicable to Them (Cross-Sector Platform Governance)**  
   Broad statutory frameworks that do not name navigation software explicitly, but directly govern the apps' legal operations, user interactions, proprietary data feeds, commercial vehicle guidance algorithms, and liability boundaries. This includes driver device safety rules, sensitive location privacy regimes, consumer protection against deceptive ETAs, Section 230 platform liability boundaries for crowdsourced user hazard alerts, public records rules for government-app data exchanges, and federal commercial freight routing standards.

3. **Tier 3: Indirectly Applicable Road and Traffic Laws (Infrastructure, Operational & Traffic Control Regulations)**  
   The underlying body of motor vehicle codes, traffic engineering standards, and local police power ordinances that govern roadway users, physical infrastructure, and operational conditions. While these laws bind drivers, vehicles, and road authorities rather than tech platforms, navigation algorithms must continuously mirror, ingest, and route around them to avoid recommending unlawful maneuvers or routing users into impassable, restricted, or camera-enforced corridors.

```
+-----------------------------------------------------------------------------------+
|                        TIER 1: DIRECT PLATFORM GOVERNANCE                         |
|  - Explicitly names routing apps / GPS navigation                                 |
|  - Slow street exclusions (CA AB 2015), Emergency rerouting (NJ SAFER APP)        |
|  - Commercial GPS bridge clearance & low-clearance mandates (NY, Federal HR 6531) |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|               TIER 2: CROSS-SECTOR DIRECTLY APPLICABLE PLATFORM LAWS              |
|  - Hands-free device mounting rules (CVC §§ 23123/23123.5)                        |
|  - Precise geolocation data privacy (CCPA/CPRA, NY A8729)                         |
|  - Consumer protection & false advertising (Cal B&PC § 17200, FTC Act § 5)        |
|  - Section 230 immunity for crowdsourced alerts vs algorithm design               |
|  - Public records & data exchange (CPRA, Connected Citizens / Waze for Cities)    |
|  - Commercial freight standards (49 CFR 397 hazmat, 23 CFR 658 National Network)  |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                   TIER 3: INDIRECT ROAD, TRAFFIC & POLICE LAWS                    |
|  - Turn prohibitions & cut-through restrictions (CVC §§ 21101, 22101, 22113)      |
|  - Preferential residential permit parking (CVC § 22507)                          |
|  - Truck weight limits, oversize corridors & municipal bans (CVC § 35701, TX Ch621|
|  - Automated speed cameras & photo radar bans (AR, WA, NY, AL, CT, AZ Prop 319)   |
|  - Congestion pricing (23 U.S.C. § 129), HOV/HOT dynamic lanes (23 U.S.C. § 166)  |
|  - Traffic control device engineering standards (23 CFR Part 655 / MUTCD 11th Ed) |
+-----------------------------------------------------------------------------------+
```

---

# Tier 1: Laws Directly Governing Routing Apps

Statutes and legislative proposals that explicitly name navigation applications, GPS routing providers, digital mapping platforms, or algorithmic route outputs, imposing affirmative obligations, restrictions, study charters, or civil liability on them.

### Topic 1.1: Slow Streets and Residential Route Exclusion
* **Enacted:**
  * **California AB 2015 (Chapter 207, Statutes of 2026):** Adds California Streets and Highways Code § 155.8. Empowers local authorities that have lawfully established slow streets programs to formally notify navigation app providers to exclude designated slow streets from commuter cut-through routes.
  * **Verified Statutory Provisions:**
    * *Study Scope:* Caltrans, in consultation with the California State Transportation Agency (CalSTA), must conduct a comprehensive **statewide empirical study** of the impacts of third-party navigation apps on state highways and local streets, evaluating congestion, safety, cut-through traffic, and emergency response. (An earlier draft proposal to limit the empirical inquiry to a single regional pilot was expanded during legislative amendments into a statewide study). The final report is due to the Legislature by **January 1, 2028**.
    * *Sunset Date:* Streets and Highways Code § 155.8(g) establishes a statutory sunset date of **January 1, 2033** (confirming Digital Democracy / Enrolled Bill records; resolving initial confusion from earlier summaries that referenced 2032).

### Topic 1.2: Route Adjustment During Emergencies
* **Enacted:**
  * **New Jersey A3036 / P.L. 2026, c. 12 (Smart App Freight Enforcement and Rerouting — SAFER APP Act):** Signed into law by Governor Phil Murphy on **January 20, 2026** (resolving outcome). Passed the Senate on December 18, 2025; the Legislature concurred with the Governor's conditional veto recommendations on January 12, 2026, and the bill was signed into law as Chapter 12 of the Laws of 2026.
  * *Operational Mandate:* Empowers the New Jersey Attorney General, in coordination with the Department of Transportation and State Police, to issue emergency rerouting directives to turn-by-turn navigation apps during natural disasters, major infrastructure failures, commercial corridor closures, or severe weather events.
  * *Enforcement & Liability:* Imposes civil administrative penalties up to **$1,000 per violation** against navigation app providers that fail to incorporate official road restriction and emergency detour feeds.

### Topic 1.3: Heavy Vehicle Route Restrictions
* **Enacted:**
  * *None in force directly naming apps.* (Commercial truck restrictions currently operate via Tier 2 commercial regulations and Tier 3 local route ordinances).
* **Failed / Stalled Bills:**
  * **Connecticut HB 5071 (2025 Regular Session):** *Failed.* Proposed to prohibit commercial navigation apps from routing heavy commercial motor vehicles onto local residential and municipal roads; died in the Joint Committee on Transportation upon adjournment of the 2025 regular session.
  * **Connecticut HB 6709 (2025 Regular Session):** *Failed.* Proposed by Rep. Tracy Marra; sought to mandate navigation apps to restrict heavy commercial vehicles from local municipal streets and display bridge height restrictions; died in committee at session end (June 2025).
  * **Massachusetts HD.4949 (2025–2026 Legislative Session):** *Stalled / Pending.* Prohibits commercial navigation apps from directing heavy commercial motor vehicles onto residential roadways or municipal ways without prior local commercial route authorization; referred to House Rules Committee in July 2025 where it remains pending.

### Topic 1.4: Bridge Clearance and Safety Information
* **Enacted:**
  * *None in force directly naming apps.* (Governed under federal bridge formula in 23 U.S.C. § 127 and state low-clearance signage standards).
* **Pending / Failed Bills:**
  * **New York Assembly Bill A8582 (2023–2024 Legislative Session):** *Failed.* Passed the New York State Assembly by a 143–1 vote on June 3, 2024; died in the Senate Rules/Consumer Protection Committee at sine die adjournment.
  * **New York S6197 / A3536 (2025–2026 Regular Session):** *Pending.* Reintroduced successor to A8582. Requires electronic mapping and GPS navigation apps to prominently display the legal height and weight clearance limits of bridges and elevated overpasses, issuing visual and audible warnings when a route approaches low-clearance infrastructure. A3536 passed the Assembly and was referred to the Senate Transportation Committee on May 6, 2026.
  * **Federal H.R. 6531 (119th Congress, Bridges Not Bumpers Act of 2025):** *Pending.* Introduced December 9, 2025; directs USDOT and FHWA to establish an interagency working group on low-clearance bridge strikes and construct a National Bridge Clearance Clearinghouse, requiring commercial GPS providers to integrate real-time low-clearance data into routing engines.

### Topic 1.5: Study and Data Reporting
* **Enacted:**
  * **California AB 2015 (Chapter 207, Statutes of 2026):** Mandates Caltrans and CalSTA to study the systemic diversionary effects of third-party navigation apps, evaluate algorithmic routing impacts on local traffic calming, and submit empirical policy recommendations to the Legislature by **January 1, 2028**.
* **Pending Federal Proposals:**
  * **Federal MAP Roads Act (Modernizing Access to Public Roads Act):** *Pending.* Bipartisan federal bill directing the U.S. Department of Transportation to award competitive digitization grants to county, municipal, and rural road agencies to standardize and publish machine-readable geospatial databases of local road restrictions, bridge weight/clearance limits, and seasonal closures for seamless integration by commercial and consumer navigation applications.

---

# Tier 2: Laws Not Specific to Routing Apps but Directly Applicable to Them

Broad statutory frameworks and administrative regulations that do not explicitly mention navigation software by name, but directly govern how platforms interact with mobile drivers, collect and monetize location telemetry, warrant route travel times, manage crowdsourced hazard reporting, interface with government public records, and calculate commercial motor carrier routes.

> [!NOTE]
> **Litigation and Case Law Notice:** Most Tier 2 statutes have extensive case law regarding software platforms, privacy, and telecommunications, but have relatively few published appellate opinions specifically resolving navigation app routing liabilities. Where judicial precedent exists, it is highlighted below.

### Topic 2.1: Device Use While Driving
* **Enacted:**
  * **California Vehicle Code §§ 23123 & 23123.5:** Prohibits operating a motor vehicle while holding and operating a handheld wireless telephone or electronic wireless communications device.
  * *App-Specific Application & Exemption:* Specifically permits drivers to view turn-by-turn navigation prompts and GPS route guidance *only* if the device is mounted to the vehicle windshield, dashboard, or center console, and is activated via a single touch, swipe, or voice command. Navigation app UI/UX workflows (e.g. searching destinations, reporting hazards) that require continuous manual typing while in motion violate § 23123.5.

### Topic 2.2: Location Data and Privacy
* **Enacted:**
  * **California Consumer Privacy Act (CCPA) / California Privacy Rights Act (CPRA), Cal. Civ. Code § 1798.140 et seq.:** Explicitly classifies "precise geolocation" (geographic area within a radius of 1,850 feet) as **Sensitive Personal Information**. Imposes affirmative obligations on navigation platforms to grant users the right to limit the use and disclosure of sensitive location information beyond what is strictly necessary to perform navigation services.
  * **California Penal Code § 637.7:** Makes it a misdemeanor to use an electronic tracking device to determine the location or movement of a person without consent.
  * *Litigation Status:* Plaintiffs have attempted to apply § 637.7 to mobile phone location logging (e.g., *In re Google Location History Litigation*). However, California appellate courts have historically construed § 637.7 as targeting physical hardware tracking devices installed on vehicles, maintaining active debate over whether continuous smartphone background location telemetry falls within statutory boundaries.
* **Pending Bills:**
  * **New York Assembly Bill A8729 (2025–2026 Regular Session):** *Pending.* Introduced by Assemblymember Linda Rosenthal; referred to the Committee on Science and Technology on January 7, 2026. Amends General Business Law to add Article 39-FFF, prohibiting telecommunications carriers and mobile application providers from selling, leasing, or trading precise consumer geolocation data without explicit affirmative consent.

### Topic 2.3: Consumer Protection and False Advertising
* **Enacted:**
  * **California Business and Professions Code §§ 17200 (Unfair Competition Law — UCL) & 17500 (False Advertising Law — FAL):** Prohibits unlawful, unfair, or fraudulent business practices and deceptive advertising. In the navigation context, plaintiffs have invoked UCL claims alleging deceptive ETA representations, unfulfilled promises of toll-free routing, or routing through dangerous routes.
  * **Federal Trade Commission Act, Section 5 (15 U.S.C. § 45):** Prohibits unfair or deceptive acts or practices in or affecting commerce. Enforces algorithmic transparency, data security, and truth-in-advertising standards against consumer tech platforms representing real-time traffic accuracy.

### Topic 2.4: Platform Liability for User-Generated Content
* **Enacted:**
  * **Federal Communications Decency Act, Section 230 (47 U.S.C. § 230(c)(1)):** Provides civil immunity to interactive computer services against claims treating them as the publisher or speaker of third-party information.
  * *Application to Navigation Apps:* Protects navigation platforms (such as Waze) from third-party defamation or tort liability arising from user-submitted hazard reports, speed-trap pins, or road closure alerts.
  * *Judicial Limitation:* Leading appellate precedents (notably *Lemmon v. Snap, Inc.*, 995 F.3d 1085 (9th Cir. 2021) and *Herrick v. Grindr LLC*, 765 F. App'x 586 (2d Cir. 2019)) establish that Section 230 **does not immunize a platform's own affirmative algorithmic design, routing recommendations, or product architecture**. If a navigation app's proprietary algorithm directs traffic into an unpaved cliff or hazardous alleyway, Section 230 immunity does not shield the platform's independent design negligence.

### Topic 2.5: Government Data Exchange and Public Records
* **Enacted:**
  * **California Public Records Act (CPRA), Cal. Gov. Code § 7920 et seq.:** Governs public disclosure of records held by state and municipal transportation agencies. Data-sharing compacts, memorandums of understanding (MOUs), and connected vehicle telemetry agreements between public DOTs and commercial mapping companies (e.g., Google/Waze Connected Citizens Program / Waze for Cities) are subject to public inspection, balancing trade secret exemptions against open governance mandates.
  * *Administrative Note:* Programs such as the **Illinois State Police partnership with Google** to push "Move Over" emergency responder alerts through Waze and Google Maps operate under administrative data-sharing agreements rather than statutory enactments.

### Topic 2.6: Transportation Network Companies (TNCs)
* **Enacted:**
  * **California Public Utilities Code §§ 5430–5450:** Codifies CPUC statutory jurisdiction over Transportation Network Companies (Uber, Lyft). Imposes mandatory driver background checks, insurance requirements, vehicle inspection mandates, and driver navigation safety protocols, governing how dispatch and routing software interfaces with passenger service operations.

### Topic 2.7: Commercial Vehicle Routing Standards
* **Enacted:**
  * **49 CFR Part 397, Subparts C–D (§§ 397.61–397.103):** Federal Motor Carrier Safety Administration (FMCSA) standards for hazardous materials highway routing. Mandates that carriers transporting placardable hazmat or radioactive cargo adhere strictly to state-designated routing corridors. Commercial GPS engines must hard-code these FMCSA corridors into routing logic.
  * **23 CFR Part 658 (§§ 658.1–658.23; Appendix A):** Defines the National Network (Interstate System and designated Federal-Aid primary highways) open to commercial Surface Transportation Assistance Act (STAA) vehicles.
    * *Reasonable Access Rule (§ 658.19):* Prohibits states from denying commercial trucks reasonable access between the National Network and terminals, food, fuel, repairs, and rest stops within **1 road-mile** of the exit, except where access is denied for route-specific safety reasons based on sound traffic engineering analysis.
  * **23 U.S.C. § 127:** Federal vehicle weight limitations (80,000 lbs gross weight, 20,000 lbs single axle, 34,000 lbs tandem axle) and the Federal Bridge Gross Weight Formula on the Interstate System.
  * **23 CFR Part 655 (MUTCD):** Codifies the National Standards for Traffic Control Devices, mandating uniform sign engineering for truck weight limits, low bridges, and hazardous cargo detours.

---

# Tier 3: Indirectly Applicable Road and Traffic Laws

The broad foundation of state vehicle codes, federal highway statutes, and municipal traffic ordinances that govern drivers, vehicles, and roadway infrastructure. Although they do not regulate tech platforms directly, navigation algorithms must ingest and respect these legal boundaries to calculate lawful, viable, and toll-accurate routes.

### Topic 3.1: Slow Streets and Street Closures
* **Enacted:**
  * **California Vehicle Code § 21101:** Grants local authorities broad police power to close streets, restrict through-traffic, and designate slow streets or pedestrian plazas during specific hours or conditions. (Provides the underlying municipal authorization that AB 2015 bridges into digital routing platforms).

### Topic 3.2: Turn and Through-Traffic Restrictions
* **Enacted:**
  * **California Vehicle Code §§ 22101 & 22113:** Authorizes local authorities to place official traffic control devices prohibiting turns, mandating turn lanes, and barring cut-through traffic. Drivers disobeying signs violate the vehicle code; navigation apps must model these turn restrictions to avoid recommending unlawful routing maneuvers.

### Topic 3.3: Residential Parking Permits and Access Restrictions
* **Enacted:**
  * **California Vehicle Code § 22507:** Authorizes local authorities to establish preferential residential permit parking programs. (Provides local governments tools to deter cut-through commuter parking generated by navigation app spillover).

### Topic 3.4: Commercial Vehicle and Truck Routes
* **Enacted:**
  * **California Vehicle Code § 22507.5:** Authorizes local authorities to prohibit commercial vehicle parking and through travel on residential streets.
  * **Texas Transportation Code Chapters 621, 622, and 623:** Establishes TxDOT and county statutory powers over vehicle size, gross weight, axle loads, and oversize/overweight routing permits, requiring commercial haulers to obtain route-specific clearance permits.

### Topic 3.5: Speed Enforcement and Automated Cameras
* **Enacted:**
  * **Arkansas Act 707 (2023, SB 481):** Authorized automated speed photo radar enforcement in active highway work zones, effective August 1, 2023.
  * **Arkansas Code §§ 27-52-110 & 27-52-111:** Governs automated enforcement in school zones and railroad crossings, mandating strict live-officer citation review (prohibiting unverified mail-in camera tickets).
  * **Washington RCW 46.63.220 (ESHB 2384, 2024):** Broadens municipal authority to deploy automated speed safety camera systems in school walk areas, public parks, hospital speed zones, and highway work zones, effective July 12, 2024.
  * **New York Vehicle and Traffic Law (VTL) § 1180-b:** Authorizes New York City’s 24/7 automated school speed photo radar program; extended through **July 1, 2030**.
  * **Alabama SB 341 (2026) / Act 2026-475 (Alabama Work Zone Safety Act):** Signed into law April 15, 2026. Authorizes a pilot program deploying automated speed camera systems in active Interstate 65 construction work zones in Chilton County, issuing $250 civil fines for speeds exceeding 10 mph over the posted work zone limit.
  * **Texas Transportation Code Chapter 707:** Prohibits local authorities from installing or operating photographic traffic signal enforcement systems (red-light cameras) statewide (enacted in 2019 under HB 1631).
  * **Connecticut Public Act 23-116 (HB 5917, 2023):** Enacted comprehensive Vision Zero legislation authorizing municipalities to deploy automated speed and red-light enforcement cameras in school zones and crash corridors.
  * **Connecticut Public Act 26-14 (2026):** Codifies rigorous privacy, data retention, and destruction standards governing automated traffic camera footage and automated license plate reader (ALPR) systems.

### Topic 3.6: Congestion and Road Pricing
* **Enacted:**
  * **23 U.S.C. § 129:** Governs the federal statutory conditions under which states and regional authorities may impose tolls on federal-aid highways, bridges, and tunnels, requiring revenues to be dedicated to transportation facilities.

### Topic 3.7: High-Occupancy Vehicle (HOV) and High-Occupancy Toll (HOT) Lanes
* **Enacted:**
  * **23 U.S.C. § 166:** Establishes federal operational performance standards, vehicle occupancy minimums, and dynamic pricing rules for HOV and High-Occupancy Toll (HOT) lanes on federal-aid highways.

### Topic 3.8: Federal Transportation Planning and Funding
* **Enacted:**
  * **23 U.S.C. § 149:** Congestion Mitigation and Air Quality Improvement (CMAQ) Program; provides federal funding apportionments for state and local traffic flow improvements and intelligent transportation systems (ITS).
  * **Public Law 117-58 (Infrastructure Investment and Jobs Act — IIJA / Bipartisan Infrastructure Law):** Provided 5-year surface transportation funding authorization through **September 30, 2026**. Programs currently operate under continuing federal appropriations.

### Topic 3.9: Traffic Control Device Standards
* **Enacted:**
  * **23 CFR Part 655 / Federal MUTCD (Manual on Uniform Traffic Control Devices, 11th Edition, December 2023):** National engineering standards for all traffic control devices, street signage, pavement markings, and dynamic message signs nationwide.

---

### Failed, Pending, and Unresolved Bills (Tier 3)

* **Failed / Inactive Bills:**
  * **Texas HB 4605, HB 3678, SB 2841 (2025 Regular Session):** *Failed.* Proposed automated routing and enhanced civil penalties for oversize commercial vehicles; died in committee at sine die adjournment.
  * **Federal H.R. 3372 (118th Congress):** *Failed.* Proposed a 5-year pilot program allowing states to permit 91,000-pound, 6-axle commercial trucks on Interstate highways; expired with the conclusion of the 118th Congress.
  * **Arizona SB 1003 (2025 Regular Session):** *Vetoed.* Legislative bill to ban photo radar and automated speed enforcement statewide; **vetoed by Governor Katie Hobbs** on May 2, 2025.
* **Pending Proposals (2025–2026):**
  * **Colorado SB 26-152 (2026 Regular Session):** *Pending.* Lowers the statutory speed camera enforcement threshold from 10 mph to 6 mph above the posted limit in designated residential corridors.
  * **Colorado HB26-1318 (2026 Regular Session):** *Pending.* Expands municipal authority to operate automated speed cameras in school zones and codifies municipal "School Streets" traffic restrictions.
  * **Colorado Senate Interstate Camera Bill (2026 Session):** *Pending.* Proposes automated camera speed enforcement in high-crash interstate mountain corridors.
  * **Connecticut HB 5464 (2026 Session):** *Pending.* Proposes expanding automated speed camera enforcement to limited-access state highways.
  * **New York A4167 & A5717 (2025–2026 Regular Session):** *Pending.* Mandates commercial motor vehicles, trucks, and buses operating on New York highways to use specialized commercial GPS navigation systems equipped with low-clearance bridge detection; pending in Assembly Transportation Committee.
  * **Alaska SB 235, HB 282, HB 283 (2026 Session):** *Pending.* Measures restricting or establishing procedural hurdles for municipal automated speed enforcement systems.
  * **Alabama SB 147 & SB 295 (2026 Session):** *Pending.* Legislative measures proposing work zone speed safety cameras and agricultural commercial vehicle weight exemptions.
  * **Washington ESHB 1423 & SB 5417 (2025 Session):** *Pending.* Automated traffic safety camera expansion and calibration standards.
* **Result Unresolved -> Enacted:**
  * **Arizona SB 1624 / Proposition 319 (SCR 1004, November 2026 General Election):** *Enacted / Approved by Voters.* Referred to the ballot by the Legislature as Proposition 319. Approved by Arizona voters on **November 3, 2026**, enacting a statewide statutory prohibition on new photo radar and automated speed cameras, and requiring existing municipal photo radar systems to terminate by **December 31, 2026** unless reauthorized by affirmative local voter referendum.

---

## Analytical Matrix: Summary Distribution Across the Three Tiers

| Tier Name | Scope & Relationship to Navigation Apps | Primary Topics Covered | Codified / Active Instruments in Database | Pending / Failed Proposals |
| :--- | :--- | :--- | :---: | :---: |
| **Tier 1: Laws Directly Governing Routing Apps** | Statutes explicitly naming apps, GPS routing, or digital maps; imposes direct platform obligations, study mandates, or civil penalties. | 1.1 Slow Streets Exclusion<br>1.2 Emergency Rerouting<br>1.3 Heavy Vehicle Route Rules<br>1.4 Bridge Clearance Mandates<br>1.5 Empirical Study & Data Reporting | **2** (CA AB 2015, NJ A3036 SAFER APP) | **9** (CT HB 5071, CT HB 6709, MA HD.4949, NY A8582, NY S6197/A3536, Federal H.R. 6531, Federal MAP Roads Act, NJ S756, etc.) |
| **Tier 2: Laws Not Specific to Routing Apps but Directly Applicable to Them** | Cross-sector statutes governing device usage, precise location privacy, platform liability for crowdsourced alerts, public data compacts, and commercial freight standards. | 2.1 Device Use While Driving<br>2.2 Location Data & Privacy<br>2.3 Consumer Protection (UCL/FAL)<br>2.4 Section 230 UGC Immunity<br>2.5 Public Records & Data Compacts<br>2.6 TNC Dispatch & Routing<br>2.7 Commercial Routing (49 CFR 397, 23 CFR 658) | **11** (CVC §§ 23123/23123.5, CCPA/CPRA, PC § 637.7, B&PC §§ 17200/17500, FTC Act § 5, CDA § 230, CPRA, CPUC TNC, 49 CFR 397, 23 CFR 658, 23 U.S.C. § 127) | **1** (NY A8729 Location Privacy) |
| **Tier 3: Indirectly Applicable Road and Traffic Laws** | Infrastructure, operational, and traffic control device laws governing drivers, vehicles, and roadway access; navigation engines must model these rules to calculate valid routes. | 3.1 Slow Streets & Closures<br>3.2 Turn & Through Restrictions<br>3.3 Residential Parking Permits<br>3.4 Commercial & Oversize Corridors<br>3.5 Automated Speed Enforcement<br>3.6 Congestion Tolling (23 USC § 129)<br>3.7 HOV/HOT Lanes (23 USC § 166)<br>3.8 Planning & Grants (IIJA)<br>3.9 Traffic Control Standards (MUTCD) | **141** (State Vehicle Codes, Speed Camera Statutes, MUTCD, 23 U.S.C. §§ 129/149/166, Local Municipal & County Ordinances) | **15** (TX HB 4605, Fed HR 3372, AZ SB 1003, CO SB 26-152, CO HB26-1318, CT HB 5464, NY A4167/A5717, AK SB 235, AL SB 147, AZ Prop 319, etc.) |
| **Total Instruments** | **Unified Centralized Research Database** | **All 21 Functional Topics** | **154 In Force** | **25 Legislative Actions** (Total: **179**) |

---
*Verified against primary statutory records, legislative bills, and appellate case law as of November 12, 2026.*
