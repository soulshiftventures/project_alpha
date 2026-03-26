# Project Alpha Phase 5 - Verification Guide

## Overview

This guide provides step-by-step verification procedures for Project Alpha Phase 5, covering all stage workflows, portfolio execution, multi-business management, tool integrations, and fallback behaviors.

---

## Table of Contents

1. [Quick Start Verification](#quick-start-verification)
2. [Stage-Specific Workflow Verification](#stage-specific-workflow-verification)
3. [Portfolio Execution Verification](#portfolio-execution-verification)
4. [Multi-Business Management Verification](#multi-business-management-verification)
5. [Tool Integrations Verification](#tool-integrations-verification)
6. [Fallback Behaviors Verification](#fallback-behaviors-verification)
7. [Performance Verification](#performance-verification)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start Verification

### 1. System Health Check

```bash
# Navigate to project directory
cd /Users/krissanders/project_alpha

# Run basic health check
python3 -c "
from project_alpha.core.workflow_orchestrator import WorkflowOrchestrator
from project_alpha.core.stage_workflows import StageWorkflows
from project_alpha.core.portfolio_manager import PortfolioManager

orchestrator = WorkflowOrchestrator()
print('✓ Workflow Orchestrator initialized')

workflows = StageWorkflows()
print('✓ Stage Workflows initialized')

portfolio = PortfolioManager()
print('✓ Portfolio Manager initialized')

print('\nTool Status:')
status = orchestrator.get_tool_status()
for tool, info in status.items():
    symbol = '✓' if info['initialized'] else '✗'
    print(f'{symbol} {tool}: Available={info[\"available\"]}, Initialized={info[\"initialized\"]}')
"
```

**Expected Output:**
```
✓ Workflow Orchestrator initialized
✓ Stage Workflows initialized
✓ Portfolio Manager initialized

Tool Status:
✗ ai_q: Available=False, Initialized=False
✗ nemoclaw: Available=False, Initialized=False
✗ zep: Available=False, Initialized=False
✓ simulator: Available=True, Initialized=True
```

### 2. Run Full System Test

```bash
# Run the complete test suite
python3 -m pytest tests/test_workflows.py -v --tb=short

# Run with coverage
python3 -m pytest tests/test_workflows.py --cov=project_alpha/core --cov-report=term-missing
```

**Expected Output:**
```
tests/test_workflows.py::TestStageWorkflows::test_discovered_stage PASSED
tests/test_workflows.py::TestStageWorkflows::test_validating_stage PASSED
...
===================== X passed in Y.YYs ======================
```

---

## Stage-Specific Workflow Verification

### DISCOVERED Stage (3-4 tasks)

#### Verification Steps:

```bash
python3 << 'EOF'
from project_alpha.core.stage_workflows import StageWorkflows
from project_alpha.core.lifecycle_manager import LifecycleManager

# Create test business
lifecycle = LifecycleManager()
business = lifecycle.create_business({
    "idea": "AI-powered task management system",
    "target_market": "Small businesses",
    "potential": "high"
})

# Generate DISCOVERED tasks
workflows = StageWorkflows()
tasks = workflows.get_discovered_tasks(business)

print(f"Generated {len(tasks)} DISCOVERED tasks:")
for i, task in enumerate(tasks, 1):
    print(f"{i}. {task['title']}")
    print(f"   Priority: {task['priority']}, Agent: {task['assigned_agent']}")

# Execute first task
result = workflows.execute_discovered_task(tasks[0], business)
print(f"\nTask execution result: {result['status']}")
print(f"Market size: {result.get('market_size', 'N/A')}")
EOF
```

**Expected Output:**
```
Generated 4 DISCOVERED tasks:
1. Initial market research for: AI-powered task management system
   Priority: high, Agent: research
2. Competitive landscape analysis: AI-powered task management system
   Priority: high, Agent: research
3. Opportunity assessment: AI-powered task management system
   Priority: medium, Agent: planning
4. Validation decision for: AI-powered task management system
   Priority: high, Agent: planning

Task execution result: success
Market size: large
```

#### Success Criteria:
- ✓ 4 tasks generated for DISCOVERED stage
- ✓ Tasks have correct priorities (high/medium/low)
- ✓ Assigned agents match task type (research/planning)
- ✓ Execution returns success with market data

---

### VALIDATING Stage (5-8 tasks)

#### Verification Steps:

```bash
python3 << 'EOF'
from project_alpha.core.stage_workflows import StageWorkflows
from project_alpha.core.lifecycle_manager import LifecycleManager

lifecycle = LifecycleManager()
business = lifecycle.create_business({
    "idea": "Automated invoice processing",
    "target_market": "Accounting firms"
})
lifecycle.update_stage(business["id"], "VALIDATING", "Manual test")
business = lifecycle.get_business(business["id"])

workflows = StageWorkflows()
tasks = workflows.get_validating_tasks(business)

print(f"Generated {len(tasks)} VALIDATING tasks:")
for i, task in enumerate(tasks, 1):
    print(f"{i}. {task['title'][:60]}")

# Execute problem validation task
result = workflows.execute_validating_task(tasks[0], business)
print(f"\nProblem validation: {result['problem_validated']}")
print(f"Customer pain level: {result['customer_pain_level']:.2f}")
EOF
```

**Expected Output:**
```
Generated 8 VALIDATING tasks:
1. Customer problem validation: Automated invoice processing
2. Solution fit validation: Automated invoice processing
3. Pricing research: Automated invoice processing
4. Target audience interviews: Automated invoice processing
5. MVP design: Automated invoice processing
6. Business model validation: Automated invoice processing
7. Market entry strategy: Automated invoice processing
8. Build decision: Automated invoice processing

Problem validation: True
Customer pain level: 0.XX
```

#### Success Criteria:
- ✓ 8 tasks generated for VALIDATING stage
- ✓ Includes customer validation, solution fit, pricing research
- ✓ Final task is build/no-build decision
- ✓ Execution returns validation metrics (0.0-1.0)

---

### BUILDING Stage (7-8 tasks)

#### Verification Steps:

```bash
python3 << 'EOF'
from project_alpha.core.stage_workflows import StageWorkflows
from project_alpha.core.lifecycle_manager import LifecycleManager

lifecycle = LifecycleManager()
business = lifecycle.create_business({"idea": "Customer feedback platform"})
lifecycle.update_stage(business["id"], "BUILDING", "Manual test")
business = lifecycle.get_business(business["id"])

workflows = StageWorkflows()
tasks = workflows.get_building_tasks(business)

print(f"Generated {len(tasks)} BUILDING tasks:")
for task in tasks:
    print(f"• {task['title'][:60]}")

# Execute architecture task
result = workflows.execute_building_task(tasks[0], business)
print(f"\nArchitecture type: {result['architecture_type']}")
print(f"Tech stack: {', '.join(result['tech_stack'])}")
EOF
```

**Expected Output:**
```
Generated 8 BUILDING tasks:
• Technical architecture: Customer feedback platform
• MVP Sprint 1: Customer feedback platform
• MVP Sprint 2: Customer feedback platform
• Core features implementation: Customer feedback platform
• QA and testing: Customer feedback platform
• Beta user onboarding: Customer feedback platform
• Feedback collection: Customer feedback platform
• Production readiness: Customer feedback platform

Architecture type: microservices
Tech stack: Python, PostgreSQL, Redis, React
```

#### Success Criteria:
- ✓ 8 tasks generated for BUILDING stage
- ✓ Includes architecture, sprints, testing, deployment
- ✓ Execution returns technical specifications
- ✓ Build progress tracked (0.0-1.0)

---

### SCALING Stage (5-7 tasks)

#### Verification Steps:

```bash
python3 << 'EOF'
from project_alpha.core.stage_workflows import StageWorkflows
from project_alpha.core.lifecycle_manager import LifecycleManager

lifecycle = LifecycleManager()
business = lifecycle.create_business({"idea": "SaaS analytics tool"})
lifecycle.update_stage(business["id"], "SCALING", "Manual test")
lifecycle.update_metrics(business["id"], {"performance": 0.7, "stability": 0.8})
business = lifecycle.get_business(business["id"])

workflows = StageWorkflows()
tasks = workflows.get_scaling_tasks(business)

print(f"Generated {len(tasks)} SCALING tasks:")
for task in tasks:
    print(f"• {task['title'][:55]}")

# Execute marketing task
result = workflows.execute_scaling_task(tasks[0], business)
print(f"\nCampaigns launched: {result['campaigns_launched']}")
print(f"CAC: ${result['cac']:.2f}")
print(f"ROI: {result['roi']:.2f}")
EOF
```

**Expected Output:**
```
Generated 7 SCALING tasks:
• Growth marketing: SaaS analytics tool
• Performance optimization: SaaS analytics tool
• User acquisition scaling: SaaS analytics tool
• Infrastructure scaling: SaaS analytics tool
• Customer success program: SaaS analytics tool
• Analytics tracking: SaaS analytics tool
• Scaling evaluation: SaaS analytics tool

Campaigns launched: X
CAC: $XX.XX
ROI: X.XX
```

#### Success Criteria:
- ✓ 7 tasks generated for SCALING stage
- ✓ Covers marketing, infrastructure, acquisition, retention
- ✓ Execution returns growth metrics (CAC, ROI, retention)
- ✓ Performance and stability metrics updated

---

### OPERATING Stage (4-5 tasks)

#### Verification Steps:

```bash
python3 << 'EOF'
from project_alpha.core.stage_workflows import StageWorkflows
from project_alpha.core.lifecycle_manager import LifecycleManager

lifecycle = LifecycleManager()
business = lifecycle.create_business({"idea": "Project management tool"})
lifecycle.update_stage(business["id"], "OPERATING", "Manual test")
lifecycle.update_metrics(business["id"], {"performance": 0.85, "stability": 0.90})
business = lifecycle.get_business(business["id"])

workflows = StageWorkflows()
tasks = workflows.get_operating_tasks(business)

print(f"Generated {len(tasks)} OPERATING tasks:")
for task in tasks:
    print(f"• {task['title'][:55]}")

# Execute monitoring task
result = workflows.execute_operating_task(tasks[0], business)
print(f"\nUptime: {result['uptime']:.4f}")
print(f"Active users: {result['active_users']}")
print(f"Revenue trend: {result['revenue_trend']}")
EOF
```

**Expected Output:**
```
Generated 5 OPERATING tasks:
• Operations monitoring: Project management tool
• Customer support: Project management tool
• Revenue optimization: Project management tool
• System maintenance: Project management tool
• Performance monitoring: Project management tool

Uptime: 0.XXXX
Active users: XXXX
Revenue trend: stable/growing
```

#### Success Criteria:
- ✓ 5 tasks generated for OPERATING stage
- ✓ Covers monitoring, support, revenue, maintenance
- ✓ Execution returns operational metrics (uptime, users, revenue)
- ✓ Stability remains high (>0.85)

---

### OPTIMIZING Stage (5-6 tasks)

#### Verification Steps:

```bash
python3 << 'EOF'
from project_alpha.core.stage_workflows import StageWorkflows
from project_alpha.core.lifecycle_manager import LifecycleManager

lifecycle = LifecycleManager()
business = lifecycle.create_business({"idea": "E-commerce platform"})
lifecycle.update_stage(business["id"], "OPTIMIZING", "Manual test")
lifecycle.update_metrics(business["id"], {"performance": 0.60, "stability": 0.75})
business = lifecycle.get_business(business["id"])

workflows = StageWorkflows()
tasks = workflows.get_optimizing_tasks(business)

print(f"Generated {len(tasks)} OPTIMIZING tasks:")
for task in tasks:
    print(f"• {task['title'][:55]}")

# Execute bottleneck analysis
result = workflows.execute_optimizing_task(tasks[0], business)
print(f"\nBottlenecks found: {result['bottlenecks_found']}")
print(f"Expected improvement: {result['expected_improvement']}")
EOF
```

**Expected Output:**
```
Generated 6 OPTIMIZING tasks:
• Bottleneck analysis: E-commerce platform
• Cost optimization: E-commerce platform
• UX improvements: E-commerce platform
• Conversion optimization: E-commerce platform
• Technical debt reduction: E-commerce platform
• Optimization evaluation: E-commerce platform

Bottlenecks found: X
Expected improvement: XX%
```

#### Success Criteria:
- ✓ 6 tasks generated for OPTIMIZING stage
- ✓ Covers bottlenecks, cost, UX, conversion, tech debt
- ✓ Execution returns optimization metrics and improvements
- ✓ Performance improvement tracked

---

### TERMINATED Stage (3-4 tasks)

#### Verification Steps:

```bash
python3 << 'EOF'
from project_alpha.core.stage_workflows import StageWorkflows
from project_alpha.core.lifecycle_manager import LifecycleManager

lifecycle = LifecycleManager()
business = lifecycle.create_business({"idea": "Failed startup concept"})
lifecycle.update_stage(business["id"], "TERMINATED", "Validation failed")
business = lifecycle.get_business(business["id"])

workflows = StageWorkflows()
tasks = workflows.get_terminated_tasks(business)

print(f"Generated {len(tasks)} TERMINATED tasks:")
for task in tasks:
    print(f"• {task['title'][:55]}")

# Execute final report task
result = workflows.execute_terminated_task(tasks[0], business)
print(f"\nFinal report generated: {result['final_report_generated']}")
print(f"Termination reason: {result['termination_reason']}")
EOF
```

**Expected Output:**
```
Generated 4 TERMINATED tasks:
• Final report: Failed startup concept
• Data archival: Failed startup concept
• Lessons learned: Failed startup concept
• Resource cleanup: Failed startup concept

Final report generated: True
Termination reason: Validation failed
```

#### Success Criteria:
- ✓ 4 tasks generated for TERMINATED stage
- ✓ Covers reporting, archival, lessons, cleanup
- ✓ Execution records termination reason and learnings
- ✓ Resources properly deallocated

---

## Portfolio Execution Verification

### Test Portfolio-Level Operations

```bash
python3 << 'EOF'
from project_alpha.core.portfolio_manager import PortfolioManager
from project_alpha.core.lifecycle_manager import LifecycleManager

portfolio = PortfolioManager(max_active=5)
lifecycle = LifecycleManager()

# Create multiple businesses
ideas = [
    "AI content generator",
    "Blockchain supply chain",
    "IoT sensor network",
    "Mobile fitness app",
    "Cloud storage service"
]

for idea in ideas:
    if portfolio.can_add_business():
        business = lifecycle.create_business({"idea": idea})
        portfolio.add_business(business)
        print(f"✓ Added: {idea}")

# Get portfolio stats
stats = portfolio.get_portfolio_stats()
print(f"\nPortfolio Statistics:")
print(f"Total businesses: {stats['total_businesses']}")
print(f"Active: {stats['active_count']}")

print(f"\nBy stage:")
for stage, count in stats['by_stage'].items():
    if count > 0:
        print(f"  {stage}: {count}")

# Get top performers
top = portfolio.get_top_performers(3)
print(f"\nTop performers: {len(top)}")
EOF
```

**Expected Output:**
```
✓ Added: AI content generator
✓ Added: Blockchain supply chain
✓ Added: IoT sensor network
✓ Added: Mobile fitness app
✓ Added: Cloud storage service

Portfolio Statistics:
Total businesses: 5
Active: 5

By stage:
  DISCOVERED: 5

Top performers: 3
```

#### Success Criteria:
- ✓ Can add up to max_active businesses
- ✓ Portfolio stats accurately reflect business count
- ✓ Top performers can be retrieved and ranked
- ✓ Stage distribution correctly calculated

---

## Multi-Business Management Verification

### Concurrent Business Processing

```bash
python3 << 'EOF'
from project_alpha.core.workflow_orchestrator import WorkflowOrchestrator
from project_alpha.core.stage_workflows import StageWorkflows
from project_alpha.core.lifecycle_manager import LifecycleManager
from project_alpha.core.portfolio_manager import PortfolioManager

orchestrator = WorkflowOrchestrator()
workflows = StageWorkflows()
lifecycle = LifecycleManager()
portfolio = PortfolioManager()

# Create 3 businesses in different stages
businesses = []
for i, (idea, stage) in enumerate([
    ("SaaS CRM", "VALIDATING"),
    ("Mobile game", "BUILDING"),
    ("Analytics dashboard", "SCALING")
]):
    biz = lifecycle.create_business({"idea": idea})
    lifecycle.update_stage(biz["id"], stage, "Test")
    if stage == "SCALING":
        lifecycle.update_metrics(biz["id"], {"performance": 0.75, "stability": 0.80})
    businesses.append(lifecycle.get_business(biz["id"]))

# Execute workflows for all businesses
results = []
for biz in businesses:
    tasks = workflows.get_tasks_for_stage(biz["stage"], biz)
    print(f"\n{biz['opportunity']['idea']} ({biz['stage']}): {len(tasks)} tasks")

    result = orchestrator.execute_stage_workflow(
        business=biz,
        stage=biz["stage"],
        tasks=tasks[:3],  # Execute first 3 tasks
        stage_workflows_module=workflows
    )
    results.append(result)
    print(f"  Status: {result['status']}")
    print(f"  Completed: {result['tasks_completed']}/{result['tasks_total']}")

# Check execution stats
stats = orchestrator.get_execution_stats()
print(f"\nExecution Statistics:")
print(f"Total workflows: {stats['total_workflows']}")
print(f"Total tasks: {stats['total_tasks']}")
print(f"Success rate: {stats['success_rate']:.2f}")
EOF
```

**Expected Output:**
```
SaaS CRM (VALIDATING): 8 tasks
  Status: completed
  Completed: 3/3

Mobile game (BUILDING): 8 tasks
  Status: completed
  Completed: 3/3

Analytics dashboard (SCALING): 7 tasks
  Status: completed
  Completed: 3/3

Execution Statistics:
Total workflows: 3
Total tasks: 9
Success rate: 1.00
```

#### Success Criteria:
- ✓ Multiple businesses processed concurrently
- ✓ Each business executes stage-appropriate tasks
- ✓ Workflow orchestrator tracks all executions
- ✓ High success rate (>0.90)

---

## Tool Integrations Verification

### AI-Q Integration

```bash
# Set AI-Q API key (optional - will fallback if not set)
export AIQ_API_KEY="test_key_12345"

python3 << 'EOF'
from project_alpha.core.workflow_orchestrator import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()
status = orchestrator.get_tool_status()

print("AI-Q Status:")
print(f"  Available: {status['ai_q']['available']}")
print(f"  Initialized: {status['ai_q']['initialized']}")

if status['ai_q']['available']:
    print("  ✓ AI-Q reasoning will be used for task prioritization")
else:
    print("  ⓘ AI-Q not available, using default task order")
EOF
```

**Expected Outputs:**

With API key:
```
AI-Q Status:
  Available: True
  Initialized: True
  ✓ AI-Q reasoning will be used for task prioritization
```

Without API key:
```
AI-Q Status:
  Available: False
  Initialized: False
  ⓘ AI-Q not available, using default task order
```

#### Success Criteria:
- ✓ Detects AIQ_API_KEY environment variable
- ✓ Initializes when available
- ✓ Gracefully degrades when unavailable

---

### NemoClaw Integration

```bash
# Check NemoClaw availability
python3 << 'EOF'
from project_alpha.core.workflow_orchestrator import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()
status = orchestrator.get_tool_status()

print("NemoClaw Status:")
print(f"  Available: {status['nemoclaw']['available']}")
print(f"  Initialized: {status['nemoclaw']['initialized']}")

if status['nemoclaw']['available']:
    print(f"  Sandbox path: {orchestrator.nemoclaw['sandbox_path']}")
    print("  ✓ Tasks will execute in sandboxed environment")
else:
    print("  ⓘ NemoClaw not installed, using direct execution")
EOF
```

**Expected Output:**
```
NemoClaw Status:
  Available: False
  Initialized: False
  ⓘ NemoClaw not installed, using direct execution
```

#### Success Criteria:
- ✓ Checks for NemoClaw binary in PATH
- ✓ Initializes sandbox when available
- ✓ Falls back to direct execution when unavailable

---

### Zep Memory Integration

```bash
# Set Zep API key (optional)
export ZEP_API_KEY="test_zep_key"

python3 << 'EOF'
from project_alpha.core.workflow_orchestrator import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()
status = orchestrator.get_tool_status()

print("Zep Memory Status:")
print(f"  Available: {status['zep']['available']}")
print(f"  Initialized: {status['zep']['initialized']}")

if status['zep']['available']:
    print(f"  Session ID: {orchestrator.zep['session_id']}")
    print("  ✓ Task results will be stored in Zep memory")
else:
    print("  ⓘ Zep not available, using local memory only")
EOF
```

**Expected Outputs:**

With API key:
```
Zep Memory Status:
  Available: True
  Initialized: True
  Session ID: project_alpha_20260325
  ✓ Task results will be stored in Zep memory
```

Without API key:
```
Zep Memory Status:
  Available: False
  Initialized: False
  ⓘ Zep not available, using local memory only
```

#### Success Criteria:
- ✓ Detects ZEP_API_KEY environment variable
- ✓ Creates session with timestamp
- ✓ Stores task results when available

---

### Simulator (Built-in)

```bash
python3 << 'EOF'
from project_alpha.core.workflow_orchestrator import WorkflowOrchestrator
from project_alpha.core.lifecycle_manager import LifecycleManager

orchestrator = WorkflowOrchestrator()
lifecycle = LifecycleManager()

# Simulator is always available
status = orchestrator.get_tool_status()
print("Simulator Status:")
print(f"  Available: {status['simulator']['available']}")
print(f"  Initialized: {status['simulator']['initialized']}")
print(f"  Confidence threshold: {orchestrator.simulator['confidence_threshold']}")

# Test simulation
business = lifecycle.create_business({"idea": "Test app"})
task = {"title": "Test task", "task_id": "test_1"}

simulation = orchestrator._simulate_task(task, business, "BUILDING")
print(f"\nSimulation result:")
print(f"  Confidence: {simulation['confidence']:.2f}")
print(f"  Available: {simulation['available']}")
EOF
```

**Expected Output:**
```
Simulator Status:
  Available: True
  Initialized: True
  Confidence threshold: 0.75

Simulation result:
  Confidence: 0.XX
  Available: True
```

#### Success Criteria:
- ✓ Simulator is always available (built-in)
- ✓ Returns confidence score (0.0-1.0)
- ✓ Adjusts confidence based on business metrics

---

## Fallback Behaviors Verification

### Test Fallback Execution Path

```bash
python3 << 'EOF'
from project_alpha.core.workflow_orchestrator import WorkflowOrchestrator
from project_alpha.core.lifecycle_manager import LifecycleManager

orchestrator = WorkflowOrchestrator()
lifecycle = LifecycleManager()

# Create business and unknown task
business = lifecycle.create_business({"idea": "Test business"})
task = {
    "task_id": "unknown_task",
    "title": "Unknown task type",
    "stage": "UNKNOWN_STAGE"
}

# This should trigger fallback execution
result = orchestrator._fallback_execute(task, business, "UNKNOWN_STAGE")

print("Fallback execution result:")
print(f"  Status: {result['status']}")
print(f"  Fallback: {result['fallback']}")
print(f"  Message: {result['output']['message']}")
EOF
```

**Expected Output:**
```
Fallback execution result:
  Status: completed
  Fallback: True
  Message: Fallback execution: Unknown task type
```

#### Success Criteria:
- ✓ Unknown tasks execute via fallback handler
- ✓ Returns completed status with fallback flag
- ✓ Includes helpful message about fallback execution

---

### Test Low Confidence Simulation Rejection

```bash
python3 << 'EOF'
from project_alpha.core.workflow_orchestrator import WorkflowOrchestrator
from project_alpha.core.lifecycle_manager import LifecycleManager

orchestrator = WorkflowOrchestrator()
lifecycle = LifecycleManager()

# Create business with high failure count (reduces confidence)
business = lifecycle.create_business({"idea": "Risky business"})
lifecycle.update_metrics(business["id"], {"failure_count": 5})
business = lifecycle.get_business(business["id"])

task = {"task_id": "risky_task", "title": "Risky task"}

# Simulate should return low confidence
simulation = orchestrator._simulate_task(task, business, "BUILDING")
print(f"Simulation confidence: {simulation['confidence']:.2f}")
print(f"Factors: {simulation['factors']}")

if simulation['confidence'] < 0.75:
    print("\n✓ Task would be rejected due to low confidence")
else:
    print("\n✗ Task would proceed despite high failure count")
EOF
```

**Expected Output:**
```
Simulation confidence: 0.XX (< 0.75)
Factors: {'failure_count': 5, 'stage': 'BUILDING', 'base_confidence': 0.8}

✓ Task would be rejected due to low confidence
```

#### Success Criteria:
- ✓ High failure count reduces confidence
- ✓ Tasks rejected when confidence < 0.75
- ✓ Simulation factors clearly reported

---

## Performance Verification

### Execution Speed Test

```bash
python3 << 'EOF'
import time
from project_alpha.core.workflow_orchestrator import WorkflowOrchestrator
from project_alpha.core.stage_workflows import StageWorkflows
from project_alpha.core.lifecycle_manager import LifecycleManager

orchestrator = WorkflowOrchestrator()
workflows = StageWorkflows()
lifecycle = LifecycleManager()

# Create test business
business = lifecycle.create_business({"idea": "Performance test"})

# Time workflow execution
start = time.time()
tasks = workflows.get_discovered_tasks(business)
result = orchestrator.execute_stage_workflow(
    business=business,
    stage="DISCOVERED",
    tasks=tasks,
    stage_workflows_module=workflows
)
duration = time.time() - start

print(f"Workflow execution time: {duration:.3f}s")
print(f"Tasks completed: {result['tasks_completed']}/{result['tasks_total']}")
print(f"Success rate: {result['success_rate']:.2%}")

# Performance targets
if duration < 1.0:
    print("✓ Performance: Excellent (<1s)")
elif duration < 3.0:
    print("✓ Performance: Good (<3s)")
else:
    print("⚠ Performance: Needs optimization (>3s)")
EOF
```

**Expected Output:**
```
Workflow execution time: 0.XXXs
Tasks completed: 4/4
Success rate: 100.00%
✓ Performance: Excellent (<1s)
```

#### Success Criteria:
- ✓ Workflow execution < 3 seconds for 4 tasks
- ✓ 100% success rate
- ✓ No memory leaks or resource exhaustion

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Tool Status Shows All Unavailable

**Symptoms:**
```
ai_q: Available=False
nemoclaw: Available=False
zep: Available=False
```

**Solution:**
```bash
# AI-Q: Set API key
export AIQ_API_KEY="your_api_key"

# NemoClaw: Install binary
# (Instructions depend on your system)

# Zep: Set API key
export ZEP_API_KEY="your_zep_key"

# Verify
python3 -c "from project_alpha.core.workflow_orchestrator import WorkflowOrchestrator; print(WorkflowOrchestrator().get_tool_status())"
```

---

#### Issue 2: Tests Fail with ModuleNotFoundError

**Symptoms:**
```
ModuleNotFoundError: No module named 'project_alpha'
```

**Solution:**
```bash
# Add project to PYTHONPATH
export PYTHONPATH="/Users/krissanders/project_alpha:$PYTHONPATH"

# Or install in development mode
cd /Users/krissanders/project_alpha
pip3 install -e .

# Verify
python3 -c "import project_alpha; print('✓ Import successful')"
```

---

#### Issue 3: Workflows Returning Empty Task Lists

**Symptoms:**
```
Generated 0 DISCOVERED tasks
```

**Solution:**
```python
# Check business structure
from project_alpha.core.lifecycle_manager import LifecycleManager

lifecycle = LifecycleManager()
business = lifecycle.create_business({"idea": "Test business"})

# Ensure business has all required fields
print(f"Business ID: {business['id']}")
print(f"Stage: {business['stage']}")
print(f"Opportunity: {business['opportunity']}")

# Regenerate tasks
from project_alpha.core.stage_workflows import StageWorkflows
workflows = StageWorkflows()
tasks = workflows.get_tasks_for_stage(business["stage"], business)
print(f"Tasks generated: {len(tasks)}")
```

---

#### Issue 4: Low Success Rates

**Symptoms:**
```
Success rate: 0.45
```

**Solution:**
```python
# Check execution errors
from project_alpha.core.workflow_orchestrator import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()
stats = orchestrator.get_execution_stats()
print(f"Success rate: {stats['success_rate']:.2%}")

# Check recent failures in execution history
for workflow in orchestrator.execution_history[-5:]:
    if workflow['status'] != 'completed':
        print(f"\nFailed workflow: {workflow['workflow_id']}")
        print(f"Errors: {workflow['errors']}")
```

---

#### Issue 5: Memory Growth Over Time

**Symptoms:**
- Increasing memory usage during long runs
- System slowdown

**Solution:**
```python
# Clear execution history periodically
from project_alpha.core.workflow_orchestrator import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()

# Keep only last 100 executions
if len(orchestrator.execution_history) > 100:
    orchestrator.execution_history = orchestrator.execution_history[-100:]

# Verify
print(f"History size: {len(orchestrator.execution_history)}")
```

---

### Debug Mode

Enable verbose logging for detailed diagnostics:

```bash
python3 << 'EOF'
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Run your test
from project_alpha.core.workflow_orchestrator import WorkflowOrchestrator
orchestrator = WorkflowOrchestrator()
# ... rest of your code
EOF
```

---

## Verification Checklist

Use this checklist to verify complete Phase 5 implementation:

### Stage Workflows
- [ ] DISCOVERED stage: 4 tasks generated and executed
- [ ] VALIDATING stage: 8 tasks generated and executed
- [ ] BUILDING stage: 8 tasks generated and executed
- [ ] SCALING stage: 7 tasks generated and executed
- [ ] OPERATING stage: 5 tasks generated and executed
- [ ] OPTIMIZING stage: 6 tasks generated and executed
- [ ] TERMINATED stage: 4 tasks generated and executed

### Portfolio Management
- [ ] Can add businesses up to max_active limit
- [ ] Portfolio stats accurately calculated
- [ ] Top performers correctly ranked
- [ ] Stage distribution tracked

### Multi-Business Operations
- [ ] Multiple businesses process concurrently
- [ ] Stage-specific workflows execute correctly
- [ ] No interference between businesses
- [ ] High overall success rate (>90%)

### Tool Integrations
- [ ] AI-Q: Detection and initialization working
- [ ] NemoClaw: Detection and sandbox working
- [ ] Zep: Detection and memory storage working
- [ ] Simulator: Always available and functioning

### Fallback Behaviors
- [ ] Unknown tasks execute via fallback
- [ ] Low confidence tasks rejected
- [ ] Missing tools don't block execution
- [ ] Graceful degradation working

### Performance
- [ ] Workflow execution < 3 seconds
- [ ] No memory leaks
- [ ] Success rate > 90%
- [ ] All tests passing

---

## Support

For issues not covered in this guide:

1. Check test output: `pytest tests/test_workflows.py -v`
2. Review execution history in workflow orchestrator
3. Enable debug logging for detailed traces
4. Verify tool status with `get_tool_status()`

---

**Phase 5 Verification Complete** ✓
