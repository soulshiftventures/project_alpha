# Workflow Validator Usage Guide

## Overview

The `WorkflowValidator` performs 5 comprehensive pre-execution checks before any workflow is executed. This ensures safety and increases success probability by requiring a minimum 75% confidence score.

## The 5 Validation Checks

### 1. Business Health Check
Validates business metrics and lifecycle state:
- Failure count (errors if > 5, warnings if > 3)
- Performance score (errors if < 0.4, warnings if < 0.6)
- Validation score for early stages
- Stage cycling detection (potential regression)
- Terminated state check

### 2. Task Dependency Validation
Ensures tasks are properly configured:
- No duplicate task IDs
- All required fields present (task_id, title, stage, priority)
- Task count matches expected range for stage
- At least one high-priority task
- Stage consistency across all tasks

### 3. Resource Availability Check
Validates system and agent resources:
- Required agents are available
- Resource-intensive stages flagged
- Concurrent workflow limits checked
- Business resource allocation validated

### 4. Simulation Validation (75% Threshold)
Predicts workflow success probability:
- Each task simulated based on historical data
- Critical tasks must have > 60% confidence
- Average confidence must be >= 75%
- Risk levels assigned (low/medium/high)
- Business metrics factored into predictions

### 5. Tool Integration Check
Validates external tool availability:
- **Simulator** (required): Built-in fallback always available
- **AI-Q** (optional): Advanced reasoning and task prioritization
- **NemoClaw** (optional): Sandboxed task execution
- **Zep Memory** (optional): Persistent validation logging

Base confidence: 75% (Simulator only)
- +8% for AI-Q
- +8% for NemoClaw
- +9% for Zep
- Maximum: 100%

## Usage

### Basic Usage

```python
from core.workflow_validator import WorkflowValidator
from core.workflow_orchestrator import WorkflowOrchestrator

# Initialize with orchestrator for full tool integration
orchestrator = WorkflowOrchestrator()
validator = WorkflowValidator(orchestrator=orchestrator)

# Validate workflow before execution
result = validator.validate_workflow(
    business=business_dict,
    stage="VALIDATING",
    tasks=task_list,
    stage_workflows_module=stage_workflows
)

# Check result
if result["passed"]:
    print(f"✓ Validation passed with {result['confidence']:.2%} confidence")
    # Proceed with workflow execution
else:
    print(f"✗ Validation failed: {result['recommendation']}")
    print(f"Errors: {result['errors']}")
```

### Integration with WorkflowOrchestrator

```python
from core.workflow_validator import WorkflowValidator
from core.workflow_orchestrator import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()
validator = WorkflowValidator(orchestrator=orchestrator)

# Validate before executing stage workflow
validation_result = validator.validate_workflow(
    business=business,
    stage=current_stage,
    tasks=tasks,
    stage_workflows_module=stage_workflows
)

if validation_result["passed"]:
    # Safe to proceed
    execution_result = orchestrator.execute_stage_workflow(
        business=business,
        stage=current_stage,
        tasks=tasks,
        stage_workflows_module=stage_workflows
    )
elif validation_result["recommendation"] == "review":
    # Manual review recommended
    print(f"Manual review required (confidence: {validation_result['confidence']:.2f})")
else:
    # Abort execution
    print(f"Aborting: {validation_result['errors']}")
```

## Validation Result Structure

```python
{
    "validation_id": "val_biz_001_VALIDATING_2024-03-25T22:50:00",
    "timestamp": "2024-03-25T22:50:00.000000",
    "business_id": "biz_001",
    "business_idea": "AI-powered analytics platform",
    "stage": "VALIDATING",
    "task_count": 5,

    # Overall result
    "passed": True,
    "confidence": 0.82,
    "recommendation": "proceed",  # proceed | review | abort

    # Individual checks
    "checks": {
        "business_health": {
            "check_name": "business_health",
            "passed": True,
            "confidence": 0.90,
            "warnings": [],
            "errors": [],
            "details": {...}
        },
        "task_dependencies": {...},
        "resource_availability": {...},
        "simulation": {...},
        "tool_integration": {...}
    },

    # Aggregated issues
    "warnings": [
        "[simulation] 2 tasks have elevated risk (confidence < 0.7)"
    ],
    "errors": []
}
```

## Recommendations

### Proceed (Confidence >= 75%, All Checks Pass)
- Safe to execute workflow
- All validation checks passed
- Confidence meets or exceeds threshold
- No critical errors detected

### Review (Confidence 65-74%, Some Checks Pass)
- Manual review recommended
- Some checks passed but confidence below threshold
- Non-critical warnings present
- Consider addressing warnings before execution

