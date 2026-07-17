# Portfolio Evidence

Detail for `testing-obsessive` — how testing decisions double as apprenticeship/portfolio evidence.

**KSBs Demonstrated by Testing**:
- **S9**: Create Analysis Artefacts (test plans, coverage reports, risk assessments)
- **S10**: Analyse Problem Reports (reproduction tests, debugging tests)
- **S11**: Apply Appropriate Recovery Techniques (regression tests)
- **S14**: Follow Company Procedures (testing standards, CI integration)

**How to Document**:
- Screenshot coverage reports showing strategic testing
- Document risk assessment decisions in README/docs
- Show test files alongside features
- Explain testing decisions in code review
- Document bug reproduction tests
- Demonstrate professional judgment about test priorities

**Evidence Example**:
```markdown
## Testing Strategy

Applied risk-based testing approach to this feature:

HIGH PRIORITY (Tested):
- Payment calculation logic - Complex algorithm, financial impact
- User authentication - Security critical
- Data validation - Prevents data corruption

MEDIUM PRIORITY (Basic tests):
- Form validation - Standard patterns, low complexity
- API error handling - Important but straightforward

LOW PRIORITY (Manual testing only):
- UI styling - Visual verification sufficient
- Configuration loading - One-time, low risk
```
