"""
Volume Ledger Model (Phase 1)

Provides formal volume accounting with invariant checks.
Every yd³ must have exactly one owner; ledger must balance.

INVARIANTS:
1. bulk_residual >= 0 (can't have negative bulk)
2. bulk_residual <= bulk_raw (subtraction can't add mass)
3. subtracted_area <= pile_area (can't subtract more than exists)
4. large_unowned_blobs == 0 (every big blob has an owner)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional


@dataclass
class VolumeLedger:
    """Formal volume accounting with invariant enforcement."""
    
    # Bulk lane
    bulk_raw: float = 0.0           # K × median_pile_ratio (before subtraction)
    bulk_subtracted: float = 0.0    # Sum of subtracted discrete areas × K
    bulk_residual: float = 0.0      # bulk_raw - bulk_subtracted (used in final)
    
    # Discrete lane
    discrete_volume: float = 0.0     # From catalog lookups
    discrete_items: List[str] = field(default_factory=list)
    
    # Countable lane
    countable_volume: float = 0.0    # From qty × vol_per
    countable_classes: Dict[str, int] = field(default_factory=dict)
    countable_subtracted: float = 0.0  # Area subtracted for countables (Gap 2)
    
    # Bulky priors lane
    bulky_prior_volume: float = 0.0  # From safety net
    bulky_priors_applied: Set[str] = field(default_factory=set)
    
    # Uncertain blob lane (Gap 4: Policy A fallback)
    uncertain_blob_volume: float = 0.0  # Area→Volume fallback for unowned blobs
    uncertain_blob_count: int = 0
    
    # Final
    final_volume: float = 0.0
    
    # Area accounting (for invariant checks)
    pile_area: float = 0.0           # Total pile mask area (%)
    subtracted_area: float = 0.0     # Total area subtracted (%)
    remainder_area: float = 0.0      # pile_area - subtracted_area
    bulk_residual_pct: float = 0.0   # P5: Single source of truth for final residual
    
    # Ownership tracking
    ownership_map: Dict[str, List[dict]] = field(default_factory=dict)
    unowned_blobs: List[dict] = field(default_factory=list)
    overlap_risk_volume: float = 0.0  # Change C: Items with volume but too small to subtract
    
    # Invariant results
    violations: List[str] = field(default_factory=list)
    
    def check_invariants(self, tolerance: float = 0.01) -> bool:
        """
        Check all invariants and record violations.
        
        Phase 1 Invariants:
        - I1: bulk_residual >= 0
        - I2: bulk_residual <= bulk_raw (monotonicity)
        - I3: subtracted_area <= pile_area
        - I4: large_unowned_blobs == 0
        
        Phase 6 Invariants:
        - I5: lane_exclusivity (volume sources don't overlap)
        - I6: owner_completeness (subtracted + remainder ≈ pile)
        
        Returns True if all pass, False otherwise.
        """
        self.violations = []
        
        # Invariant 1: bulk_residual >= 0
        if self.bulk_residual < -tolerance:
            self.violations.append(
                f"I1: bulk_residual ({self.bulk_residual:.2f}) < 0"
            )
        
        # Invariant 2: bulk_residual <= bulk_raw (monotonicity)
        if self.bulk_residual > self.bulk_raw + tolerance:
            self.violations.append(
                f"I2: bulk_residual ({self.bulk_residual:.2f}) > bulk_raw ({self.bulk_raw:.2f})"
            )
        
        # Invariant 3: subtracted_area <= pile_area
        if self.subtracted_area > self.pile_area + tolerance:
            self.violations.append(
                f"I3: subtracted_area ({self.subtracted_area:.2%}) > pile_area ({self.pile_area:.2%})"
            )
        
        # Invariant 4: no large unowned blobs (>5% of pile)
        large_unowned = [b for b in self.unowned_blobs if b.get("area", 0) > 0.05]
        if large_unowned:
            labels = [b.get("label", "?") for b in large_unowned]
            self.violations.append(
                f"I4: {len(large_unowned)} large unowned blobs: {labels}"
            )
        
        # Invariant 5: lane exclusivity (final should equal sum of lanes)
        # Include all volume sources in ledger
        expected_sum = (
            self.bulk_residual + 
            self.discrete_volume + 
            self.countable_volume + 
            self.bulky_prior_volume + 
            self.uncertain_blob_volume  # Gap 4: Policy A fallback
        )
        # Allow for countable capping (final may be less than expected)
        if self.final_volume > expected_sum + tolerance:
            self.violations.append(
                f"I5: final ({self.final_volume:.2f}) > lane_sum ({expected_sum:.2f})"
            )
        
        # Invariant 6: owner completeness (area accounting)
        # subtracted + remainder should approximately equal pile
        if self.pile_area > 0:
            accounted_area = self.subtracted_area + self.remainder_area
            coverage = accounted_area / self.pile_area
            if coverage < 0.8:  # >20% leakage
                self.violations.append(
                    f"I6: area coverage ({coverage:.1%}) < 80% - possible leakage"
                )
        
        return len(self.violations) == 0
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for API response."""
        return {
            "bulk_raw": round(self.bulk_raw, 2),
            "bulk_subtracted": round(self.bulk_subtracted, 2),
            "bulk_residual": round(self.bulk_residual, 2),
            "bulk_residual_pct": round(self.bulk_residual_pct, 4),  # P5: Single source
            "discrete_volume": round(self.discrete_volume, 2),
            "countable_volume": round(self.countable_volume, 2),
            "countable_subtracted": round(self.countable_subtracted, 4),
            "bulky_prior_volume": round(self.bulky_prior_volume, 2),
            "uncertain_blob_volume": round(self.uncertain_blob_volume, 2),
            "uncertain_blob_count": self.uncertain_blob_count,
            "final_volume": round(self.final_volume, 2),
            "pile_area": round(self.pile_area, 4),
            "subtracted_area": round(self.subtracted_area, 4),
            "remainder_area": round(self.remainder_area, 4),
            "invariants_passed": len(self.violations) == 0,
            "violations": self.violations,
            "unowned_blob_count": len(self.unowned_blobs)
        }
    
    def log_summary(self) -> str:
        """Return human-readable summary for logging."""
        lines = [
            f"📊 Volume Ledger:",
            f"   Bulk: raw={self.bulk_raw:.2f} - sub={self.bulk_subtracted:.2f} = residual={self.bulk_residual:.2f} yd³ ({self.bulk_residual_pct:.1%})",
            f"   Discrete: {self.discrete_volume:.2f} yd³ ({len(self.discrete_items)} items)",
            f"   Countable: {self.countable_volume:.2f} yd³ ({dict(self.countable_classes)})",
            f"   Bulky Prior: {self.bulky_prior_volume:.2f} yd³ ({self.bulky_priors_applied})",
            f"   Final: {self.final_volume:.2f} yd³",
            f"   Area: pile={self.pile_area:.1%} sub={self.subtracted_area:.1%} rem={self.remainder_area:.1%}",
        ]
        
        if self.violations:
            lines.append(f"   ⚠️ VIOLATIONS: {self.violations}")
        else:
            lines.append(f"   ✅ All invariants passed")
        
        return "\n".join(lines)
