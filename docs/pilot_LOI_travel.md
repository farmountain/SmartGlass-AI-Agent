# Letter of Intent: Travel Pilot Preview

## Partner Information
- **Travel Partner (Airline/Agency):** ____________________________
- **Primary Contacts:** __________________________
- **Airport/Hub/Route Coverage:** ____________________________
- **Preview Start Date:** ____________________________
- **Preview End Date:** ____________________________

## Preview Distribution Scope
- **Operational Zones:** Restricted to check-in counters, gate areas, and service desks approved by the partner.
- **User Eligibility:** Opt-in agents and supervisors; no passenger self-service flows during pilot.
- **Device Coverage:** Smart glasses issued per shift with serialized IDs mapped to agent roles.
- **Feature Set:** Real-time itinerary lookup, disruption playbooks, boarding support, and baggage status prompts.
- **Content Limitations:** No capture of passport/ID scans; avoid free-form passenger recording.

## Key Performance Indicators (KPIs)
- **Service Throughput:** Time to resolve check-in or rebooking vs. baseline workflow.
- **Recovery Effectiveness:** Reduction in missed connections handled manually; speed of disruption communications.
- **Customer Impact:** Passenger satisfaction signals (CSAT/NPS proxies) collected via partner-approved survey.
- **Reliability:** Successful API interactions with reservation systems and minimal timeout incidents.
- **Training & Adoption:** Agent session counts, completion of guided scenarios, and coaching feedback logged weekly.

## Operating Cadence
- **Readiness Reviews:** Twice-weekly syncs covering airport operations constraints and feature toggles.
- **Ops Reporting:** Incident and SLA dashboard circulated before peak travel windows; red/amber/green status calls.
- **Change Windows:** Deployments aligned to low-traffic periods; rollback scripts validated before each change.
- **Onsite Coverage:** Joint support during first two operational days per station; remote on-call thereafter.

## SDK Mock Requirements
- **Data Sources:** Mocked PNR queries, seat map views, baggage events, and flight status updates with stable schemas.
- **Latency Targets:** Sub-400ms p95 to mirror airport network variability; retries configurable.
- **Offline Mode:** Graceful degradation with cached itineraries and playbooks for temporary connectivity loss.
- **Event Logging:** Telemetry for lookup success, rebooking steps, device health, and error codes to validate analytics.

## Privacy & Safety Commitments
- **Data Protection:** No storage of passport, government ID, or payment data; minimal passenger identifiers limited to booking references when required.
- **Access Controls:** Role-based access for agents vs. supervisors; session timeouts aligned to airport security policy.
- **Safety in Use:** HUD elements sized for situational awareness; hands-free controls tested for airside safety rules.
- **Incident Handling:** Shared escalation matrix for privacy, security, or safety events with response SLAs.

## Acceptance & Signatures
- **Travel Partner Authorized Signatory:** ____________________________    **Date:** ______________
- **SmartGlass AI Authorized Signatory:** ____________________________    **Date:** ______________

---

# Pilot Outreach Materials (Travel Vertical)

## 2-Minute Demo Script

**Goal**: Show 3 tasks completed faster than baseline: rebooking, gate change, baggage lookup.

1. **Intro (10s)**
	- "This is SmartGlass AI for airport agents. It listens, sees, and helps in real time."

2. **Scenario 1: Rebooking (35s)**
	- Agent: "Rebook passenger to earliest flight to SFO."
	- System: Shows top 3 options, reads summary, suggests best choice.
	- Outcome: "Rebooking confirmed in 20 seconds."

3. **Scenario 2: Gate Change (35s)**
	- Agent: "Gate change for AA245."
	- System: Confirms gate update, auto-pushes notification.
	- Outcome: "Gate change announced without switching screens."

4. **Scenario 3: Baggage Status (30s)**
	- Agent: "Baggage status for PNR 8X7K2."
	- System: Displays last scan location, ETA, next step recommendation.

5. **Close (10s)**
	- "We reduce agent task time by 30–50% with hands-free assistance."

## 10-Slide Sales Deck Outline

1. **Title**: SmartGlass AI for Travel Operations
2. **Problem**: High cognitive load, slow task switching, delays
3. **Solution**: Hands-free multimodal AI on smart glasses
4. **How It Works**: Glasses → Mobile → Edge AI → Actions
5. **Use Cases**: Rebooking, gate changes, baggage, disruption playbooks
6. **Results**: Target 30–50% task time reduction, p95 latency <1.5s
7. **Safety & Privacy**: Opt-in data, no raw storage by default
8. **Pilot Plan**: 4-week pilot, 10–50 agents, clear KPIs
9. **Pricing**: $50K–$100K pilot, $500–$1,000 per device/year
10. **Next Steps**: LOI + hardware trial schedule

## Pilot Pricing Sheet (Draft)

**Pilot Package (4–6 weeks)**
- **$50K** for 10–25 devices
- **$100K** for 26–50 devices
- Includes onboarding, analytics dashboard, weekly support

**Annual Deployment (Post-Pilot)**
- **$500–$1,000 per device/year** (volume-based)
- Optional integrations: $25K–$100K depending on system complexity

**Notes**
- Hardware cost not included (can be procured by partner or bundled).
- SLA and uptime guarantees available at enterprise tier.
