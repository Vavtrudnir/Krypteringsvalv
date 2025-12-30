"""
Password strength validator for Hemliga valvet.
"""

import re
from typing import Tuple, List


class PasswordStrength:
    """Password strength validation and scoring."""
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, List[str]]:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Length check
        if len(password) < 12:
            issues.append("Minst 12 tecken")
        
        # Uppercase check
        if not re.search(r'[A-ZÅÄÖ]', password):
            issues.append("Minst 1 stor bokstav (Å-Ö)")
        
        # Lowercase check
        if not re.search(r'[a-zåäö]', password):
            issues.append("Minst 1 liten bokstav (å-ö)")
        
        # Number check
        if not re.search(r'\d', password):
            issues.append("Minst 1 siffra")
        
        # Special character check
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\/?]', password):
            issues.append("Minst 1 specialtecken (!@#$%...)")
        
        # Common patterns check
        common_patterns = [
            r'123', r'abc', r'qwerty', r'password', r'lösenord',
            r'admin', r'user', r'test'
        ]
        
        for pattern in common_patterns:
            if re.search(pattern, password, re.IGNORECASE):
                issues.append(f"Undvik vanliga mönster ({pattern})")
                break
        
        # Repeated characters check
        if re.search(r'(.)\1{2,}', password):
            issues.append("Undvik upprepade tecken (aaa, 111)")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    @staticmethod
    def get_strength_score(password: str) -> int:
        """
        Get password strength score (0-100).
        
        Args:
            password: Password to score
            
        Returns:
            Strength score 0-100
        """
        score = 0
        
        # Length scoring
        score += min(len(password) * 2, 30)
        
        # Character variety scoring
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\/?]', password):
            score += 15
        
        # Complexity bonus
        unique_chars = len(set(password))
        score += min(unique_chars * 2, 25)
        
        return min(score, 100)
    
    @staticmethod
    def get_strength_text(score: int) -> str:
        """Get strength description from score."""
        if score < 30:
            return "Svag"
        elif score < 50:
            return "Måttlig"
        elif score < 70:
            return "Bra"
        elif score < 90:
            return "Stark"
        else:
            return "Mycket stark"
