"""
SahAI Tools - Agentic Tool System
Implements tools for eligibility checking, scheme retrieval, and mock APIs
Each tool has explicit input/output schemas and can be called by the agent
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
import re
import json


class ToolStatus(Enum):
    """Status of tool execution"""
    SUCCESS = "success"
    PARTIAL = "partial"  # Some info missing but can continue
    NEEDS_INFO = "needs_info"  # Cannot proceed without more info
    ERROR = "error"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class ToolResult:
    """Standardized result from any tool"""
    tool_name: str
    status: ToolStatus
    data: Any = None
    message: str = ""
    message_hi: str = ""  # Hindi message
    missing_fields: List[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolSchema:
    """Schema definition for a tool"""
    name: str
    description: str
    description_hi: str
    required_inputs: List[str]
    optional_inputs: List[str]
    output_type: str
    examples: List[Dict[str, Any]] = field(default_factory=list)


class BaseTool(ABC):
    """Base class for all tools"""
    
    @property
    @abstractmethod
    def schema(self) -> ToolSchema:
        """Return the tool's schema"""
        pass
    
    @abstractmethod
    def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """Execute the tool with given inputs"""
        pass
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate that required inputs are present"""
        missing = []
        for field in self.schema.required_inputs:
            if field not in inputs or inputs[field] is None:
                missing.append(field)
        return len(missing) == 0, missing


class EligibilityEngineTool(BaseTool):
    """
    Tool 1: Eligibility Engine
    Checks if a user is eligible for specific schemes based on their data
    """
    
    def __init__(self, scheme_db):
        self.scheme_db = scheme_db
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="eligibility_engine",
            description="Check user eligibility for government schemes based on their personal data",
            description_hi="व्यक्तिगत जानकारी के आधार पर सरकारी योजनाओं के लिए पात्रता जांचें",
            required_inputs=[],  # Can work with partial info
            optional_inputs=["age", "income", "gender", "category", "state", "occupation", "disability", "bpl", "area"],
            output_type="eligibility_results"
        )
    
    def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """Check eligibility for all schemes based on available user data"""
        
        # Check what info we have
        age = inputs.get("age")
        income = inputs.get("income")
        gender = inputs.get("gender")
        category = inputs.get("category")
        bpl = inputs.get("bpl")
        area = inputs.get("area")
        occupation = inputs.get("occupation")
        disability = inputs.get("disability")
        
        # Track what we need for accurate results
        missing_for_accuracy = []
        if age is None:
            missing_for_accuracy.append("age")
        if income is None:
            missing_for_accuracy.append("income")
        
        # Check each scheme
        eligible_schemes = []
        partially_eligible = []
        not_eligible = []
        
        for scheme in self.scheme_db.schemes:
            result = self._check_scheme_eligibility(scheme, inputs)
            if result["status"] == "eligible":
                eligible_schemes.append(result)
            elif result["status"] == "partial":
                partially_eligible.append(result)
            else:
                not_eligible.append(result)
        
        # Determine overall status
        if not inputs or all(v is None for v in inputs.values()):
            return ToolResult(
                tool_name="eligibility_engine",
                status=ToolStatus.NEEDS_INFO,
                data={"all_schemes": [s.id for s in self.scheme_db.schemes]},
                message="Need user information to check eligibility",
                message_hi="पात्रता जांचने के लिए आपकी जानकारी चाहिए",
                missing_fields=["age", "income"],
                confidence=0.3
            )
        
        return ToolResult(
            tool_name="eligibility_engine",
            status=ToolStatus.SUCCESS if eligible_schemes else ToolStatus.PARTIAL,
            data={
                "eligible": eligible_schemes,
                "partial": partially_eligible,
                "not_eligible": not_eligible,
                "user_data_used": {k: v for k, v in inputs.items() if v is not None}
            },
            message=f"Found {len(eligible_schemes)} eligible schemes",
            message_hi=f"{len(eligible_schemes)} योजनाओं के लिए पात्र",
            missing_fields=missing_for_accuracy,
            confidence=1.0 if not missing_for_accuracy else 0.7
        )
    
    def _check_scheme_eligibility(self, scheme, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check eligibility for a single scheme"""
        rules = scheme.eligibility
        issues = []
        met_criteria = []
        unknown_criteria = []
        
        # Age check
        if "age_min" in rules or "min_age" in rules:
            min_age = rules.get("age_min") or rules.get("min_age")
            if user_data.get("age") is not None:
                if user_data["age"] >= min_age:
                    met_criteria.append(f"उम्र {min_age}+ ✓")
                else:
                    issues.append(f"न्यूनतम उम्र {min_age} वर्ष चाहिए")
            else:
                unknown_criteria.append("age")
        
        if "age_max" in rules or "max_age" in rules:
            max_age = rules.get("age_max") or rules.get("max_age")
            if user_data.get("age") is not None:
                if user_data["age"] <= max_age:
                    met_criteria.append(f"उम्र {max_age} से कम ✓")
                else:
                    issues.append(f"अधिकतम उम्र {max_age} वर्ष होनी चाहिए")
            else:
                unknown_criteria.append("age")
        
        # Income check
        if "income_max" in rules or "max_income" in rules:
            max_income = rules.get("income_max") or rules.get("max_income")
            if user_data.get("income") is not None:
                if user_data["income"] <= max_income:
                    met_criteria.append(f"आय ₹{max_income} से कम ✓")
                else:
                    issues.append(f"आय ₹{max_income} से कम होनी चाहिए")
            else:
                unknown_criteria.append("income")
        
        # Gender check
        if "gender" in rules:
            if user_data.get("gender") is not None:
                if user_data["gender"].lower() == rules["gender"].lower():
                    met_criteria.append(f"{rules['gender']} ✓")
                else:
                    issues.append(f"केवल {rules['gender']} के लिए")
            else:
                unknown_criteria.append("gender")
        
        # Category check
        if "categories" in rules:
            if user_data.get("category") is not None:
                if user_data["category"] in rules["categories"]:
                    met_criteria.append(f"श्रेणी {user_data['category']} ✓")
                else:
                    issues.append(f"श्रेणी {', '.join(rules['categories'])} में होनी चाहिए")
            else:
                unknown_criteria.append("category")
        
        # BPL check
        if rules.get("bpl") is True:
            if user_data.get("bpl") is not None:
                if user_data["bpl"]:
                    met_criteria.append("BPL ✓")
                else:
                    issues.append("BPL कार्ड आवश्यक")
            else:
                unknown_criteria.append("bpl")
        
        # Determine status
        if issues:
            status = "not_eligible"
        elif unknown_criteria and not met_criteria:
            status = "partial"
        elif unknown_criteria:
            status = "partial"
        else:
            status = "eligible"
        
        return {
            "scheme_id": scheme.id,
            "scheme_name_hi": scheme.get_name("hi"),
            "scheme_name_en": scheme.get_name("en"),
            "status": status,
            "met_criteria": met_criteria,
            "issues": issues,
            "unknown_criteria": unknown_criteria,
            "benefit": scheme.get_benefit("hi")
        }


