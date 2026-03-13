"""
Mind Map Generation Pipeline (Isolated Module)
-------------------------------------------------
This file contains ONLY the logic used to generate AI-based intelligence mind maps.

Usage:
from open_notebook.utils.mindmap_engine import MindMapEngine
engine = MindMapEngine()
result = engine.generate_mind_map(text)

Dependencies:
- langchain_core
- your LLM configuration
"""

import re
import json
import logging
from typing import Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# -------------------------------------------------
# LOGGER
# -------------------------------------------------
logger = logging.getLogger("MindMapEngine")

class MindMapEngine:
    """Standalone Mind Map Generation Engine"""

    def __init__(self, llm=None):
        logger.info("🧠 Initializing MindMapEngine")
        self.llm = llm

        # ===== LLM PROMPT FOR INTELLIGENCE MIND MAP =====
      self.mindmap_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a top-tier professional intelligence analyst and expert at constructing highly structured, hierarchical mind maps from raw intelligence text.\n\n"
        "OBJECTIVE:\n"
        "Analyze the intelligence text deeply, extract all relevant information, and organize it into a detailed, fully hierarchical JSON mind map optimized for NotebookLLM visualization.\n\n"
        "STRICT GUIDELINES:\n"
        "1. The root node MUST be the Subject Name or Document Title.\n"
        "2. Generate up to 6 high-level intelligence categories using meaningful analytical dimensions only.\n"
        "   Examples: Identity, Background, Criminal History, Legal Status, Gang Affiliations, Associates, Financial Links, Locations, Modus Operandi, Timeline.\n"
        "   Avoid generic or vague categories (e.g., CRIME, INCIDENT, ATTACK).\n"
        "3. For each category, automatically detect and create sub-categories if the facts contain multiple aspects.\n"
        "   Examples of dynamic sub-categories:\n"
        "     - Financial Links → Assets, Bank Accounts, Transactions, Companies\n"
        "     - Associates → Family, Criminal Contacts, Business Partners\n"
        "     - Timeline → Year, Month, Event\n"
        "     - Locations → Cities, Countries, Facilities\n"
        "4. Each child node must be a complete, atomic, factual statement extracted from the text.\n"
        "5. Remove duplicate facts and omit empty categories/sub-categories entirely.\n"
        "6. Maintain strict factual accuracy; do NOT infer unsupported information.\n"
        "7. Use up to 4 hierarchical levels: root → category → sub-category → fact.\n"
        "8. Include explicit references to dates, locations, organizations, or people mentioned in the text.\n"
        "9. Avoid abbreviations unless they appear in the text.\n"
        "10. Group related facts logically within sub-categories to enhance clarity.\n"
        "11. Return STRICTLY valid JSON in this format:\n"
        '{\n'
        '  "label": "Subject Name",\n'
        '  "children": [\n'
        '    {\n'
        '      "label": "Category",\n'
        '      "children": [\n'
        '        {\n'
        '          "label": "Sub-Category",\n'
        '          "children": [\n'
        '            {"label": "Fact"}\n'
        '          ]\n'
        '        }\n'
        '      ]\n'
        '    }\n'
        '  ]\n'
        '}\n\n'
        "ADDITIONAL NOTE FOR NotebookLLM:\n"
        "- Analyze the text comprehensively and detect relationships, timelines, patterns, and connections.\n"
        "- Auto-generate sub-categories wherever a category contains multiple types of facts.\n"
        "- Facts must be self-contained, precise, and maximally informative.\n"
        "- Ensure the JSON is fully parseable and structured for immediate mind map rendering.\n"
        "- Prioritize clarity, completeness, and hierarchical organization to support complex intelligence analysis."
    ),
    (
        "human",
        "Subject: {person}\nIntelligence Text:\n{context}"
    )
])
        if self.llm:
            self.mindmap_chain = self.mindmap_prompt | self.llm | StrOutputParser()

    # -------------------------------------------------
    # ENTITY DETECTION (MAIN PERSON)
    # -------------------------------------------------
    def detect_main_person(self, text: str) -> str:
        """Detect the main person/subject from the text"""
        persons = re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)+\b", text)
        return max(set(persons), key=persons.count) if persons else "Subject"

    # -------------------------------------------------
    # SAFE JSON PARSER
    # -------------------------------------------------
    def safe_json_load(self, text: str) -> Dict[str, Any]:
        """Safely parse JSON from LLM response"""
        try:
            return json.loads(text)
        except Exception:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            raise ValueError("Invalid JSON from LLM")

    # -------------------------------------------------
    # REMOVE DUPLICATES & CLEAN TREE
    # -------------------------------------------------
    def deduplicate_mindmap(self, mind_map: Dict) -> Dict:
        """Remove duplicate categories and facts"""
        if not isinstance(mind_map, dict):
            return mind_map

        seen_categories = set()
        clean_children = []

        for category in mind_map.get("children", []):
            label = category.get("label", "").strip()
            if not label or label in seen_categories:
                continue
            seen_categories.add(label)

            seen_facts = set()
            facts = []
            for child in category.get("children", []):
                fact = child.get("label", "").strip()
                if fact and fact not in seen_facts:
                    seen_facts.add(fact)
                    facts.append({"label": fact})

            if facts:
                clean_children.append({"label": label, "children": facts})

        mind_map["children"] = clean_children
        return mind_map

    # -------------------------------------------------
    # TABULAR DATA DETECTION & PROCESSING
    # -------------------------------------------------
    def detect_tabular_data(self, text: str) -> bool:
        """Detect if text contains tabular/spreadsheet data"""
        # Check for common table indicators
        pipe_count = text.count('|')
        tab_count = text.count('\t')

        # Check for repeated patterns (like cell IDs, phone numbers)
        cell_id_pattern = r'\d{14,}' # Long numeric IDs
        cell_ids = re.findall(cell_id_pattern, text)

        # Check for call record patterns
        call_pattern = r'Total Call(?:Total|In|Out)'
        has_call_data = bool(re.search(call_pattern, text, re.IGNORECASE))

        # Check for repeated phone numbers (10 digits)
        phone_pattern = r'\b\d{10}\b'
        phones = re.findall(phone_pattern, text)

        # Log detection metrics
        logger.info(f"📊 Tabular Detection: pipes={pipe_count}, tabs={tab_count}, cell_ids={len(cell_ids)}, phones={len(phones)}, call_data={has_call_data}")

        # If we have many pipes/tabs or repeated numeric patterns, it's likely tabular
        is_tabular = (pipe_count > 20 or tab_count > 20 or len(cell_ids) > 5 or
                      (has_call_data and len(phones) > 3))

        logger.info(f"📊 Is Tabular: {is_tabular}")
        return is_tabular

    def extract_tabular_structure(self, text: str, title: str) -> Dict:
        """Extract structured mind map from tabular data"""
        logger.info("📊 Detected tabular data, creating structured groupings")

        children = []

        # Extract phone numbers
        phone_pattern = r'\b\d{10}\b'
        phones = list(set(re.findall(phone_pattern, text)))
        if phones:
            phone_nodes = [{"label": f"Phone: {phone}"} for phone in phones[:10]]
            children.append({"label": "Contact Numbers", "children": phone_nodes})
            logger.info(f" ✓ Added Contact Numbers: {len(phone_nodes)} phones")

        # Extract Cell IDs and group by location patterns
        cell_id_pattern = r'(\d{14,})'
        cell_ids = re.findall(cell_id_pattern, text)

        # Extract addresses/locations
        location_pattern = r'(?:R/O|R/o|Resident of|Village|Near)\s+([^|,\n]{10,100})'
        locations = re.findall(location_pattern, text, re.IGNORECASE)

        if locations:
            # Group locations by area/district
            location_groups = {}
            for loc in locations[:20]: # Limit to 20 locations
                loc = loc.strip()
                # Try to extract district/area name
                area_match = re.search(r'\b(Anantnag|Shopian|Pulwama|Bijbehara|[A-Z][a-z]+)\b', loc)
                area = area_match.group(1) if area_match else "Other Areas"

                if area not in location_groups:
                    location_groups[area] = []
                if len(location_groups[area]) < 5: # Max 5 per area
                    location_groups[area].append({"label": loc[:80]})

            # Create location nodes
            location_children = []
            for area, locs in location_groups.items():
                if locs:
                    location_children.append({"label": area, "children": locs})

            if location_children:
                children.append({"label": "Locations", "children": location_children})
            logger.info(f" ✓ Added Locations: {len(location_children)} areas")

        # Extract call statistics
        call_patterns = [
            (r'Total CallTotal\s*:\s*(\d+)', 'Total Calls'),
            (r'Total CallIn\s*:\s*(\d+)', 'Incoming Calls'),
            (r'Total CallOut\s*:\s*(\d+)', 'Outgoing Calls'),
            (r'Total SMS(?:In|Out)\s*:\s*(\d+)', 'SMS Count'),
        ]

        call_stats = []
        for pattern, label in call_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                call_stats.append({"label": f"{label}: {matches[0]}"})

        if call_stats:
            children.append({"label": "Call Statistics", "children": call_stats})
            logger.info(f" ✓ Added Call Statistics: {len(call_stats)} stats")

        # Extract names (proper nouns)
        name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b'
        names = re.findall(name_pattern, text)
        # Filter out common words and get unique names
        common_words = {'Near', 'Village', 'District', 'Tehsil', 'Police', 'Station', 'Total', 'Call', 'Sheet'}
        unique_names = []
        seen = set()
        for name in names:
            if name not in common_words and name not in seen and len(name) > 5:
                seen.add(name)
                unique_names.append({"label": name})
            if len(unique_names) >= 10:
                break

        if unique_names:
            children.append({"label": "Persons/Entities", "children": unique_names})
            logger.info(f" ✓ Added Persons/Entities: {len(unique_names)} names")

        # Extract dates
        date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b'
        dates = list(set(re.findall(date_pattern, text)))
        if dates:
            date_nodes = [{"label": f"Date: {date}"} for date in dates[:10]]
            children.append({"label": "Timeline", "children": date_nodes})

        # Extract case/FIR numbers
        case_pattern = r'(?:FIR|Case|File)\s*(?:No|Number)?[.:]?\s*([A-Z0-9/-]+)'
        cases = list(set(re.findall(case_pattern, text, re.IGNORECASE)))
        if cases:
            case_nodes = [{"label": f"Case: {case}"} for case in cases[:10]]
            children.append({"label": "Case References", "children": case_nodes})

        # If we found cell IDs but no other structure, add them
        if cell_ids and not any(c['label'] == 'Cell Tower IDs' for c in children):
            unique_cells = list(set(cell_ids))[:15]
            cell_nodes = [{"label": f"Cell ID: {cid}"} for cid in unique_cells]
            children.append({"label": "Cell Tower IDs", "children": cell_nodes})

        # If no children found, create a basic structure
        if not children:
            # Extract first few lines as summary
            lines = [l.strip() for l in text.split('\n') if l.strip()][:5]
            summary_nodes = [{"label": line[:100]} for line in lines]
            children.append({"label": "Data Summary", "children": summary_nodes})
            logger.info(f" ⚠️ No patterns found, added Data Summary: {len(summary_nodes)} lines")

        logger.info(f"📊 Tabular extraction complete: {len(children)} main categories")
        logger.info(f"📊 Children structure: {[c['label'] for c in children]}")

        return {
            "label": title or "Tabular Data Report",
            "children": children
        }

    # -------------------------------------------------
    # FALLBACK RULE-BASED MIND MAP
    # -------------------------------------------------
    def fallback_mindmap(self, person: str, text: str) -> Dict:
        """Generate rule-based mind map when LLM fails"""
        def extract_sentences(pattern, limit=8):
            sentences = re.split(r"(?<=[.!?])\s+", text)
            matches = []
            for s in sentences:
                if re.search(pattern, s, re.I):
                    clean = s.strip()
                    if 20 < len(clean) < 300:
                        matches.append({"label": clean})
                    if len(matches) >= limit:
                        break
            return matches

        # Extract incidents
        incident_pattern = r'(\d+(?:ST|ND|RD|TH)?\s*INCIDENT)'
        incident_matches = list(re.finditer(incident_pattern, text, re.IGNORECASE))

        children = []

        if incident_matches:
            # Criminal case structure
            incidents = []
            for i, match in enumerate(incident_matches[:10]): # Limit to 10 incidents
                start = match.start()
                end = incident_matches[i+1].start() if i+1 < len(incident_matches) else len(text)
                incident_text = text[start:end].strip()
                incident_title = incident_text.split('\n')[0][:100]

                # Extract key facts from incident
                facts = []
                fir_match = re.search(r'FIR\s*NO[.:]?\s*(\d+/\d+)', incident_text, re.IGNORECASE)
                if fir_match:
                    facts.append({"label": f"FIR: {fir_match.group(1)}"})

                date_matches = re.findall(r'\b(\d{2}[./]\d{2}[./]\d{4})\b', incident_text)
                if date_matches:
                    facts.append({"label": f"Date: {date_matches[0]}"})

                if facts:
                    incidents.append({"label": incident_title, "children": facts})

            if incidents:
                children.append({"label": "Criminal Incidents", "children": incidents})

        # Add other categories
        children.extend([
            {"label": "Identity & Background", "children": extract_sentences(r"address|village|resident|age|dob|born", 6)},
            {"label": "Family & Associates", "children": extract_sentences(r"father|mother|brother|sister|associate|gang|friend", 6)},
            {"label": "Legal Status", "children": extract_sentences(r"arrest|court|bail|custody|trial|jail|prison", 6)},
        ])

        # Remove empty categories
        children = [c for c in children if c.get("children")]

        return {
            "label": person,
            "children": children,
        }

    # -------------------------------------------------
    # MAIN PUBLIC FUNCTION
    # -------------------------------------------------
    def generate_mind_map(self, full_text: str, title: Optional[str] = None) -> Dict:
        """Main API to generate mind map from text"""
        person = title or self.detect_main_person(full_text)

        # Check if this is tabular data first
        if self.detect_tabular_data(full_text):
            logger.info("📊 Tabular data detected, using specialized extraction")
            return self.extract_tabular_structure(full_text, person)

        # If no LLM configured, use fallback
        if not self.llm:
            logger.info("⚠️ No LLM configured, using rule-based fallback")
            return self.fallback_mindmap(person, full_text)

        try:
            logger.info(f"🤖 Generating AI mind map for: {person}")
            raw = self.mindmap_chain.invoke({
                "person": person,
                "context": full_text[:12000] # Limit context to 12k chars
            })

            mind_map = self.safe_json_load(raw)
            if not mind_map.get("children"):
                raise ValueError("Empty mind map")

            mind_map = self.deduplicate_mindmap(mind_map)
            logger.info("✅ LLM Mind Map Generated")
            return mind_map

        except Exception as e:
            logger.warning(f"⚠️ LLM mind map failed, using fallback: {e}")
            # Check if tabular before using standard fallback
            if self.detect_tabular_data(full_text):
                return self.extract_tabular_structure(full_text, person)
            return self.fallback_mindmap(person, full_text)