### Abort (Confidence < 65% or Critical Errors)
- Do NOT execute workflow
- Critical validation failures
- High risk of workflow failure
- Address errors before retrying

## Statistics and History

```python
# Get validation statistics
stats = validator.get_validation_statistics()
print(f"Total validations: {stats['total_validations']}")
print(f"Pass rate: {stats['pass_rate']:.2%}")
print(f"Average confidence: {stats['avg_confidence']:.2f}")

# Get specific validation report
report = validator.get_validation_report(validation_id="val_biz_001_...")
print(f"Passed: {report['passed']}")
print(f"Checks: {len(report['checks'])}")

# Get all validation history
history = validator.get_validation_history()
for validation in history[-5:]:  # Last 5 validations
    print(f"{validation['validation_id']}: {validation['recommendation']}")
```

## Zep Memory Integration

When `ZEP_API_KEY` environment variable is set, validation results are automatically logged to Zep memory:

```bash
export ZEP_API_KEY="your-zep-api-key"
```

Validation results are stored with:
- Session ID: `validator_YYYYMMDD_HHMMSS`
- Business context
- Check results summary
- Confidence scores
- Warnings and errors count

Fallback: If Zep is unavailable, results are stored locally in `/Users/krissanders/project_alpha/memory/validation_history.json`

## Expected Task Ranges by Stage

| Stage | Min Tasks | Max Tasks |
|-------|-----------|-----------|
| DISCOVERED | 3 | 4 |
| VALIDATING | 5 | 8 |
| BUILDING | 7 | 8 |
| SCALING | 5 | 7 |
| OPERATING | 4 | 5 |
| OPTIMIZING | 5 | 6 |
| TERMINATED | 3 | 4 |

## Example Scenarios

### Scenario 1: New Business (High Confidence)
```python
business = {
    'id': 'biz_001',
    'stage': 'DISCOVERED',
    'opportunity': {'idea': 'AI analytics'},
    'metrics': {
        'failure_count': 0,
        'performance': 0.85,
        'validation_score': 0.80
    },
    'history': []
}
# Expected: confidence ~0.85, recommendation=proceed
```

### Scenario 2: Struggling Business (Low Confidence)
```python
business = {
    'id': 'biz_002',
    'stage': 'OPERATING',
    'metrics': {
        'failure_count': 8,
        'performance': 0.32,
        'validation_score': 0.45
    },
    'history': [...]  # Stage cycling detected
}
# Expected: confidence ~0.40, recommendation=abort
```

### Scenario 3: Borderline Business (Review Required)
```python
business = {
    'id': 'biz_003',
    'stage': 'BUILDING',
    'metrics': {
        'failure_count': 3,
        'performance': 0.68,
        'validation_score': 0.72
    }
}
# Expected: confidence ~0.70, recommendation=review
```

## Best Practices

1. **Always validate before execution**: Never skip validation for production workflows
2. **Address errors immediately**: Don't proceed with "review" recommendation without investigation
3. **Monitor confidence trends**: Track validation confidence over time
4. **Configure Zep integration**: Enable persistent logging for production systems
5. **Review simulation details**: Check `task_simulations` in simulation check for risky tasks
6. **Handle warnings**: Even if validation passes, address warnings to improve reliability
7. **Set up orchestrator**: Always pass orchestrator instance for full tool integration
8. **Check tool status**: Verify all tools are available for maximum confidence

## Production Deployment

For production use:

1. Set environment variables:
```bash
export ZEP_API_KEY="your-zep-api-key"
export AIQ_API_KEY="your-aiq-api-key"  # Optional
```

2. Initialize with orchestrator:
```python
orchestrator = WorkflowOrchestrator()
validator = WorkflowValidator(orchestrator=orchestrator)
```

3. Check tool status:
```python
tool_status = orchestrator.get_tool_status()
print(f"Simulator: {tool_status['simulator']['available']}")
print(f"AI-Q: {tool_status['ai_q']['available']}")
print(f"NemoClaw: {tool_status['nemoclaw']['available']}")
print(f"Zep: {tool_status['zep']['available']}")
```

4. Validate before every workflow:
```python
result = validator.validate_workflow(business, stage, tasks, stage_workflows)
if not result["passed"]:
    raise ValidationError(f"Workflow validation failed: {result['errors']}")
```

## File Locations

- Validator: `/Users/krissanders/project_alpha/core/workflow_validator.py`
- Local backup: `/Users/krissanders/project_alpha/memory/validation_history.json`
- Integration: `/Users/krissanders/project_alpha/core/workflow_orchestrator.py`