class SchemeRetrievalTool(BaseTool):
    """
    Tool 2: Scheme Retrieval System
    Retrieves detailed information about specific schemes
    """
    
    def __init__(self, scheme_db):
        self.scheme_db = scheme_db
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="scheme_retrieval",
            description="Retrieve detailed information about government schemes",
            description_hi="सरकारी योजनाओं की विस्तृत जानकारी प्राप्त करें",
            required_inputs=[],
            optional_inputs=["scheme_id", "query", "category"],
            output_type="scheme_info"
        )
    
    def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """Retrieve scheme information"""
        
        scheme_id = inputs.get("scheme_id")
        query = inputs.get("query", "")
        category = inputs.get("category")
        
        # Direct lookup by ID
        if scheme_id:
            scheme = self.scheme_db.get_scheme_by_id(scheme_id)
            if scheme:
                return ToolResult(
                    tool_name="scheme_retrieval",
                    status=ToolStatus.SUCCESS,
                    data=self._format_scheme_details(scheme),
                    message=f"Found scheme: {scheme.get_name('en')}",
                    message_hi=f"योजना मिली: {scheme.get_name('hi')}",
                    confidence=1.0
                )
        
        # Search by query
        if query:
            results = self.scheme_db.search_schemes(query)
            if results:
                return ToolResult(
                    tool_name="scheme_retrieval",
                    status=ToolStatus.SUCCESS,
                    data={
                        "schemes": [self._format_scheme_brief(s) for s in results[:5]],
                        "total_found": len(results)
                    },
                    message=f"Found {len(results)} matching schemes",
                    message_hi=f"{len(results)} मिलती-जुलती योजनाएं मिलीं",
                    confidence=0.9
                )
        
        # Search by category
        if category:
            results = self.scheme_db.get_schemes_by_category(category)
            if results:
                return ToolResult(
                    tool_name="scheme_retrieval",
                    status=ToolStatus.SUCCESS,
                    data={
                        "schemes": [self._format_scheme_brief(s) for s in results],
                        "category": category
                    },
                    message=f"Found {len(results)} schemes in {category}",
                    message_hi=f"{category} श्रेणी में {len(results)} योजनाएं मिलीं",
                    confidence=0.95
                )
        
        # Return all schemes if no specific query
        return ToolResult(
            tool_name="scheme_retrieval",
            status=ToolStatus.SUCCESS,
            data={
                "schemes": [self._format_scheme_brief(s) for s in self.scheme_db.schemes],
                "total": len(self.scheme_db.schemes)
            },
            message=f"Listing all {len(self.scheme_db.schemes)} schemes",
            message_hi=f"सभी {len(self.scheme_db.schemes)} योजनाएं",
            confidence=1.0
        )
    
    def _format_scheme_details(self, scheme) -> Dict[str, Any]:
        """Format full scheme details"""
        return {
            "id": scheme.id,
            "name_hi": scheme.get_name("hi"),
            "name_en": scheme.get_name("en"),
            "category": scheme.category,
            "description_hi": scheme.get_description("hi"),
            "benefit_hi": scheme.get_benefit("hi"),
            "eligibility": scheme.eligibility,
            "documents": scheme.documents,
            "helpline": scheme.helpline,
            "application_url": scheme.application_url
        }
    
    def _format_scheme_brief(self, scheme) -> Dict[str, Any]:
        """Format brief scheme info"""
        return {
            "id": scheme.id,
            "name_hi": scheme.get_name("hi"),
            "category": scheme.category,
            "benefit_hi": scheme.get_benefit("hi")
        }


