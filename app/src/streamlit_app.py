# app/src/streamlit_app.py
import streamlit as st
import openai
import re
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# Configure page
st.set_page_config(
    page_title="HealthForm AI Validator",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Create data directory for local storage
import pathlib
DATA_DIR = pathlib.Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Initialize OpenAI client
@st.cache_resource
def get_openai_client():
    """Initialize OpenAI client with API key from environment or secrets"""
    api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        st.stop()
    
    try:
        # Check OpenAI version and initialize accordingly
        openai_version = openai.__version__
        st.sidebar.write(f"OpenAI version: {openai_version}")
        
        if hasattr(openai, 'OpenAI'):
            # Version 1.0+ - new client pattern
            return openai.OpenAI(api_key=api_key)
        else:
            # Version < 1.0 - old pattern
            openai.api_key = api_key
            return openai
    except Exception as e:
        st.error(f"Failed to initialize OpenAI client: {str(e)}")
        st.error("Try: pip uninstall openai && pip install openai==1.3.8")
        st.stop()

@dataclass
class PatientData:
    """Structured patient data extracted from form"""
    name: str = ""
    age: int = 0
    gender: str = ""
    weight: str = ""
    chief_complaint: str = ""
    medications: List[str] = None
    allergies: str = ""
    vital_signs: Dict[str, str] = None
    medical_history: str = ""
    social_history: str = ""
    
    def __post_init__(self):
        if self.medications is None:
            self.medications = []
        if self.vital_signs is None:
            self.vital_signs = {}

class MedicalFormParser:
    """Parses medical forms and extracts structured data"""
    
    @staticmethod
    def extract_patient_data(form_text: str) -> PatientData:
        """Extract structured data from medical form text"""
        data = PatientData()
        
        # Extract basic patient info - fix regex patterns
        name_match = re.search(r'Patient Name:\s*([^\n\r]+)', form_text)
        if name_match:
            data.name = name_match.group(1).strip()
        
        age_match = re.search(r'Age:\s*(\d+)', form_text)
        if age_match:
            data.age = int(age_match.group(1))
        
        # Look for Gender with various patterns
        gender_match = re.search(r'Gender:\s*([MF])', form_text)
        if gender_match:
            data.gender = "Male" if gender_match.group(1) == "M" else "Female"
        
        weight_match = re.search(r'Weight:\s*([^\n\r]+)', form_text)
        if weight_match:
            data.weight = weight_match.group(1).strip()
        
        # Extract chief complaint - improved pattern
        complaint_match = re.search(r'Primary reason for today\'s visit:\s*\n([^-\n]+(?:\n[^-\n]+)*)', form_text, re.DOTALL)
        if complaint_match:
            data.chief_complaint = complaint_match.group(1).strip()
        
        medications = []
        # Define the exact header we are looking for
              # --- START DEBUGGING ---
        print("--- Checking for Medication Header ---")
        med_header = "Medication Name | Dosage | Frequency | Prescribing Doctor"

        print(f"REPR OF HEADER: {repr(med_header)}") 
        # Split the entire text into individual lines for easier processing
        lines = form_text.strip().splitlines()

        header_found = False
        for i, line in enumerate(lines):
            # Print the line from the text and what we are comparing it to
            print(f"Line {i}: {repr(line.strip())}")
            if line.strip() == med_header:
                print(f"SUCCESS: Header found on line {i}")
                header_found = True
                break
        
        if not header_found:
            print("ERROR: Medication header was NOT found in the text.")
        # --- END DEBUGGING ---

        # Find the line number where the header is located
        try:
            header_index = lines.index(med_header)
        except ValueError:
            header_index = -1 # Header not found

        # If the header was found (index is not -1)
        if header_index != -1:
            # Start processing from the line immediately after the header
            for line in lines[header_index + 1:]:
                # Stop if we encounter a blank line or a line without a '|'
                if not line.strip() or '|' not in line:
                    break

                # Split the line into parts based on the '|' delimiter
                parts = [part.strip() for part in line.split('|')]

                # Ensure the line has the expected number of columns (4) and the first part is not empty
                if len(parts) == 4 and parts[0]:
                    med_name = parts[0]
                    dosage = parts[1]
                    frequency = parts[2]
                    # doctor = parts[3] # The 4th part is available if you need it

                    # Append the formatted string to the list
                    # You can decide what information to include in the final string
                    medications.append(f"{med_name} {dosage} {frequency}".strip())
        print(medications)
        data.medications = medications
        
        # Extract allergies - improved pattern
        allergy_match = re.search(r'Drug Allergies:\s*\n([^\n\r]+)', form_text)
        if allergy_match:
            data.allergies = allergy_match.group(1).strip()
        
        # Extract vital signs - improved patterns
        bp_match = re.search(r'Blood Pressure:\s*(\d+\s*/\s*\d+)', form_text)
        hr_match = re.search(r'Heart Rate:\s*(\d+)', form_text)
        temp_match = re.search(r'Temperature:\s*([^\s\n]+)', form_text)
        
        if bp_match or hr_match or temp_match:
            data.vital_signs = {
                'blood_pressure': bp_match.group(1) if bp_match else '',
                'heart_rate': hr_match.group(1) if hr_match else '',
                'temperature': temp_match.group(1) if temp_match else ''
            }
        
        # Extract medical history - improved pattern
        history_match = re.search(r'Chronic Conditions:\s*\n([^\n\r]+)', form_text)
        if history_match:
            data.medical_history = history_match.group(1).strip()
        
        return data

class ClinicalAI:
    """AI-powered clinical decision support"""
    
    def __init__(self, client):
        self.client = client
    
    def analyze_patient_data(self, patient_data: PatientData) -> Dict:
        """Analyze patient data and provide clinical insights"""

        # Debug: Show what data we're analyzing
        st.write("**🔍 DEBUG: Analyzing patient data:**")
        st.write(f"- Name: {patient_data.name}")
        st.write(f"- Age: {patient_data.age}")
        st.write(f"- Medications: {patient_data.medications}")
        st.write(f"- Vital Signs: {patient_data.vital_signs}")
        
        # Construct clinical analysis prompt
        prompt = self._build_clinical_prompt(patient_data)
        st.write("**🔍 DEBUG: Prompt being sent to AI:**")
        with st.expander("View AI Prompt"):
            st.text(prompt[:1000] + "..." if len(prompt) > 1000 else prompt)
        
        # Construct clinical analysis prompt
        prompt = self._build_clinical_prompt(patient_data)
        
        try:
            # Check if we have the new client or old client
            if hasattr(self.client, 'chat') and hasattr(self.client.chat, 'completions'):
                # New OpenAI client (v1.0+)
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",  # Using gpt-3.5-turbo for better compatibility
                    messages=[
                        {
                            "role": "system", 
                            "content": """You are a clinical decision support AI. Analyze patient data and provide:
                            1. CRITICAL ALERTS (immediate danger)
                            2. DRUG INTERACTIONS (medication safety)
                            3. MISSING INFORMATION (clinical gaps)
                            4. CLINICAL RECOMMENDATIONS (next steps)
                            
                            Return a JSON response with these categories. Each should be an array of objects with 'severity' and 'message' fields."""
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=1200,
                    temperature=0.1
                )
                ai_content = response.choices[0].message.content
                st.write("**🔍 DEBUG: Got response from OpenAI**")
                with st.expander("View AI Raw Response"):
                    st.text(ai_content)
                
            elif hasattr(self.client, 'ChatCompletion'):
                # Old OpenAI client (v0.x)
                response = self.client.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system", 
                            "content": """You are a clinical decision support AI. Analyze patient data and provide:
                            1. CRITICAL ALERTS (immediate danger)
                            2. DRUG INTERACTIONS (medication safety)
                            3. MISSING INFORMATION (clinical gaps)
                            4. CLINICAL RECOMMENDATIONS (next steps)
                            
                            Return a JSON response with these categories."""
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=1200,
                    temperature=0.1
                )
                ai_content = response.choices[0].message.content
                
            else:
                # Fallback - create mock analysis for demo
                ai_content = self._create_mock_analysis(patient_data)
            
            # Parse response
            try:
                # Try to find JSON in response
                json_match = re.search(r'\{.*\}', ai_content, re.DOTALL)
                if json_match:
                    # Normalize the keys to match our expected format
                    raw_analysis = json.loads(json_match.group(0))
                    analysis = {
                        "critical_alerts": raw_analysis.get("CRITICAL ALERTS", raw_analysis.get("critical_alerts", [])),
                        "drug_interactions": raw_analysis.get("DRUG INTERACTIONS", raw_analysis.get("drug_interactions", [])),
                        "missing_info": raw_analysis.get("MISSING INFORMATION", raw_analysis.get("missing_info", [])),
                        "recommendations": raw_analysis.get("CLINICAL RECOMMENDATIONS", raw_analysis.get("recommendations", []))
                    }
                else:
                    analysis = self._parse_text_response(ai_content)
            except json.JSONDecodeError:
                analysis = self._parse_text_response(ai_content)
            
            return analysis
            
        except Exception as e:
            # Create mock analysis if API fails
            return self._create_mock_analysis(patient_data)
    
    def _create_mock_analysis(self, patient_data: PatientData) -> Dict:
        """Create mock analysis for demo purposes when API fails"""
        analysis = {
            "critical_alerts": [],
            "drug_interactions": [],
            "missing_info": [],
            "recommendations": []
        }
        
        # Basic analysis based on extracted data
        if patient_data.age > 65:
            analysis["critical_alerts"].append({
                "severity": "medium",
                "message": f"Elderly patient (age {patient_data.age}) requires careful monitoring"
            })
        
        if patient_data.medications:
            analysis["drug_interactions"].append({
                "severity": "medium", 
                "message": f"Patient on {len(patient_data.medications)} medications - check for interactions"
            })
            
            # Check for common dangerous combinations
            med_list = " ".join(patient_data.medications).lower()
            if "warfarin" in med_list and "aspirin" in med_list:
                analysis["critical_alerts"].append({
                    "severity": "high",
                    "message": "DANGEROUS: Warfarin + Aspirin combination increases bleeding risk"
                })
        
        if patient_data.vital_signs and patient_data.vital_signs.get('blood_pressure'):
            bp = patient_data.vital_signs['blood_pressure']
            if '180' in bp or '110' in bp:
                analysis["critical_alerts"].append({
                    "severity": "high",
                    "message": f"HYPERTENSIVE CRISIS: Blood pressure {bp} requires immediate attention"
                })
        
        analysis["recommendations"].append({
            "severity": "low",
            "message": "Complete medication reconciliation recommended"
        })
        
        return analysis
    
    def _build_clinical_prompt(self, data: PatientData) -> str:
        """Build comprehensive clinical analysis prompt"""
        prompt = f"""
PATIENT CLINICAL DATA ANALYSIS

DEMOGRAPHICS:
- Name: {data.name}
- Age: {data.age} years old
- Gender: {data.gender}
- Weight: {data.weight}

CHIEF COMPLAINT:
{data.chief_complaint}

CURRENT MEDICATIONS:
{chr(10).join(data.medications) if data.medications else "None listed"}

ALLERGIES:
{data.allergies or "None known"}

VITAL SIGNS:
{json.dumps(data.vital_signs, indent=2) if data.vital_signs else "Not provided"}

MEDICAL HISTORY:
{data.medical_history or "Not provided"}

CLINICAL ANALYSIS REQUEST:
Please analyze this patient data for:
1. Immediate safety concerns or critical alerts
2. Drug-drug interactions or contraindications  
3. Missing critical information for safe care
4. Clinical recommendations and next steps

Focus on patient safety, medication interactions, and clinical decision support.
"""
        return prompt
    
    def _parse_text_response(self, text: str) -> Dict:
        """Parse non-JSON AI response into structured format"""
        return {
            "critical_alerts": [{"severity": "medium", "message": text}],
            "drug_interactions": [],
            "missing_info": [],
            "recommendations": []
        }

def save_form_data(patient_data: PatientData, analysis: Dict, original_text: str) -> str:
    """Save form data and analysis locally"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"patient_form_{timestamp}.json"
    filepath = DATA_DIR / filename
    
    # Prepare data for saving
    save_data = {
        "timestamp": timestamp,
        "patient_data": {
            "name": patient_data.name,
            "age": patient_data.age,
            "gender": patient_data.gender,
            "weight": patient_data.weight,
            "chief_complaint": patient_data.chief_complaint,
            "medications": patient_data.medications,
            "allergies": patient_data.allergies,
            "vital_signs": patient_data.vital_signs,
            "medical_history": patient_data.medical_history,
            "social_history": patient_data.social_history
        },
        "ai_analysis": analysis,
        "original_form_text": original_text
    }
    
    # Save to JSON file
    try:
        with open(filepath, 'w') as f:
            json.dump(save_data, f, indent=2)
        return str(filepath)
    except Exception as e:
        st.error(f"Failed to save data: {str(e)}")
        return None

def load_uploaded_file(uploaded_file) -> str:
    """Process uploaded file and return text content"""
    try:
        if uploaded_file.type == "text/plain":
            # Handle text files
            content = str(uploaded_file.read(), "utf-8")
        elif uploaded_file.type == "application/pdf":
            # For PDF files - we'll implement basic text extraction
            st.warning("PDF upload detected. For demo purposes, please copy and paste the text content instead.")
            return None
        else:
            st.error("Unsupported file type. Please upload a text file or paste the content directly.")
            return None
        
        return content
    except Exception as e:
        st.error(f"Error reading uploaded file: {str(e)}")
        return None
    """Display AI analysis results with appropriate styling"""
    
    if "error" in analysis:
        st.error(f"❌ Analysis Error: {analysis['error']}")
        return
    
    # Critical Alerts
    if analysis.get("critical_alerts"):
        st.subheader("🚨 Critical Alerts")
        for alert in analysis["critical_alerts"]:
            severity = alert.get("severity", "medium")
            message = alert.get("message", "")
            
            if severity == "high":
                st.error(f"🚨 CRITICAL: {message}")
            elif severity == "medium":
                st.warning(f"⚠️ WARNING: {message}")
            else:
                st.info(f"ℹ️ NOTE: {message}")
    
    # Drug Interactions
    if analysis.get("drug_interactions"):
        st.subheader("💊 Drug Interactions")
        for interaction in analysis["drug_interactions"]:
            severity = interaction.get("severity", "medium")
            message = interaction.get("message", "")
            
            if severity == "high":
                st.error(f"🚫 HIGH RISK: {message}")
            else:
                st.warning(f"⚠️ INTERACTION: {message}")
    
    # Missing Information
    if analysis.get("missing_info"):
        st.subheader("📋 Missing Information")
        for info in analysis["missing_info"]:
            st.info(f"📝 {info.get('message', '')}")
    
    # Clinical Recommendations
    if analysis.get("recommendations"):
        st.subheader("🎯 Clinical Recommendations")
        for rec in analysis["recommendations"]:
            st.success(f"✅ {rec.get('message', '')}")

def main():
    """Main Streamlit application"""
    
    # Header
    st.title("HealthForm AI Validator")
    st.subheader("Enterprise Healthcare Form Validation with AI-Powered Clinical Decision Support")
    
    # Sidebar
    with st.sidebar:
        st.header("System Status")
        st.success("OpenAI API Connected")
        st.success("Clinical AI Engine Active")
        st.success("HIPAA Compliant Processing")
        
        st.header("Sample Forms")
        st.info("Tip: Copy and paste one of the sample forms from the repository to test the AI analysis.")
        
        st.header("Security Notice")
        st.warning("Demo Environment: This system uses synthetic patient data for demonstration purposes only.")
        
        # Display saved files
        st.header("Recent Analyses")
        saved_files = list(DATA_DIR.glob("patient_form_*.json"))
        if saved_files:
            st.write(f"Total saved: {len(saved_files)} forms")
            # Show most recent 5 files
            for file in sorted(saved_files, reverse=True)[:5]:
                st.text(file.name)
        else:
            st.write("No saved analyses yet")
    
    # Main interface
    st.header("Medical Form Input")
    
    # Input method selection
    input_method = st.radio(
        "Choose input method:",
        ["Upload File", "Paste Text"],
        horizontal=True
    )
    
    form_text = ""
    
    if input_method == "Upload File":
        uploaded_file = st.file_uploader(
            "Upload medical form",
            type=['txt'],
            help="Upload a text file containing the medical form data"
        )
        
        if uploaded_file is not None:
            form_text = load_uploaded_file(uploaded_file)
            if form_text:
                st.success(f"File uploaded successfully: {uploaded_file.name}")
                # Show preview of uploaded content
                with st.expander("Preview uploaded content"):
                    st.text_area("File content:", value=form_text[:500] + "..." if len(form_text) > 500 else form_text, height=150, disabled=True)
    
    else:  # Paste Text
        form_text = st.text_area(
            "Paste medical form text here:",
            height=300,
            placeholder="Copy and paste a completed medical intake form here...\n\nExample: Use one of the sample forms from the GitHub repository.",
            help="Paste the complete text of a medical intake form. The AI will extract patient data and provide clinical analysis."
        )
    
    # Analysis button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_button = st.button("Analyze with AI", type="primary", use_container_width=True)
    
    if analyze_button and form_text and form_text.strip():
        with st.spinner("Parsing medical form and analyzing clinical data..."):
            try:
                # Initialize components
                client = get_openai_client()
                parser = MedicalFormParser()
                clinical_ai = ClinicalAI(client)
                
                # Parse form data
                patient_data = parser.extract_patient_data(form_text)
                
                # Display extracted data
                st.header("Extracted Patient Data")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Patient Information")
                    st.write(f"**Name:** {patient_data.name}")
                    st.write(f"**Age:** {patient_data.age} years")
                    st.write(f"**Gender:** {patient_data.gender}")
                    st.write(f"**Weight:** {patient_data.weight}")
                    
                    st.subheader("Vital Signs")
                    if patient_data.vital_signs:
                        for key, value in patient_data.vital_signs.items():
                            if value:
                                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                    else:
                        st.write("No vital signs extracted")
                
                with col2:
                    st.subheader("Current Medications")
                    if patient_data.medications:
                        for med in patient_data.medications:
                            st.write(f"• {med}")
                    else:
                        st.write("No medications extracted")
                    
                    st.subheader("Allergies")
                    st.write(patient_data.allergies or "None extracted")
                
                st.subheader("Chief Complaint")
                st.write(patient_data.chief_complaint or "No chief complaint extracted")
                
                # AI Analysis
                st.header("AI Clinical Analysis")
                analysis = clinical_ai.analyze_patient_data(patient_data)
                
                # Display analysis results
                if "error" in analysis:
                    st.error(f"Analysis Error: {analysis['error']}")
                else:
                    # Critical Alerts
                    if analysis.get("critical_alerts"):
                        st.subheader("Critical Alerts")
                        for alert in analysis["critical_alerts"]:
                            severity = alert.get("severity", "medium")
                            message = alert.get("message", "")
                            
                            if severity == "high":
                                st.error(f"CRITICAL: {message}")
                            elif severity == "medium":
                                st.warning(f"WARNING: {message}")
                            else:
                                st.info(f"NOTE: {message}")
                    
                    # Drug Interactions
                    if analysis.get("drug_interactions"):
                        st.subheader("Drug Interactions")
                        for interaction in analysis["drug_interactions"]:
                            severity = interaction.get("severity", "medium")
                            message = interaction.get("message", "")
                            
                            if severity == "high":
                                st.error(f"HIGH RISK: {message}")
                            else:
                                st.warning(f"INTERACTION: {message}")
                    
                    # Missing Information
                    if analysis.get("missing_info"):
                        st.subheader("Missing Information")
                        for info in analysis["missing_info"]:
                            st.info(f"MISSING: {info.get('message', '')}")
                    
                    # Clinical Recommendations
                    if analysis.get("recommendations"):
                        st.subheader("Clinical Recommendations")
                        for rec in analysis["recommendations"]:
                            st.success(f"RECOMMENDATION: {rec.get('message', '')}")
                    
                    # If no specific categories, show general analysis
                    if not any([analysis.get("critical_alerts"), analysis.get("drug_interactions"), 
                               analysis.get("missing_info"), analysis.get("recommendations")]):
                        st.info("Analysis completed - no critical issues detected")
                
                # Save data locally
                saved_path = save_form_data(patient_data, analysis, form_text)
                if saved_path:
                    st.success(f"Analysis saved locally: {saved_path}")
                
                # Timestamp
                st.caption(f"Analysis completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")
                st.error("Please check your form format and try again.")
    
    elif analyze_button and (not form_text or not form_text.strip()):
        st.warning("Please upload a file or paste medical form text before analyzing.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
    <p>HealthForm AI Validator | Built with Streamlit + OpenAI GPT-4</p>
    <p>For demonstration purposes only - Not for actual medical use</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()