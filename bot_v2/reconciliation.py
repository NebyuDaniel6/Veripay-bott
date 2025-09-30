import re
import logging
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ReconciliationResult:
    """Result of reconciliation between bank statement and waiter transactions"""
    matched_refs: Set[str]
    missing_from_bank: Set[str]
    extra_in_bank: Set[str]
    total_difference: float
    matched_count: int
    missing_count: int
    extra_count: int

class BankStatementParser:
    """Parses bank statement PDFs to extract transaction references"""
    
    def __init__(self):
        # Common patterns for transaction references in Ethiopian banks
        self.ref_patterns = [
            r'Ref[:\s]*(\d{6,12})',  # Ref: 123456789
            r'Reference[:\s]*(\d{6,12})',  # Reference: 123456789
            r'TXN[:\s]*(\d{6,12})',  # TXN: 123456789
            r'Transaction[:\s]*(\d{6,12})',  # Transaction: 123456789
            r'(\d{6,12})',  # Just numbers (6-12 digits)
        ]
    
    def extract_references(self, pdf_text: str) -> Set[str]:
        """Extract all transaction reference numbers from PDF text"""
        references = set()
        
        for pattern in self.ref_patterns:
            matches = re.findall(pattern, pdf_text, re.IGNORECASE)
            for match in matches:
                if len(match) >= 6:  # Minimum 6 digits for a valid ref
                    references.add(match)
        
        logger.info(f"Extracted {len(references)} references from PDF: {list(references)}")
        return references

class TransactionReconciler:
    """Reconciles waiter transactions with bank statement references"""
    
    def __init__(self):
        self.parser = BankStatementParser()
    
    def reconcile(self, bank_refs: Set[str], waiter_refs: Set[str]) -> ReconciliationResult:
        """Compare bank statement references with waiter transaction references"""
        
        # Find matches
        matched_refs = bank_refs.intersection(waiter_refs)
        
        # Find missing (in waiter but not in bank)
        missing_from_bank = waiter_refs - bank_refs
        
        # Find extra (in bank but not in waiter)
        extra_in_bank = bank_refs - waiter_refs
        
        # Calculate total difference (simplified - just count)
        total_difference = len(missing_from_bank) - len(extra_in_bank)
        
        return ReconciliationResult(
            matched_refs=matched_refs,
            missing_from_bank=missing_from_bank,
            extra_in_bank=extra_in_bank,
            total_difference=total_difference,
            matched_count=len(matched_refs),
            missing_count=len(missing_from_bank),
            extra_count=len(extra_in_bank)
        )
    
    def format_result(self, result: ReconciliationResult) -> str:
        """Format reconciliation result for display"""
        output = []
        output.append("📊 **Reconciliation Results**\n")
        
        output.append(f"✅ **Matched Transactions:** {result.matched_count}")
        
        if result.missing_count > 0:
            missing_list = ", ".join(list(result.missing_from_bank)[:5])
            if len(result.missing_from_bank) > 5:
                missing_list += f" (+{len(result.missing_from_bank) - 5} more)"
            output.append(f"❌ **Missing from Bank:** {result.missing_count} (Refs: {missing_list})")
        
        if result.extra_count > 0:
            extra_list = ", ".join(list(result.extra_in_bank)[:5])
            if len(result.extra_in_bank) > 5:
                extra_list += f" (+{len(result.extra_in_bank) - 5} more)"
            output.append(f"⚠️ **Extra in Bank:** {result.extra_count} (Refs: {extra_list})")
        
        if result.total_difference != 0:
            if result.total_difference > 0:
                output.append(f"**Total Difference:** {result.total_difference} transactions missing")
            else:
                output.append(f"**Total Difference:** {abs(result.total_difference)} extra transactions")
        else:
            output.append("**Total Difference:** Perfect match! 🎉")
        
        return "\n".join(output)

# Global instance for easy access
reconciler = TransactionReconciler()