class ApplicationStatusTool(BaseTool):
    """
    Tool 3: Mock Application Status API
    Simulates checking application status (mock API)
    """
    
    def __init__(self):
        # Mock database of applications
        self._mock_applications = {
            "PM123456": {
                "scheme": "pm-kisan",
                "status": "approved",
                "status_hi": "स्वीकृत",
                "amount": 2000,
                "next_installment": "जनवरी 2025",
                "message_hi": "आपका आवेदन स्वीकृत है। अगली किस्त जनवरी 2025 में आएगी।"
            },
            "AW789012": {
                "scheme": "pm-awas-gramin",
                "status": "pending",
                "status_hi": "प्रक्रियाधीन",
                "stage": "document_verification",
                "message_hi": "आपके दस्तावेज़ सत्यापन में हैं। कृपया 15 दिन प्रतीक्षा करें।"
            }
        }
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="application_status",
            description="Check status of a scheme application (Mock API)",
            description_hi="योजना आवेदन की स्थिति जांचें",
            required_inputs=["application_id"],
            optional_inputs=["scheme_id", "aadhaar_last4"],
            output_type="application_status"
        )
    
    def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """Check application status"""
        
        app_id = inputs.get("application_id", "").upper()
        
        if not app_id:
            return ToolResult(
                tool_name="application_status",
                status=ToolStatus.NEEDS_INFO,
                message="Application ID required",
                message_hi="आवेदन संख्या बताएं",
                missing_fields=["application_id"],
                confidence=0.0
            )
        
        # Check mock database
        if app_id in self._mock_applications:
            app_data = self._mock_applications[app_id]
            return ToolResult(
                tool_name="application_status",
                status=ToolStatus.SUCCESS,
                data=app_data,
                message=f"Application {app_id} found",
                message_hi=f"आवेदन {app_id} मिला - {app_data['status_hi']}",
                confidence=1.0
            )
        
        # Application not found - simulate API response
        return ToolResult(
            tool_name="application_status",
            status=ToolStatus.PARTIAL,
            data={"application_id": app_id, "found": False},
            message="Application not found in system",
            message_hi=f"आवेदन संख्या {app_id} नहीं मिली। कृपया सही नंबर दें।",
            confidence=0.8
        )


