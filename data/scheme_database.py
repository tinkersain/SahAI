"""
SahAI Scheme Database - Government Scheme Data Management
Loads and searches government welfare schemes
"""
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class Scheme:
    """Government scheme data structure"""
    id: str
    name: Dict[str, str]
    category: str
    description: Dict[str, str]
    benefit: Dict[str, str]
    eligibility: Dict[str, Any]
    documents: List[str]
    application_url: str
    helpline: str
    tags: List[str]
    
    def get_name(self, lang: str = "hi") -> str:
        return self.name.get(lang, self.name.get("en", self.id))
    
    def get_description(self, lang: str = "hi") -> str:
        return self.description.get(lang, self.description.get("en", ""))
    
    def get_benefit(self, lang: str = "hi") -> str:
        return self.benefit.get(lang, self.benefit.get("en", ""))


class SchemeDatabase:
    """
    Database of government welfare schemes
    Loads from JSON and provides search functionality
    """
    
    _instance = None
    _data_path = Path(__file__).parent / "schemes.json"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.schemes: List[Scheme] = []
        self._scheme_map: Dict[str, Scheme] = {}
        self._load_data()
        self._initialized = True
    
    def _load_data(self):
        """Load schemes from JSON file"""
        try:
            with open(self._data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for scheme_data in data.get("schemes", []):
                scheme = Scheme(
                    id=scheme_data["id"],
                    name=scheme_data["name"],
                    category=scheme_data["category"],
                    description=scheme_data["description"],
                    benefit=scheme_data["benefit"],
                    eligibility=scheme_data.get("eligibility", {}),
                    documents=scheme_data.get("documents", []),
                    application_url=scheme_data.get("application_url", ""),
                    helpline=scheme_data.get("helpline", ""),
                    tags=scheme_data.get("tags", [])
                )
                self.schemes.append(scheme)
                self._scheme_map[scheme.id] = scheme
            
            print(f"📋 Loaded {len(self.schemes)} government schemes")
            
        except FileNotFoundError:
            print(f"⚠️ Scheme database not found at {self._data_path}")
        except json.JSONDecodeError as e:
            print(f"⚠️ Invalid JSON in scheme database: {e}")
    
    def get_scheme_by_id(self, scheme_id: str) -> Optional[Scheme]:
        """Get scheme by ID"""
        return self._scheme_map.get(scheme_id)
    
    def search_schemes(self, query: str) -> List[Scheme]:
        """Search schemes by query"""
        query_lower = query.lower()
        results = []
        
        for scheme in self.schemes:
            score = 0
            
            # Check name
            if query_lower in scheme.name.get("hi", "").lower():
                score += 10
            if query_lower in scheme.name.get("en", "").lower():
                score += 10
            
            # Check tags
            for tag in scheme.tags:
                if query_lower in tag.lower():
                    score += 5
            
            # Check category
            if query_lower in scheme.category.lower():
                score += 3
            
            if score > 0:
                results.append((score, scheme))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [scheme for _, scheme in results]
    
    def get_schemes_by_category(self, category: str) -> List[Scheme]:
        """Get schemes by category"""
        return [s for s in self.schemes if s.category.lower() == category.lower()]
    
    def get_eligible_schemes(self, user_data: Dict[str, Any]) -> List[Scheme]:
        """
        Get schemes user might be eligible for based on basic data
        """
        age = user_data.get("age")
        income = user_data.get("income")
        gender = user_data.get("gender")
        category = user_data.get("category")
        
        eligible = []
        
        for scheme in self.schemes:
            rules = scheme.eligibility
            is_potentially_eligible = True
            
            # Quick eligibility check
            if age is not None:
                if "age_min" in rules and age < rules["age_min"]:
                    is_potentially_eligible = False
                if "age_max" in rules and age > rules["age_max"]:
                    is_potentially_eligible = False
            
            if income is not None:
                if "income_max" in rules and income > rules["income_max"]:
                    is_potentially_eligible = False
            
            if gender is not None and "gender" in rules:
                if gender != rules["gender"]:
                    is_potentially_eligible = False
            
            if category is not None and "categories" in rules:
                if category not in rules["categories"]:
                    is_potentially_eligible = False
            
            if is_potentially_eligible:
                eligible.append(scheme)
        
        return eligible
