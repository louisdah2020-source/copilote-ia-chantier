"""
ai_agents/base_agent.py
Classe de base pour les agents spécialisés du Copilote IA Chantier.
Fournit le cadre d'analyse et de génération de diagnostics en langage naturel.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from core.models import KPISummary, ValidationReport


class BaseChantierAgent(ABC):
    """Agent expert spécialisé dans un domaine de l'ingénierie de chantier."""

    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    @abstractmethod
    def analyze(self, kpi: KPISummary, validation: Optional[ValidationReport] = None, trends: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Produit un diagnostic structuré et une interprétation en langage naturel."""
        pass