class DocumentCheckerTool(BaseTool):
    """
    Tool 4: Document Requirement Checker
    Checks what documents are needed for a scheme
    """
    
    def __init__(self, scheme_db):
        self.scheme_db = scheme_db
        self._document_info = {
            "Aadhaar Card": "आधार कार्ड - UIDAI द्वारा जारी 12 अंकों का विशिष्ट पहचान संख्या",
            "Income Certificate": "आय प्रमाण पत्र - तहसील कार्यालय से प्राप्त करें",
            "BPL Certificate": "बीपीएल प्रमाण पत्र - ग्राम पंचायत/नगर पालिका से",
            "Age Proof": "आयु प्रमाण - जन्म प्रमाण पत्र, मतदाता पहचान पत्र, या स्कूल प्रमाण पत्र",
            "Bank Account": "बैंक खाता - आधार से लिंक होना चाहिए",
            "Land Records": "भूमि रिकॉर्ड - खतौनी/खसरा",
            "Disability Certificate": "विकलांगता प्रमाण पत्र - जिला अस्पताल से",
            "Death Certificate of Husband": "पति का मृत्यु प्रमाण पत्र - नगर पालिका/ग्राम पंचायत से"
        }
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="document_checker",
            description="Check required documents for scheme application",
            description_hi="योजना आवेदन के लिए आवश्यक दस्तावेज़ जांचें",
            required_inputs=["scheme_id"],
            optional_inputs=["available_documents"],
            output_type="document_list"
        )
    
    def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """Check document requirements"""
        
        scheme_id = inputs.get("scheme_id")
        available_docs = inputs.get("available_documents", [])
        
        if not scheme_id:
            return ToolResult(
                tool_name="document_checker",
                status=ToolStatus.NEEDS_INFO,
                message="Scheme ID required",
                message_hi="कौन सी योजना के लिए दस्तावेज़ चाहिए?",
                missing_fields=["scheme_id"],
                confidence=0.0
            )
        
        scheme = self.scheme_db.get_scheme_by_id(scheme_id)
        if not scheme:
            return ToolResult(
                tool_name="document_checker",
                status=ToolStatus.ERROR,
                message=f"Scheme {scheme_id} not found",
                message_hi=f"योजना {scheme_id} नहीं मिली",
                confidence=0.0
            )
        
        # Format document requirements
        required_docs = []
        for doc in scheme.documents:
            doc_info = {
                "name": doc,
                "description_hi": self._document_info.get(doc, ""),
                "available": doc in available_docs
            }
            required_docs.append(doc_info)
        
        missing = [d for d in required_docs if not d["available"]]
        
        return ToolResult(
            tool_name="document_checker",
            status=ToolStatus.SUCCESS,
            data={
                "scheme_name_hi": scheme.get_name("hi"),
                "required_documents": required_docs,
                "missing_count": len(missing),
                "total_required": len(required_docs)
            },
            message=f"{len(required_docs)} documents required, {len(missing)} missing",
            message_hi=f"{len(required_docs)} दस्तावेज़ चाहिए",
            confidence=1.0
        )


