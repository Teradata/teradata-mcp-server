"""
Test result data structures for the testing framework.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running" 
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class TestPhaseResult:
    """Result of a single test phase."""
    phase_name: str
    phase_number: int
    status: TestStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    output: str = ""
    error_message: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)

    def finish(self, status: TestStatus, output: str = "", error_message: Optional[str] = None):
        """Mark phase as complete."""
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.status = status
        self.output = output
        if error_message:
            self.error_message = error_message


@dataclass 
class TestResult:
    """Complete test execution result."""
    test_name: str
    module_name: str
    status: TestStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    phases: List[TestPhaseResult] = field(default_factory=list)
    overall_output: str = ""
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_phase(self, phase: TestPhaseResult):
        """Add a phase result."""
        self.phases.append(phase)

    def finish(self, status: TestStatus, output: str = "", error_message: Optional[str] = None):
        """Mark test as complete."""
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.status = status
        self.overall_output = output
        if error_message:
            self.error_message = error_message

    @property
    def passed_phases(self) -> int:
        """Number of phases that passed."""
        return sum(1 for phase in self.phases if phase.status == TestStatus.PASSED)

    @property
    def failed_phases(self) -> int:
        """Number of phases that failed."""
        return sum(1 for phase in self.phases if phase.status == TestStatus.FAILED)

    @property
    def total_phases(self) -> int:
        """Total number of phases."""
        return len(self.phases)

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        if self.total_phases == 0:
            return 0.0
        return (self.passed_phases / self.total_phases) * 100