class UserDataExtractorTool(BaseTool):
    """
    Tool 5: User Data Extractor
    Extracts structured data from user's natural language input
    """
    
    def __init__(self):
        pass
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="user_data_extractor",
            description="Extract user information from Hindi/English text",
            description_hi="उपयोगकर्ता की जानकारी निकालें",
            required_inputs=["text"],
            optional_inputs=[],
            output_type="extracted_data"
        )
    
    def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """Extract user data from text"""
        
        text = inputs.get("text", "").lower()
        extracted = {}
        
        # Age extraction
        age_patterns = [
            (r'(\d+)\s*(?:साल|वर्ष|years?|yrs?)', 1),
            (r'उम्र\s*(?:है)?\s*(\d+)', 1),
            (r'मेरी\s*उम्र\s*(\d+)', 1),
            (r'age\s*(?:is)?\s*(\d+)', 1),
        ]
        for pattern, group in age_patterns:
            match = re.search(pattern, text)
            if match:
                age = int(match.group(group))
                if 1 <= age <= 120:
                    extracted["age"] = age
                break
        
        # Income extraction
        income_patterns = [
            (r'(\d+)\s*(?:लाख|lakh)', "lakh"),
            (r'(\d+)\s*(?:हज़ार|हजार|thousand|k\b)', "thousand"),
            (r'आय\s*(?:है)?\s*(\d+)', "raw"),
            (r'income\s*(?:is)?\s*(?:rs\.?|₹)?\s*(\d+)', "raw"),
        ]
        for pattern, multiplier in income_patterns:
            match = re.search(pattern, text)
            if match:
                amount = int(match.group(1))
                if multiplier == "lakh":
                    extracted["income"] = amount * 100000
                elif multiplier == "thousand":
                    extracted["income"] = amount * 1000
                else:
                    # Assume lakhs if > 100, else raw value
                    if amount > 100:
                        extracted["income"] = amount
                    else:
                        extracted["income"] = amount * 100000
                break
        
        # Gender extraction
        female_words = ['महिला', 'female', 'woman', 'औरत', 'लड़की', 'स्त्री', 'विधवा', 'widow']
        male_words = ['पुरुष', 'male', 'man', 'आदमी', 'लड़का']
        
        if any(word in text for word in female_words):
            extracted["gender"] = "female"
        elif any(word in text for word in male_words):
            extracted["gender"] = "male"
        
        # Category extraction
        category_map = {
            'sc': ['एससी', 'sc', 'अनुसूचित जाति', 'scheduled caste'],
            'st': ['एसटी', 'st', 'अनुसूचित जनजाति', 'scheduled tribe'],
            'obc': ['ओबीसी', 'obc', 'अन्य पिछड़ा वर्ग', 'other backward'],
            'general': ['सामान्य', 'general', 'जनरल']
        }
        for cat, keywords in category_map.items():
            if any(kw in text for kw in keywords):
                extracted["category"] = cat.upper()
                break
        
        # BPL extraction
        if any(word in text for word in ['बीपीएल', 'bpl', 'गरीबी रेखा', 'below poverty']):
            extracted["bpl"] = True
        
        # Area extraction
        if any(word in text for word in ['गांव', 'ग्रामीण', 'village', 'rural']):
            extracted["area"] = "rural"
        elif any(word in text for word in ['शहर', 'शहरी', 'city', 'urban']):
            extracted["area"] = "urban"
        
        # Occupation
        if any(word in text for word in ['किसान', 'farmer', 'खेती', 'कृषि']):
            extracted["occupation"] = "farmer"
        
        # Disability
        if any(word in text for word in ['विकलांग', 'दिव्यांग', 'disabled', 'handicap']):
            extracted["disability"] = True
        
        if extracted:
            return ToolResult(
                tool_name="user_data_extractor",
                status=ToolStatus.SUCCESS,
                data=extracted,
                message=f"Extracted {len(extracted)} fields",
                message_hi=f"{len(extracted)} जानकारी मिली",
                confidence=0.85
            )
        
        return ToolResult(
            tool_name="user_data_extractor",
            status=ToolStatus.PARTIAL,
            data={},
            message="No structured data found in text",
            message_hi="कोई जानकारी नहीं मिली",
            confidence=0.5
        )


class ToolRegistry:
    """Registry of all available tools"""
    
    def __init__(self, scheme_db=None):
        self.tools: Dict[str, BaseTool] = {}
        self._init_tools(scheme_db)
    
    def _init_tools(self, scheme_db):
        """Initialize all tools"""
        if scheme_db:
            self.register("eligibility_engine", EligibilityEngineTool(scheme_db))
            self.register("scheme_retrieval", SchemeRetrievalTool(scheme_db))
            self.register("document_checker", DocumentCheckerTool(scheme_db))
        
        self.register("application_status", ApplicationStatusTool())
        self.register("user_data_extractor", UserDataExtractorTool())
    
    def register(self, name: str, tool: BaseTool):
        """Register a tool"""
        self.tools[name] = tool
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def execute(self, name: str, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """Execute a tool by name"""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                tool_name=name,
                status=ToolStatus.ERROR,
                message=f"Tool '{name}' not found",
                message_hi=f"टूल '{name}' नहीं मिला",
                confidence=0.0
            )
        return tool.execute(inputs, context)
    
    def list_tools(self) -> List[Dict[str, str]]:
        """List all available tools"""
        return [
            {
                "name": name,
                "description": tool.schema.description,
                "description_hi": tool.schema.description_hi
            }
            for name, tool in self.tools.items()
        ]
    
    def get_tool_schemas_for_llm(self) -> str:
        """Get tool schemas formatted for LLM context"""
        schemas = []
        for name, tool in self.tools.items():
            s = tool.schema
            schemas.append(f"""
Tool: {s.name}
Description: {s.description}
Required Inputs: {', '.join(s.required_inputs) if s.required_inputs else 'None'}
Optional Inputs: {', '.join(s.optional_inputs)}
""")
        return "\n".join(schemas)
